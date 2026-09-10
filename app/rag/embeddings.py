from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


load_dotenv()


def create_embeddings():
    """Create the embedding model used for the Singapore knowledge base."""

    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )
