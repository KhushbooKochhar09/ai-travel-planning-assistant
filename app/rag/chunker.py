from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(documents):
    """Split loaded documents into focused, meaningful chunks."""

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(documents)

    return chunks