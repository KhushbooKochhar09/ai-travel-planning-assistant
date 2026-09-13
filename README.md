
# AI Travel Planning Assistant

A context-aware travel assistant for Singapore. It answers destination questions
from a document knowledge base (RAG) and fetches live weather and currency data
through MCP tools. When a request needs both - for example "plan a 3 day trip next
week and adjust it to the weather" - it combines the knowledge base with the live
forecast into one weather-aware itinerary.

Built as the solution to the AI Travel Planning Assistant assignment.

## Key idea

Stable travel info (attractions, neighbourhoods, transport, sample itineraries)
lives in a knowledge base and is searched with RAG. Fast-changing info (weather,
exchange rates) is fetched live through MCP tools, only when a question needs it.
The knowledge base is never used for live data, and MCP is never used for
destination facts RAG already covers.

## Architecture

```
question (Streamlit chat, app.py)
        |
        v
router decides what's needed  (app/mcp/router.py)
        |
   -----------------------------------
   |                |                |
  RAG          weather tool     currency tool
(app/rag)      (get_weather)   (convert_currency)
   |                |                |
 FAISS          Open-Meteo       Frankfurter
   |                |                |
   -----------------------------------
        |
        v
LLM planner assembles the reply  (app/planner.py)
        |
        v
   answer shown in the chat
```

A router reads the question and picks the sources; RAG handles destination facts,
the two MCP tools handle live data, and an LLM planner combines them into the
final answer.

## Knowledge base sources

Three public pages, listed in data/singapore/sources.json:

1. Wikivoyage - Singapore Travel Guide (districts, attractions, transport, food)
2. Visit Singapore - Essential Travel Information (practical info, climate, services)
3. Visit Singapore - Sample Itineraries (itinerary ideas by trip length)

Each page's title and URL are kept as metadata so answers can show a real citation.

## RAG workflow (app/rag/)

1. loader.py - loads the source pages with WebBaseLoader and tags each with its
   title and URL.
2. chunker.py - splits text into 600-char chunks with 100 overlap
   (RecursiveCharacterTextSplitter).
3. embeddings.py - embeds chunks with OpenAI text-embedding-3-small.
4. vectorstore.py - stores vectors in a local FAISS index.
5. retriever.py - retrieves relevant chunks using MMR search.
6. chain.py - answers using only the retrieved context and returns the sources.
   Itinerary questions run several searches so the planner has enough context.

If the retrieved text doesn't cover the question, the assistant says so instead of
guessing.

## MCP tools

A small MCP server (app/mcp/tools.py, run by app/mcp/weather_server.py) exposes
two tools; the app connects to it as a client via app/mcp/service.py.

- get_weather - current conditions and forecast for Singapore from Open-Meteo.
- convert_currency - converts between currencies via Frankfurter. Not locked to
  one pair, so INR->SGD, SGD->INR and USD->SGD all work. The amount and
  from/to currencies are parsed from the sentence in app/assistant.py
  (parse_currency_request), which understands codes, symbols and names.

Live tool results are labelled as such so they're easy to tell apart from
knowledge-base facts. If a tool fails or a required input is missing, the app
reports it instead of inventing an answer.

## Tool selection

app/mcp/router.py picks sources from the words in the question:

- attractions in Singapore -> RAG
- weather in Singapore -> weather tool
- convert INR 60,000 to SGD -> currency tool
- itinerary adjusted to next week's weather -> RAG + weather
- itinerary within an INR 60,000 budget -> RAG + currency
- itinerary within INR 60,000 and adjusted to the weather -> RAG + weather + currency

No match falls back to RAG.

## Weather-aware itinerary (the main combined feature)

For the required scenario - "create a 3 day Singapore itinerary for next week and
adjust it according to the weather forecast" - the planner (app/planner.py):

- uses RAG for attractions, activities, transport and itineraries
- uses the weather tool for each day's forecast
- on high rain-chance days prefers a supported indoor/cultural option; otherwise
  keeps the outdoor plan and notes the weather may affect it
- says so plainly when no supported indoor alternative exists, and never invents
  attractions, prices, or claims not in the sources

## Prompt and context strategy

Each source has one job, and the prompts keep them separate:

- Knowledge base -> destination facts and supported recommendations
- Weather tool -> current/upcoming weather
- Currency tool -> live exchange rates
- Conversation history -> user preferences and earlier messages

The planner prompt tells the model to use retrieved context for destination facts
only, treat MCP results as the sole source of weather/currency, never state
anything unsupported, flag when the knowledge base is short on info, adjust the
plan to the weather rather than just repeating it, keep preferences across turns,
and separate facts from generated suggestions. History is passed on every turn, so
a preference or budget mentioned earlier carries into later replies.

## Project layout

