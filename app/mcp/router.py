def select_tools(query: str) -> list[str]:
    """Select the data sources required for a travel query."""

    query_lower = query.lower()

    selected = []

    weather_keywords = [
        "weather",
        "rain",
        "raining",
        "forecast",
        "temperature",
        "sunny",
    ]

    currency_keywords = [
        "currency",
        "convert",
        "exchange rate",
        "inr",
        "sgd",
        "rupees",
        "budget",
        "₹",
        "rs",
        "rupee",
    ]

    travel_keywords = [
        "itinerary",
        "trip",
        "travel",
        "attractions",
        "places",
        "things to do",
        "visit",
        "food",
        "restaurant",
        "transport",
        "neighbourhood",
        "activity",
    ]

    if any(keyword in query_lower for keyword in travel_keywords):
        selected.append("rag")

    if any(keyword in query_lower for keyword in weather_keywords):
        selected.append("weather")

    if any(keyword in query_lower for keyword in currency_keywords):
        selected.append("currency")

    if not selected:
        selected.append("rag")

    return selected
