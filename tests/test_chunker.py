from app.rag.chunker import chunk_documents
from app.rag.loader import load_sources


def test_chunk_documents():
    documents = load_sources()
    chunks = chunk_documents(documents)

    assert len(chunks) > len(documents)

    for chunk in chunks:
        assert chunk.page_content.strip()
        assert chunk.metadata.get("source")
        assert chunk.metadata.get("url")
