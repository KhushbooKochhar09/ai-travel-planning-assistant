import re

from app.mcp.router import select_tools
from app.mcp.service import get_mcp_data
from app.rag.chain import answer_question
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

    # Retrieve knowledge-base information only when RAG is selected.
    if "rag" in selected_tools:
        rag_result = answer_question(question)

    # Extract INR amount from the user's request when not explicitly supplied.
    if amount is None:
        amount = extract_inr_amount(question)

    # Select only the MCP tools requested by the router.
    mcp_tools = [
        tool
        for tool in selected_tools
        if tool in {"weather", "currency"}
    ]

    if mcp_tools:
        mcp_result = get_mcp_data(
            tools=mcp_tools,
            amount=amount,
        )

    final_answer = None

    # The planner is required when:
    # - current weather/currency information is needed, or
    # - the user explicitly asks for an itinerary/trip plan.
    planner_required = (
        "weather" in selected_tools
        or "currency" in selected_tools
        or "itinerary" in question.lower()
        or "trip plan" in question.lower()
        or "plan a trip" in question.lower()
        or "suggest an itinerary" in question.lower()
    )

    # Weather-only request.
    if (
        "weather" in selected_tools
        and "rag" not in selected_tools
        and not any(
            phrase in question.lower()
            for phrase in [
                "itinerary",
                "trip plan",
                "plan a trip",
                "suggest an itinerary",
            ]
        )
    ):
        weather = mcp_result.get("weather", {})
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
                else "N/A"
            )

            weather_lines.append(
                f"- {date}: {min_temps[index]}°C to "
                f"{max_temps[index]}°C, rain probability "
                f"{rain_probability}%"
            )

        final_answer = (
            "### Singapore Weather Forecast\n\n"
            "Current MCP weather forecast:\n"
            + "\n".join(weather_lines)
            + "\n\n"
            "Source: MCP weather service"
        )

    # Currency-only request.
    elif (
        "currency" in selected_tools
        and "rag" not in selected_tools
        and not any(
            phrase in question.lower()
            for phrase in [
                "itinerary",
                "trip plan",
                "plan a trip",
                "suggest an itinerary",
            ]
        )
    ):
        currency = mcp_result.get("currency", {})

        if currency.get("error"):
            final_answer = (
                "The currency service is currently unavailable."
            )
        else:
            base = currency.get("base", "INR")
            converted_amount = currency.get("rates", {}).get("SGD")
            date = currency.get("date", "N/A")

            final_answer = (
                "### Currency Conversion\n\n"
                f"MCP currency data: {amount:g} {base} = "
                f"{converted_amount} SGD.\n\n"
                f"Exchange-rate date: {date}\n"
                "Source: MCP currency service"
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