```
app.py                     Streamlit chat UI
app/
  assistant.py             orchestration + currency parsing
  planner.py               LLM itinerary planner
  rag/                     loader, chunker, embeddings, vectorstore, retriever, chain
  mcp/                     tools, weather_server, router, service, client
data/singapore/
  sources.json             knowledge-base sources
  faiss_index/             saved vector store
tests/                     chunker, loader, MCP integration
requirements.txt, pytest.ini, README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add an OpenAI API key in a .env file (git-ignored):

```
OPENAI_API_KEY=your_api_key_here
```

Run it:

```bash
streamlit run app.py
```

The chat opens in the browser. The MCP server starts automatically as a subprocess
when a tool is needed.

## Tests

```bash
pytest
```

Covers chunking, knowledge-base loading, and MCP integration. The MCP test calls
the real weather and currency APIs, so it needs internet to pass.

## Example questions

```
What are the must-visit attractions in Singapore?          (RAG)
What is the forecast for the next three days?               (weather)
Convert INR 60,000 to SGD.  /  How much is 200 SGD in INR?  (currency)
I have an INR 60,000 budget. Convert it to SGD and suggest a three-day itinerary.
Create a three-day Singapore itinerary for next week and adjust it to the weather.
```

Multi-turn (context is retained):

```
I prefer cultural experiences.
Create a three-day Singapore itinerary.
Reduce the outdoor activities.
I have an INR 60,000 budget.
Now adjust my itinerary according to next week's weather.
```

## Sample questions and application responses

Real responses captured from the running app. Live tool output (weather rates,
exchange rates) reflects the day it was run and will differ on each run.

### 1. RAG destination question

**Q: What are the must-visit attractions in Singapore?**

> Singapore is brimming with incredible attractions... Here are some must-visit
> spots you definitely shouldn't miss:
>
> **Nature and Wildlife** — Singapore Zoo, Night Safari, Gardens by the Bay.
> **Cultural Experiences** — Chinatown (Sri Mariamman Temple), Little India,
> Geylang Serai. **Iconic Landmarks** — Marina Bay Sands, Singapore Flyer,
> Esplanade Theatres. **Scenic Walks** — Merlion to Boat Quay/Clarke Quay, the
> Southern Ridges Walk. **Religious Sites** — Kong Meng San Phor Kark See
> Monastery, Masjid Sultan.
>
> *Sources: Wikivoyage Singapore Travel Guide; Visit Singapore - Essential
> Travel Information*

*Tools selected: `rag`. The answer is grounded in retrieved chunks and cites its
sources.*

### 2. Weather MCP question

**Q: What's the weather in Singapore this week?**

> Here's the latest Singapore forecast (live from the weather tool):
>
> - **2026-09-13:** 24.9°C to 32.2°C — pack an umbrella, 67% chance of rain
> - **2026-09-14:** 24.5°C to 30.2°C — pack an umbrella, 100% chance of rain
> - **2026-09-15:** 24.6°C to 31.7°C — a few showers possible (43% chance of rain)
> - ... (forecast continues)
>
> Expect warm, humid days throughout — light, breathable clothing works best. If
> you'd like, I can plan a day's activities around this forecast.

*Tools selected: `weather`. Live data is labelled "live from the weather tool".*

### 3. Currency MCP question

**Q: Convert INR 60,000 to SGD.**

> At today's live exchange rate, **60000 INR** is about **796.1 SGD** (rate as of
> 2026-09-11).
>
> Would you like me to suggest a three-day Singapore itinerary that fits this
> budget?

*Tools selected: `currency`. The pair and amount are parsed from the sentence.*

### 4. Combined RAG + MCP (required weather-aware itinerary)

**Q: Create a three-day Singapore itinerary for next week and adjust it according
to the weather forecast.**

> Next week, you can expect warm temperatures ranging from 25°C to 32°C, with a
> high chance of rain on all three days (62% to 75% probability) (live forecast).
> Here's a three-day itinerary that balances outdoor activities with cultural
> experiences, keeping the weather in mind.
>
> **Day 1 — Cultural Exploration and Indoor Delights:** National Museum of
> Singapore (indoor, given the 62% chance of rain — live forecast), lunch in
> Chinatown, hawker-centre dinner.
>
> **Day 2 — Nature and Scenic Views:** Southern Ridges Walk in the morning
> (73% chance of rain — live forecast), then the indoor VivoCity Mall, and the
> Singapore Flyer in the evening if the weather permits.
>
> **Day 3 — Relaxation and Local Flavors:** Gardens by the Bay, using the indoor
> Cloud Forest and Flower Dome (75% chance of rain — live forecast); ArtScience
> Museum as a rainy-day alternative near Marina Bay.

*Tools selected: `rag`, `weather`. Destination facts come from RAG; each day's
rain chance comes from the weather tool and is marked "live forecast"; indoor
options are offered on high rain-chance days.*

### 5. Multi-turn conversation (retained context)

**Turn 1 — Q: Create a three-day Singapore itinerary.**

> A three-day plan: Day 1 cultural (Esplanade, Marina Bay, Chinatown), Day 2
> nature (Southern Ridges Walk, Mount Faber), Day 3 shopping and food (Orchard
> Road, Little India), each with the live forecast noted.

**Turn 2 — Q: We are travelling with two young children.**

> That sounds wonderful!... Let's tweak the itinerary to make it more
> kid-friendly: Supertree Grove on Day 1, playgrounds at Mount Faber on Day 2,
> kid-friendly malls on Day 3, plus tips on family-friendly MRT travel, staying
> hydrated, and rest breaks.

**Turn 3 — Q: Make Day 2 mostly indoor.**

> Let's adjust Day 2 to focus on indoor activities... Singapore Science Centre in
> the morning, Snow City for lunch, the Cloud Forest and Flower Dome at Gardens
> by the Bay in the afternoon, and VivoCity in the evening.
