"""
One-time setup: creates the Pinecone index used for RAG over SEC filings
(see docs/ARCHITECTURE.md "RAG over SEC filings" once that section exists).

Run once, by hand:
    python api/utils/create_pinecone_index.py

Safe to re-run - pc.has_index() makes it a no-op if the index already exists.
"""
import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone

# Load .env explicitly from api/ directory
env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(env_path)

INDEX_NAME = "sec-filings"


def create_index():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY not found in api/.env")
        sys.exit(1)

    pc = Pinecone(api_key=api_key)

    if pc.has_index(INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists - nothing to do.")
        return

    print(f"Creating index '{INDEX_NAME}' (model: llama-text-embed-v2, region: aws/us-east-1)...")
    pc.create_index_for_model(
        name=INDEX_NAME,
        cloud="aws",
        region="us-east-1",
        embed={"model": "llama-text-embed-v2", "field_map": {"text": "chunk_text"}},
    )
    print(f"Created index '{INDEX_NAME}'.")


if __name__ == "__main__":
    create_index()
