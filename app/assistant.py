import re

from app.mcp.router import select_tools
from app.mcp.service import get_mcp_data
from app.rag.chain import answer_question, retrieve_context
from app.planner import create_itinerary


def extract_inr_amount(question: str) -> float | None:
    """Extract an INR amount such as ₹60,000 or Rs 60000 from the question."""

    patterns = [
        r"₹\s*([\d,]+(?:\.\d+)?)",
        r"\bINR\s*([\d,]+(?:\.\d+)?)\b",
        r"\bRs\.?\s*([\d,]+(?:\.\d+)?)\b",
        r"\brupees?\s*([\d,]+(?:\.\d+)?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)

        if match:
            amount_text = match.group(1).replace(",", "")
            return float(amount_text)

    return None


# Currency tokens ordered so that more specific, multi-word aliases are
# matched before shorter ones (e.g. "singapore dollars" before "dollars").
_CURRENCY_TOKENS = [
    ("SGD", ["singapore dollars", "singapore dollar", "sgd", "s$"]),
    ("USD", ["us dollars", "us dollar", "u.s. dollars", "u.s. dollar", "usd"]),
    ("EUR", ["euros", "euro", "eur", "€"]),
    ("GBP", ["pounds", "pound", "gbp", "£"]),
    ("INR", ["rupees", "rupee", "inr", "rs.", "rs", "₹"]),
]


def _find_currency_mentions(text: str) -> list[tuple[int, str]]:
    """Return currency mentions as (position, ISO code), ordered by position."""

    mentions: list[tuple[int, str]] = []
    used = [False] * len(text)

    for code, tokens in _CURRENCY_TOKENS:
        for token in tokens:
            start = 0

            while True:
                idx = text.find(token, start)

                if idx == -1:
                    break

                end = idx + len(token)

                # Require word boundaries for alphabetic tokens so that
                # "inr" does not match inside another word.
                if token[0].isalnum():
                    before_ok = idx == 0 or not text[idx - 1].isalnum()
                else:
                    before_ok = True

                if token[-1].isalnum():
                    after_ok = end >= len(text) or not text[end].isalnum()
                else:
                    after_ok = True

                if before_ok and after_ok and not any(used[idx:end]):
                    mentions.append((idx, code))
                    for position in range(idx, end):
                        used[position] = True

                start = end

    mentions.sort()
    return mentions


def _extract_amount(text: str, mentions: list[tuple[int, str]]) -> float | None:
    """Extract the monetary amount, preferring a number near a currency token."""

    numbers = [
        (match.start(), match.group(1))
        for match in re.finditer(r"(\d[\d,]*(?:\.\d+)?)", text)
    ]

    if not numbers:
        return None

    if mentions:
        best_text = None
        best_distance = None

        for number_position, number_text in numbers:
            for currency_position, _ in mentions:
                distance = abs(number_position - currency_position)

                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_text = number_text

        return float(best_text.replace(",", ""))

    return float(numbers[0][1].replace(",", ""))


def parse_currency_request(
    question: str,
) -> tuple[float | None, str, str]:
    """Parse amount and source/target currencies from a conversion request.

    Supports directions such as INR -> SGD, SGD -> INR and USD -> SGD.
    Defaults to INR -> SGD when a side is not specified.
    """

    text = question.lower()
    mentions = _find_currency_mentions(text)
    amount = _extract_amount(text, mentions)

    from_currency = "INR"
    to_currency = "SGD"

    if not mentions:
        return amount, from_currency, to_currency

    codes_in_order = [code for _, code in mentions]

    to_match = None
    from_match = None

    for position, code in mentions:
        prefix = text[max(0, position - 8):position]

        if re.search(r"\b(?:to|in|into)\s+$", prefix):
            to_match = code
        elif re.search(r"\bfrom\s+$", prefix):
            from_match = code

    if to_match:
        to_currency = to_match

    if from_match:
        from_currency = from_match
    else:
        # First currency that is not the target becomes the source.
        for code in codes_in_order:
            if code != to_currency:
                from_currency = code
                break

    if not to_match:
        # A currency other than the source becomes the target.
        for code in codes_in_order:
            if code != from_currency:
                to_currency = code
                break

    return amount, from_currency, to_currency


def run_assistant(
    question: str,
    amount: float | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """Run the travel assistant with RAG, MCP, planning, and conversation context."""

    if conversation_history is None:
        conversation_history = []

    selected_tools = select_tools(question)

    rag_result = None
    mcp_result = {}

    question_lower = question.lower()

    itinerary_phrases = [
        "itinerary",
        "trip plan",
        "plan a trip",
        "suggest an itinerary",
    ]

    # The planner is required when:
    # - current weather/currency information is needed, or
    # - the user explicitly asks for an itinerary/trip plan.
    planner_required = (
        "weather" in selected_tools
        or "currency" in selected_tools
        or "itinerary" in question_lower
        or "trip plan" in question_lower
        or "plan a trip" in question_lower
        or "suggest an itinerary" in question_lower
    )

    # Retrieve knowledge-base information only when RAG is selected.
    # When the planner will generate the final answer, retrieve the
    # grounding context only and skip the extra RAG answer generation.
    if "rag" in selected_tools:
        if planner_required:
            rag_result = retrieve_context(question, conversation_history)
        else:
            rag_result = answer_question(question, conversation_history)

    # Extract INR amount from the user's request when not explicitly supplied.
    if amount is None:
        amount = extract_inr_amount(question)

    # Select only the MCP tools requested by the router.
    mcp_tools = [
        tool
        for tool in selected_tools
        if tool in {"weather", "currency"}
    ]

    # Determine the conversion direction from the user's request so that
    # any supported pair works (INR -> SGD, SGD -> INR, USD -> SGD, ...).
    from_currency = "INR"
    to_currency = "SGD"

    if "currency" in mcp_tools:
        parsed_amount, from_currency, to_currency = parse_currency_request(
            question
        )

        if amount is None:
            amount = parsed_amount

    if mcp_tools:
        mcp_result = get_mcp_data(
            tools=mcp_tools,
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
        )

    final_answer = None

    # Weather-only request.
    if (
        "weather" in selected_tools
        and "rag" not in selected_tools
        and not any(
            phrase in question_lower
            for phrase in itinerary_phrases
        )
    ):
        weather = mcp_result.get("weather", {})

        if weather.get("error"):
            final_answer = (
                "I'm sorry — the live weather service is "
                "unavailable right now, so I can't share the "
                "Singapore forecast at the moment. Please try "
                "again shortly."
            )
        else:
            daily = weather.get("daily", {})

            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            rain = daily.get("precipitation_probability_max", [])

            weather_lines = []

            for index, date in enumerate(dates):
                if index >= len(max_temps) or index >= len(min_temps):
                    continue

                rain_probability = (
                    rain[index]
                    if index < len(rain)
                    else None
                )

                if rain_probability is None:
                    rain_text = ""
                elif rain_probability >= 60:
                    rain_text = (
                        f" — pack an umbrella, "
                        f"{rain_probability}% chance of rain"
                    )
                elif rain_probability >= 30:
                    rain_text = (
                        f" — a few showers possible "
                        f"({rain_probability}% chance of rain)"
                    )
                else:
                    rain_text = (
                        f" — mostly dry "
                        f"({rain_probability}% chance of rain)"
                    )

                weather_lines.append(
                    f"- **{date}:** "
                    f"{min_temps[index]}°C to {max_temps[index]}°C"
                    f"{rain_text}"
                )

            final_answer = (
                "Here's the latest Singapore forecast "
                "(live from the weather tool):\n\n"
                + "\n".join(weather_lines)
                + "\n\nExpect warm, humid days throughout — light, "
                "breathable clothing works best. If you'd like, I "
                "can plan a day's activities around this forecast."
            )

    # Currency-only request.
    elif (
        "currency" in selected_tools
        and "rag" not in selected_tools
        and not any(
            phrase in question_lower
            for phrase in itinerary_phrases
        )
    ):
        currency = mcp_result.get("currency", {})

        if currency.get("error"):
            missing_amount = "amount" in currency.get("error", "").lower()

            if missing_amount:
                final_answer = (
                    "I can convert your budget once you tell me the "
                    "amount — for example, \"Convert 60,000 "
                    f"{from_currency} to {to_currency}\"."
                )
            else:
                final_answer = (
                    "I'm sorry — the live currency service is "
                    "unavailable right now, so I can't convert your "
                    "budget at the moment. Please try again shortly."
                )
        else:
            base = currency.get("base", from_currency)
            rates = currency.get("rates", {})
            converted_amount = rates.get(to_currency)
            date = currency.get("date", "N/A")

            final_answer = (
                f"At today's live exchange rate, "
                f"**{amount:g} {base}** is about "
                f"**{converted_amount} {to_currency}** "
                f"(rate as of {date}).\n\n"
                "Would you like me to suggest a three-day Singapore "
                "itinerary that fits this budget?"
            )

    # Combined RAG + MCP or itinerary request.
    elif planner_required:
        final_answer = create_itinerary(
            question=question,
            rag_result=rag_result or {},
            mcp_result=mcp_result,
            conversation_history=conversation_history,
        )

    # Pure RAG question.
    elif rag_result:
        final_answer = rag_result.get("answer")

    # Fallback for any remaining MCP response.
    elif mcp_result:
        final_answer = str(mcp_result)

    conversation_history.append({
        "user": question,
        "assistant": final_answer,
    })

    return {
        "question": question,
        "selected_tools": selected_tools,
        "rag": rag_result,
        "mcp": mcp_result,
        "answer": final_answer,
        "conversation_history": conversation_history,
    }

if __name__ == "__main__":
    question = (
        "Create a three-day Singapore itinerary for next week "
        "and adjust it according to the weather forecast."
    )

    result = run_assistant(question)

    print("\nSelected tools:")
    print(result["selected_tools"])

    print("\nFinal answer:")
    print(result["answer"])