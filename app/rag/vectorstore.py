from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS

from app.rag.embeddings import create_embeddings


VECTORSTORE_PATH = Path("data/singapore/faiss_index")


def create_vectorstore(chunks):
    """Create and persist a FAISS vector store from document chunks."""

    embeddings = create_embeddings()

    vectorstore = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )

    VECTORSTORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    vectorstore.save_local(str(VECTORSTORE_PATH))

    return vectorstore


@lru_cache(maxsize=1)
def load_vectorstore():
    """Load the persisted Singapore FAISS vector store (cached)."""

    embeddings = create_embeddings()

    return FAISS.load_local(
        str(VECTORSTORE_PATH),
        embeddings,
        allow_dangerous_deserialization=True,
    )
