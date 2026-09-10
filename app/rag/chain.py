from langchain_openai import ChatOpenAI

from app.rag.retriever import get_retriever


def create_rag_chain():
    """Create the Singapore RAG question-answering chain."""

    retriever = get_retriever(k=8)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    return retriever, llm


def answer_question(question):
    """Answer a Singapore travel question using retrieved knowledge."""

    retriever, llm = create_rag_chain()

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
        documents = retriever.invoke(question)

    if not documents:
        return {
            "answer": (
                "I don't have enough information in the Singapore "
                "knowledge base to answer this question."
            ),
            "sources": [],
            "context": "",
        }

    context = "\n\n".join(
        document.page_content for document in documents
    )

    prompt = f"""
You are a Singapore travel assistant.

Answer the user's question using ONLY the provided knowledge-base context.

If the context does not contain enough information to answer the question,
clearly say that the knowledge base does not have enough information.

Do not invent facts.

User question:
{question}

Knowledge-base context:
{context}

Answer:
"""

    response = llm.invoke(prompt)

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
        "answer": response.content,
        "sources": sources,
        "context": context,
    }