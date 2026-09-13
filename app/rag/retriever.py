from functools import lru_cache

from app.rag.vectorstore import load_vectorstore


@lru_cache(maxsize=4)
def get_retriever(k=8):
    """Return a diverse retriever for the Singapore knowledge base.

    The vector store and embedding model are loaded once and cached, so
    repeated questions do not reload the FAISS index from disk each time.
    """

    vectorstore = load_vectorstore()

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": 20,
            "lambda_mult": 0.5,
        },
    )