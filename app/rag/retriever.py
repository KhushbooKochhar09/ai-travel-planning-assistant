from app.rag.vectorstore import load_vectorstore


def get_retriever(k=8):
    """Return a diverse retriever for the Singapore knowledge base."""

    vectorstore = load_vectorstore()

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": 20,
            "lambda_mult": 0.5,
        },
    )