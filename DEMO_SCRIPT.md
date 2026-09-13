# Demo Script — Singapore AI Travel Assistant

A short demonstration (aim for ~3–5 minutes) covering RAG, MCP tools, a combined
RAG + MCP response, and multi-turn conversational context. Includes the exact
steps to run the project locally in development mode.

---

## Part A — Run the code locally (development mode)

Do this once before recording so the first response isn't slow (the FAISS index
and the MCP subprocess load on first use).

### Prerequisites

- Python 3.10+ and `git`
- An OpenAI API key (used for embeddings and the LLM planner)
- Internet access (the weather and currency MCP tools call live public APIs)

### Steps

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd ai-travel-planning-assistant

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows (PowerShell)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenAI API key (this .env file is git-ignored)
echo "OPENAI_API_KEY=your_api_key_here" > .env

# 5. (Optional) run the automated tests
pytest

# 6. Start the app in development mode
streamlit run app.py
```

Streamlit opens the chat at `http://localhost:8501`. The MCP server
(`app/mcp/weather_server.py`) starts automatically as a subprocess the first time
a weather or currency tool is needed — no separate command required.

**Notes for evaluators**
- The prebuilt FAISS index is committed under `data/singapore/faiss_index/`, so no
  indexing step is needed to run.
- Live weather/currency values change daily; that's expected and confirms the data
  is fetched live through the MCP tools.

---

## Part B — Recording script (keep it short)

Say the lines in **bold-quote**, do the **Show** actions. Total ~3–5 min.

### 0. Intro (~20 sec)
> "This is my Singapore AI Travel Assistant. It answers destination questions from
> a document knowledge base using RAG, fetches live weather and currency through
> two MCP tools, combines them into a weather-aware itinerary, and keeps context
> across a conversation."

**Show:** `streamlit run app.py` in the terminal, then the chat UI in the browser.

### 1. RAG destination question (~40 sec)
> "First, a knowledge-base question — RAG only."

**Show / type:**
```
What are the must-visit attractions in Singapore?
```
> "The answer is grounded in the retrieved documents, and it cites its sources."

**Show:** expand the **📚 Sources** section (real Wikivoyage / Visit Singapore links).

### 2. Weather MCP (~30 sec)
> "Now live info — this routes to the weather MCP tool, not the knowledge base."

**Show / type:**
```
What's the weather in Singapore this week?
```
> "It comes back live from the MCP tool, labelled 'live from the weather tool',
> and flags high rain-chance days."

### 3. Currency MCP (~25 sec)
> "The second MCP tool handles currency."

**Show / type:**
```
Convert INR 60,000 to SGD.
```
> "It parses the amount and currency pair from my sentence and converts using a
> live rate. Intent decides the tool: attractions to RAG, weather to the weather
> tool, currency to the currency tool."

### 4. Combined RAG + MCP — main feature (~50 sec)
> "Here's the required combined scenario — one question that needs both."

**Show / type:**
```
Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast.
```
> "RAG supplies the attractions and itinerary; the weather tool supplies each
> day's forecast. On high rain-chance days it prefers indoor options like the
> National Museum and the Cloud Forest, and marks every forecast as 'live
> forecast'. Sourced facts, live data, and AI suggestions stay distinct."

### 5. Multi-turn context (~50 sec)
> "Finally, conversational context, built over three turns."

**Show / type one at a time:**
```
Create a three-day Singapore itinerary.
```
```
We are travelling with two young children.
```
> "It kept the same plan and made it kid-friendly instead of starting over."
```
Make Day 2 mostly indoor.
```
> "It changes only Day 2 to indoor activities while remembering both the itinerary
> and the children from earlier turns."

### 6. Close (~15 sec)
> "So: grounded RAG with citations, two live MCP tools, a combined weather-aware
> itinerary, intent-based tool selection, and retained multi-turn context — in a
> simple chat interface. Thanks for watching."

---

## Quick shot list (for editing)

1. Terminal: `streamlit run app.py` → browser opens
2. RAG answer + expanded Sources
3. Weather MCP answer (live label)
4. Currency MCP answer (live rate)
5. Combined weather-aware 3-day itinerary
6. Three-turn conversation showing retained context
