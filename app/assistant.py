import re

from app.mcp.router import select_tools
from app.mcp.service import get_mcp_data
from app.rag.chain import answer_question, retrieve_context
from app.planner import create_itinerary


def extract_currency_request(question: str) -> tuple[float | None, str, str]:
    """
    Extract amount, source currency and target currency.

    Supports examples such as:
    - Convert INR 50,000 to SGD
    - Convert 200 SGD to INR
    - Convert my budget from USD to SGD
    """

    text = question.lower()

    # Find amount
    amount_match = re.search(
        r"(?:₹|rs\.?|inr|usd|sgd|\$|s\$)\s*([\d,]+(?:\.\d+)?)",
        text,
    )

    amount = None
    if amount_match:
        amount = float(amount_match.group(1).replace(",", ""))
    else:
        # Handles: "200 SGD to INR"
        number_match = re.search(r"\b([\d,]+(?:\.\d+)?)\b", text)
        if number_match:
            amount = float(number_match.group(1).replace(",", ""))

    # Find currencies
    currency_patterns = {
        "INR": r"\b(?:inr|rs\.?|rupees?)\b|₹",
        "SGD": r"\b(?:sgd|singapore dollars?)\b|s\$",
        "USD": r"\b(?:usd|us dollars?|u\.s\. dollars?)\b|\$",
    }

    currencies = []

    for currency, pattern in currency_patterns.items():
        for match in re.finditer(pattern, text):
            currencies.append((match.start(), currency))

    currencies.sort()

    # Default required by our application
    from_currency = "INR"
    to_currency = "SGD"

    if len(currencies) >= 2:
        from_currency = currencies[0][1]
        to_currency = currencies[1][1]

    elif len(currencies) == 1:
        # Look for "to SGD" / "in SGD"
        target_match = re.search(
            r"\b(?:to|in|into)\s+(inr|sgd|usd)\b",
            text,
        )

        if target_match:
            to_currency = target_match.group(1).upper()

            if to_currency == currencies[0][1]:
                from_currency = "INR"
            else:
                from_currency = currencies[0][1]

    return amount, from_currency, to_currency


def is_itinerary_request(question: str) -> bool:
    """Check whether the user is asking for a travel itinerary."""

    phrases = [
        "itinerary",
        "trip plan",
        "plan a trip",
        "plan my trip",
        "suggest an itinerary",
    ]

    question = question.lower()

    return any(phrase in question for phrase in phrases)


def build_weather_answer(weather: dict) -> str:
    """Format weather MCP data for the user."""

    if weather.get("error"):
        return (
            "I'm sorry — the live weather service is unavailable right now. "
            "Please try again shortly."
        )

    daily = weather.get("daily", {})

    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    rain = daily.get("precipitation_probability_max", [])

    lines = []

    for i, date in enumerate(dates):
        if i >= len(max_temps) or i >= len(min_temps):
            continue

        rain_probability = (
            rain[i] if i < len(rain) else None
        )

        rain_text = ""

        if rain_probability is not None:
            rain_text = f" — {rain_probability}% chance of rain"

        lines.append(
            f"- **{date}:** "
            f"{min_temps[i]}°C to {max_temps[i]}°C"
            f"{rain_text}"
        )

    if not lines:
        return "No valid weather information was returned."

    return (
        "### Current Weather Information\n\n"
        "The following information was retrieved from the live weather MCP tool:\n\n"
        + "\n".join(lines)
    )


def build_currency_answer(
    currency: dict,
    amount: float | None,
    from_currency: str,
    to_currency: str,
) -> str:
    """Format currency MCP data for the user."""

    if currency.get("error"):
        if amount is None:
            return (
                f"Please provide the amount you want to convert, "
                f"for example: 'Convert 60,000 {from_currency} "
                f"to {to_currency}'."
            )

        return (
            "I'm sorry — the live currency service is unavailable "
            "right now. Please try again shortly."
        )

    rates = currency.get("rates", {})
    converted_amount = rates.get(to_currency)

    if converted_amount is None:
        return (
            f"No valid exchange rate was returned for "
            f"{from_currency} to {to_currency}."
        )

    date = currency.get("date", "N/A")

    return (
        f"### Currency Information\n\n"
        f"According to the live currency MCP tool, "
        f"**{amount:g} {from_currency}** is approximately "
        f"**{converted_amount} {to_currency}** "
        f"(rate as of {date})."
    )


def run_assistant(
    question: str,
    amount: float | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run the travel assistant using:
    - RAG for destination knowledge
    - MCP for current weather/currency
    - Planner for combined travel recommendations
    - Conversation history for multi-turn context
    """

    if conversation_history is None:
        conversation_history = []

    # 1. Select tools based on user intent
    selected_tools = select_tools(question)

    itinerary_requested = is_itinerary_request(question)

    # 2. Retrieve destination knowledge when RAG is required
    rag_result = None

    needs_planning = (
        itinerary_requested
        or "weather" in selected_tools
        or "currency" in selected_tools
    )

    if "rag" in selected_tools:
        if needs_planning:
            rag_result = retrieve_context(
                question,
                conversation_history,
            )
        else:
            rag_result = answer_question(
                question,
                conversation_history,
            )

    # 3. Get current information from MCP
    mcp_result = {}

    mcp_tools = [
        tool
        for tool in selected_tools
        if tool in {"weather", "currency"}
    ]

    from_currency = "INR"
    to_currency = "SGD"

    if "currency" in mcp_tools:
        parsed_amount, from_currency, to_currency = (
            extract_currency_request(question)
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

    # 4. Generate final response
    if (
        "weather" in selected_tools
        and "rag" not in selected_tools
        and not itinerary_requested
    ):
        final_answer = build_weather_answer(
            mcp_result.get("weather", {})
        )

    elif (
        "currency" in selected_tools
        and "rag" not in selected_tools
        and not itinerary_requested
    ):
        final_answer = build_currency_answer(
            mcp_result.get("currency", {}),
            amount,
            from_currency,
            to_currency,
        )

    elif needs_planning:
        # Combine RAG knowledge + current MCP information
        final_answer = create_itinerary(
            question=question,
            rag_result=rag_result or {},
            mcp_result=mcp_result,
            conversation_history=conversation_history,
        )

    elif rag_result:
        final_answer = rag_result.get("answer")

    elif mcp_result:
        final_answer = str(mcp_result)

    else:
        final_answer = (
            "I couldn't determine how to answer this request."
        )

    # 5. Retain conversation context
    conversation_history.append(
        {
            "user": question,
            "assistant": final_answer,
        }
    )

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