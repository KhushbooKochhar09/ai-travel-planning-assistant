from app.rag.loader import load_sources


def test_load_sources():
    documents = load_sources()

    assert len(documents) > 0

    for document in documents:
        assert document.page_content
        assert document.metadata.get("source")
        assert document.metadata.get("url")
