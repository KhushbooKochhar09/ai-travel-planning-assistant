import streamlit as st

from app.assistant import run_assistant


st.set_page_config(
    page_title="Singapore AI Travel Assistant",
    page_icon="✈️",
    layout="centered",
)

st.title("✈️ Singapore AI Travel Assistant")
st.caption("RAG-powered travel knowledge + current MCP information")


if "messages" not in st.session_state:
    st.session_state.messages = []


# Display previous conversation
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            if message.get("tools"):
                st.caption(
                    "Tools used: "
                    + ", ".join(message["tools"])
                )

            if message.get("sources"):
                with st.expander("📚 Knowledge-base sources"):
                    for source in message["sources"]:
                        st.markdown(
                            f"- [{source['title']}]({source['url']})"
                        )


# Chat input
question = st.chat_input(
    "Ask me to plan your Singapore trip..."
)


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

    for index in range(
        0,
        len(st.session_state.messages) - 1,
        2,
    ):
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
        with st.spinner("Planning your trip..."):
            result = run_assistant(
                question,
                conversation_history=conversation_history,
            )

        answer = result.get(
            "answer",
            "Sorry, I could not generate a response.",
        )

        st.markdown(answer)

        # Display selected tools
        tools = result.get("selected_tools", [])

        if tools:
            st.caption(
                "Tools used: "
                + ", ".join(tools)
            )

        # Display RAG sources
        sources = []

        rag_result = result.get("rag")

        if rag_result:
            sources = rag_result.get("sources", [])

        if sources:
            with st.expander("📚 Knowledge-base sources"):
                for source in sources:
                    st.markdown(
                        f"- [{source['title']}]({source['url']})"
                    )

    # Save assistant response to conversation
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "tools": tools,
            "sources": sources,
        }
    )