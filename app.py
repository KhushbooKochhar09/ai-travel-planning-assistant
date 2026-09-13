import streamlit as st

from app.assistant import run_assistant


st.set_page_config(
    page_title="Singapore AI Travel Assistant",
    page_icon="✈️",
    layout="centered",
)


EXAMPLE_QUESTIONS = [
    ("Must-visit attractions", "What are the must-visit attractions in Singapore?"),
    ("Culture & food areas", "Which neighbourhoods are best for culture and food?"),
    ("Family activities", "Suggest fun activities for a family with children"),
    ("This week's weather", "What's the weather in Singapore this week?"),
    ("Budget in SGD + plan", "Convert ₹60,000 to SGD and suggest a 3-day itinerary"),
    ("3-day weather-aware trip", "Plan a 3-day Singapore trip and adjust it to the weather forecast"),
]


if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None


def submit_example(text):
    """Queue an example question to be answered on the next rerun."""

    st.session_state.pending_question = text


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("✈️ Singapore AI Travel Assistant")
st.caption("Your smart guide for planning the perfect Singapore trip")


# ---------------------------------------------------------------------------
# Example questions (compact, always visible)
# ---------------------------------------------------------------------------
st.caption("💡 Quick ideas:")

columns = st.columns(3)

for index, (label, question_text) in enumerate(EXAMPLE_QUESTIONS):
    columns[index % 3].button(
        label,
        key=f"example_{index}",
        on_click=submit_example,
        args=(question_text,),
        use_container_width=True,
    )


def render_sources(sources):
    """Render source references inside a collapsible section."""

    if sources:
        with st.expander("📚 Sources"):
            for source in sources:
                st.markdown(
                    f"- [{source['title']}]({source['url']})"
                )


# ---------------------------------------------------------------------------
# Display previous conversation
# ---------------------------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            render_sources(message.get("sources"))


# ---------------------------------------------------------------------------
# Handle input (typed question or a clicked example)
# ---------------------------------------------------------------------------
typed_question = st.chat_input("Ask me to plan your Singapore trip...")

question = typed_question or st.session_state.pending_question
st.session_state.pending_question = None


if question:
    # Add user message to conversation
    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Build conversation history from previous turns
    conversation_history = []

    for index in range(0, len(st.session_state.messages) - 1, 2):
        user_message = st.session_state.messages[index]
        assistant_message = st.session_state.messages[index + 1]

        conversation_history.append(
            {
                "user": user_message["content"],
                "assistant": assistant_message["content"],
            }
        )

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Putting together your travel plan..."):
            result = run_assistant(
                question,
                conversation_history=conversation_history,
            )

        answer = result.get(
            "answer",
            "Sorry, I could not generate a response.",
        )

        st.markdown(answer)

        sources = []
        rag_result = result.get("rag")

        if rag_result:
            sources = rag_result.get("sources", [])

        render_sources(sources)

    # Save assistant response to conversation
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )
