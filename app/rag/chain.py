from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.rag.retriever import get_retriever


@lru_cache(maxsize=1)
def get_llm():
    """Return a cached LLM instance for answering questions."""

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )


def create_rag_chain():
    """Create the Singapore RAG question-answering chain."""

    retriever = get_retriever(k=8)

    return retriever, get_llm()


def format_conversation_history(conversation_history):
    """Format prior turns into a readable transcript for prompting."""

    if not conversation_history:
        return ""

    lines = []

    for turn in conversation_history:
        user_text = turn.get("user", "")
        assistant_text = turn.get("assistant", "")

        if user_text:
            lines.append(f"User: {user_text}")

        if assistant_text:
            lines.append(f"Assistant: {assistant_text}")

    return "\n".join(lines)


def retrieve_context(question, conversation_history=None):
    """Retrieve relevant knowledge-base context and sources only.

    This performs retrieval without generating an answer, so callers that
    only need the grounding context (such as the itinerary planner) avoid
    an unnecessary LLM call.
    """

    retriever = get_retriever(k=8)

    is_itinerary_request = any(
        phrase in question.lower()
        for phrase in [
            "itinerary",
            "trip plan",
            "plan a trip",
            "suggest an itinerary",
        ]
    )

    if is_itinerary_request:
        retrieval_queries = [
            f"{question} Singapore three day sample itinerary",
            f"{question} Singapore attractions landmarks places to visit",
            f"{question} Singapore neighbourhoods culture food shopping",
            f"{question} Singapore indoor outdoor activities things to do",
            f"{question} Singapore transportation getting around",
        ]

        documents = []

        for query in retrieval_queries:
            documents.extend(retriever.invoke(query))

        unique_documents = []
        seen_chunks = set()

        for document in documents:
            chunk = document.page_content.strip()

            if chunk and chunk not in seen_chunks:
                seen_chunks.add(chunk)
                unique_documents.append(document)

        documents = unique_documents

    else:
        # For follow-up questions, add the previous user turn to the
        # retrieval query so references such as "those" or "there" still
        # retrieve the relevant knowledge-base content.
        retrieval_query = question

        if conversation_history:
            previous_user = conversation_history[-1].get("user", "")

            if previous_user:
                retrieval_query = f"{previous_user} {question}"

        documents = retriever.invoke(retrieval_query)

    context = "\n\n".join(
        document.page_content for document in documents
    )

    sources = []

    for document in documents:
        source = document.metadata.get("source")
        url = document.metadata.get("url")

        if source and source not in [item["title"] for item in sources]:
            sources.append({
                "title": source,
                "url": url,
            })

    return {
        "documents": documents,
        "context": context,
        "sources": sources,
    }


def answer_question(question, conversation_history=None):
    """Answer a Singapore travel question using retrieved knowledge."""

    retrieval = retrieve_context(question, conversation_history)
    documents = retrieval["documents"]

    if not documents:
        return {
            "answer": (
                "I don't have enough information in the Singapore "
                "knowledge base to answer this question."
            ),
            "sources": [],
            "context": "",
        }

    context = retrieval["context"]

    history_text = format_conversation_history(conversation_history)

    prompt = f"""
You are a friendly, knowledgeable Singapore travel assistant.

Answer the user's question in a warm, natural, conversational tone,
the way a real travel assistant would talk to a traveller. Use ONLY
the provided knowledge-base context for any Singapore facts.

Guidelines:
- Write in clear sentences and short paragraphs. Use bullet points
  or light headings only when they genuinely improve readability
  (for example, when listing several attractions).
- Bold a few key place names sparingly.
- Do not use machine-style field labels such as
  "Knowledge-base information:".
- Do not invent facts. If the context does not contain enough
  information to answer, say so honestly and naturally instead of
  guessing. The source references are shown separately below your
  answer, so you do not need to list URLs yourself.
- Use the conversation history only to understand what the user is
  referring to and to preserve their stated preferences. It is NOT a
  source of Singapore facts — every destination fact must still come
  from the knowledge-base context.

Conversation so far:
{history_text}

User question:
{question}

Knowledge-base context:
{context}

Answer:
"""

    response = get_llm().invoke(prompt)

    return {
        "answer": response.content,
        "sources": retrieval["sources"],
        "context": context,
    }