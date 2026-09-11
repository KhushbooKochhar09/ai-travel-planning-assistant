from langchain_openai import ChatOpenAI


def create_planner():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )


def create_itinerary(
    question: str,
    rag_result: dict,
    mcp_result: dict,
    conversation_history: list[dict] | None = None,
) -> str:
    """Create a grounded three-day itinerary using RAG and MCP data."""

    if conversation_history is None:
        conversation_history = []

    rag_context = rag_result.get("context", "")
    rag_sources = rag_result.get("sources", [])

    weather_data = mcp_result.get("weather", {})
    currency_data = mcp_result.get("currency", {})
    daily = weather_data.get("daily", {})

    weather_dates = daily.get("time", [])
    weather_codes = daily.get("weather_code", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    rain_probabilities = daily.get(
        "precipitation_probability_max",
        [],
    )

    weather_values = {
        date: {
            "weather_code": weather_codes[index],
            "max_temp": max_temps[index],
            "min_temp": min_temps[index],
            "rain_probability": rain_probabilities[index],
        }
        for index, date in enumerate(weather_dates)
        if (
            index < len(weather_codes)
            and index < len(max_temps)
            and index < len(min_temps)
            and index < len(rain_probabilities)
        )
    }

    next_week_weather = dict(
        list(weather_values.items())[7:10]
    )

    if not rag_context.strip():
        return (
            "I don't have enough information in the Singapore "
            "knowledge base to create a grounded itinerary."
        )

    source_text = "\n".join(
        f"- {source.get('title')}: {source.get('url')}"
        for source in rag_sources
    )

    prompt = f"""
You are a grounded Singapore travel planning assistant.

Create a useful three-day Singapore itinerary by SYNTHESIZING
multiple relevant pieces of the retrieved knowledge base.

GROUNDING RULES:

1. Use the retrieved knowledge-base context as the ONLY source
   for Singapore destination facts.

2. Use MCP data as the ONLY source for current weather and currency.

3. If currency MCP data is provided, use the converted SGD
   amount as the user's stated trip budget.

4. Do not invent prices or claim that the entire itinerary fits
   within the budget unless the knowledge-base context provides
   enough pricing information to support that conclusion.

5. Do not use pretrained knowledge to add destination facts.

6. Every attraction, neighbourhood, activity, food experience,
   transportation option, or itinerary idea must be supported
   by the retrieved knowledge-base context.

7. You SHOULD combine multiple supported items from the context.
   Do not limit the itinerary to only one attraction when the
   context provides several relevant options.

8. Spread different supported locations and experiences across
   the three days instead of repeatedly recommending the same
   location.

9. Prefer grouping geographically or thematically related
   places when the retrieved context supports such a grouping.

10. Use outdoor activities on days with more favourable weather
   when the context supports those activities.

11. If rain probability is 50% or higher, explicitly adjust the day's
   recommendation rather than only reporting the weather. Prefer a
   supported indoor or cultural activity from the knowledge base.

12. Never assume that a location is indoor or outdoor based only
    on common knowledge.

13. Never invent restaurants, attractions, activities, prices,
    opening hours, events, hotels, transport details, or other
    destination facts.

14. If the knowledge base does not contain enough information
    for a complete day, clearly state that limitation.

15. Conversation history may be used to understand user
    preferences, constraints, and references.

16. If the conversation history contains a clear user preference,
    such as cultural experiences, outdoor activities, family
    travel, food, shopping, or budget sensitivity, PRIORITIZE
    that preference when selecting among the supported
    knowledge-base options.

17. Conversation history is NOT a source of destination facts.
    Any destination-specific recommendation based on a preference
    must still be supported by the retrieved knowledge-base
    context.

18. If a previous preference cannot be satisfied using the
    retrieved knowledge base, explicitly say so rather than
    inventing information.

19. Weather values must come directly from the MCP data below.

20. Clearly label weather information as:
    "Current MCP weather data"

21. Clearly label destination recommendations as:
    "Knowledge-base information"

22. Do not invent an indoor alternative. If none is supported,
    say:
    "The knowledge base does not provide a specific indoor
    alternative for this activity."

23. It is acceptable to provide fewer recommendations rather
    than unsupported information.

RETRIEVED KNOWLEDGE-BASE CONTEXT:
{rag_context}

CURRENT MCP WEATHER DATA:
{next_week_weather}

CURRENT MCP CURRENCY DATA:
{currency_data}

BUDGET RULE:

If currency MCP data is available:
- State the user's original budget.
- State the converted SGD amount.
- Clearly identify the conversion as current MCP currency data.
- Use the converted SGD amount as the planning budget.
- Only discuss specific costs when those costs are explicitly
  present in the knowledge-base context.
- Do not claim that the itinerary fits within the budget unless
  the available pricing information supports that conclusion.

If weather MCP data is not available, do not mention weather
as "not provided" unless the user specifically asked for weather.

CONVERSATION HISTORY:
{conversation_history}

USER PREFERENCES:
- Identify and preserve explicit preferences from the conversation history.
- If the user has expressed a cultural preference, prioritize cultural
  experiences supported by the retrieved knowledge base.
- If the user is travelling with family, prioritize family-suitable activities
  when the retrieved knowledge base supports them.
- If the user has expressed an outdoor preference, prioritize outdoor
  activities when weather conditions allow and the knowledge base supports
  them.
- If the user has provided a budget, use the current MCP currency conversion
  as the planning budget, but do not invent activity or travel costs.
- Do not assume a preference that the user has not expressed.
- Do not invent suitability, facilities, prices, or attractions that are not
  supported by the retrieved knowledge base.
- Never name or recommend an attraction, venue, mall, cultural center,
  restaurant, facility, or activity unless it appears in the retrieved
  knowledge-base context.
- If a suitable indoor alternative is not present in the knowledge base,
  explicitly say that no supported indoor alternative is available.
- Do not use phrases such as "family-friendly" or "suitable for families"
  unless the retrieved knowledge-base context supports that claim.

USER REQUEST:
{question}

Create the itinerary using this structure:

### Three-Day Singapore Itinerary

#### Day 1
- **Knowledge-base information:**
- **Current MCP weather data:** 
- **Current MCP currency data:** 
- **Recommendation:**
- **Indoor alternative if supported:**

#### Day 2
- **Knowledge-base information:**
- **Current MCP weather data:**
- **Current MCP currency data:**
- **Recommendation:**
- **Indoor alternative if supported:**

#### Day 3
- **Knowledge-base information:**
- **Current MCP weather data:**
- **Current MCP currency data:**
- **Recommendation:**
- **Indoor alternative if supported:**

FINAL VALIDATION:
WEATHER ADJUSTMENT REQUIREMENT:

For each day, explain how the weather affects the itinerary.

If rain probability is 50% or higher and a supported indoor or
cultural alternative exists in the knowledge base, prefer that
alternative.

If no supported indoor alternative exists, keep the supported
activity and explicitly explain that the weather may affect it.

Do not merely report the weather. The recommendation must reflect
the weather conditions.
Before producing the answer, perform these checks:

1. For EVERY destination-specific statement, identify the exact
   information in the RETRIEVED KNOWLEDGE-BASE CONTEXT that
   supports it.

2. If you cannot find explicit support in the retrieved context,
   REMOVE the statement.

3. Do NOT add advice based on common travel knowledge.
   For example, do not add advice such as carrying an umbrella,
   checking opening hours, trying a specific dish, or visiting
   a place unless the context explicitly supports it.

4. Do NOT infer that an activity is indoor or outdoor unless the
   context explicitly indicates this.

5. Do NOT infer that a location is suitable for rain merely
   because it contains shopping, dining, or other activities.

6. You MAY combine multiple supported facts from different
   retrieved chunks to create a coherent day.

7. Prefer three different supported sets of locations or
   experiences across the three days when enough information
   exists.

8. Weather recommendations must be based only on the MCP weather
   values supplied above.

9. If a weather-based recommendation cannot be made without
   inventing information, simply state that the available
   knowledge base does not provide enough information for a
   weather-specific alternative.

10. Do not replace removed information with general knowledge.

The final answer must contain only information that can be
traced to either:
- the retrieved knowledge-base context, or
- the supplied MCP weather data.
"""

    response = create_planner().invoke(prompt)

    return response.content