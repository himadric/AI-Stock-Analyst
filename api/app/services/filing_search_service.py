"""
Semantic search over SEC filings, via Pinecone's integrated embedding
(the index and model are pinned in api/utils/create_pinecone_index.py).

Pinecone embeds text itself (llama-text-embed-v2) at both upsert and query
time - this service only chunks text and talks to the index; it never
calls an embeddings API directly, and never writes anything to MongoDB.

One namespace per ticker. A record's _id is `{ticker}-{accessionNumber}-{i}`,
so re-ingesting the same filing is a harmless no-op upsert, not a duplicate.
"""
import os
from app.services.sec import SECService

INDEX_NAME = "sec-filings"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
UPSERT_BATCH_SIZE = 96  # Pinecone's documented limit for upsert_records


class FilingSearchService:
    def __init__(self):
        self.sec_service = SECService()
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index = None
        if not self.api_key:
            print("Warning: PINECONE_API_KEY not found in environment. Filing search is disabled.")
            return
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=self.api_key)
            self.index = pc.Index(name=INDEX_NAME)
        except Exception as e:
            print(f"Warning: could not connect to Pinecone index '{INDEX_NAME}': {e}")

    def _chunk(self, text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + size])
            start += size - overlap
        return chunks

    def _batches(self, items: list, batch_size: int = UPSERT_BATCH_SIZE):
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]

    def ingest_filing(self, ticker: str, filing: dict) -> dict:
        """
        Ingests ONE filing (dict shaped like an item from SECService.get_filings,
        or the request body of POST /api/agent/ingest_filing: accessionNumber,
        form, filingDate, link). Used directly by the on-demand upload button,
        and in a loop by ingest_ticker_filings() below.
        """
        if not self.index:
            return {"status": "error", "message": "Pinecone is not configured (missing PINECONE_API_KEY)"}

        link = filing.get("link") or filing.get("url")
        accession = filing.get("accessionNumber") or filing.get("accession_number")
        if not link or not accession:
            return {"status": "error", "message": "filing needs at least accessionNumber and link"}

        text = self.sec_service.get_filing_text(link)
        if not text:
            return {"status": "error", "message": "Could not fetch filing text"}

        chunks = self._chunk(text)
        records = [
            {
                "_id": f"{ticker}-{accession}-{i}",
                "chunk_text": chunk,
                "form_type": filing.get("form") or filing.get("form_type") or "",
                "filed_date": filing.get("filingDate") or filing.get("filed_date") or "",
                "url": link,
            }
            for i, chunk in enumerate(chunks)
        ]

        try:
            for batch in self._batches(records):
                self.index.upsert_records(records=batch, namespace=ticker)
        except Exception as e:
            return {"status": "error", "message": f"Pinecone upsert failed: {e}"}

        return {"status": "ingested", "ticker": ticker, "accessionNumber": accession, "chunks": len(records)}

    def ingest_ticker_filings(self, ticker: str, max_filings: int = 2) -> dict:
        """
        Lazy-path fallback used by search_filings() when a ticker's namespace
        is empty - ingests the most recent `max_filings` filings. Kept as its
        own function (not inlined into search_filings) so it can also be
        called directly, e.g. to pre-populate a watchlist ahead of time.
        """
        filings = self.sec_service.get_filings(ticker)
        if isinstance(filings, dict) and "error" in filings:
            return {"status": "error", "message": filings["error"]}
        results = [self.ingest_filing(ticker, f) for f in filings[:max_filings]]
        return {"ingested": results}

    def _has_data(self, ticker: str) -> bool:
        try:
            stats = self.index.describe_index_stats()
            namespaces = stats.namespaces or {}
            return ticker in namespaces and namespaces[ticker].vector_count > 0
        except Exception as e:
            print(f"Warning: describe_index_stats failed: {e}")
            return False

    def get_indexed_status(self, ticker: str, accession_numbers: list[str]) -> dict[str, bool]:
        """
        Checks which of the given filings (by accessionNumber) are already
        indexed, in ONE Pinecone call - fetch() only returns ids that actually
        exist, so checking each filing's first chunk id is enough to know
        whether that filing was ingested. Used by the Overview page to show
        the upload button as already-done instead of re-offering it.
        """
        if not self.index or not accession_numbers:
            return {acc: False for acc in accession_numbers}
        ids = [f"{ticker}-{acc}-0" for acc in accession_numbers]
        try:
            result = self.index.fetch(ids=ids, namespace=ticker)
            found = set(result.vectors.keys())
        except Exception as e:
            print(f"Warning: fetch for indexed-status check failed: {e}")
            return {acc: False for acc in accession_numbers}
        return {acc: f"{ticker}-{acc}-0" in found for acc in accession_numbers}

    def search_filings(self, ticker: str, query: str, limit: int = 5) -> dict:
        if not self.index:
            return {"error": "Pinecone is not configured (missing PINECONE_API_KEY)"}

        if not self._has_data(ticker):
            self.ingest_ticker_filings(ticker)

        try:
            results = self.index.search(
                namespace=ticker,
                inputs={"text": query},
                top_k=limit,
                fields=["chunk_text", "form_type", "filed_date", "url"],
            )
        except Exception as e:
            return {"error": f"Pinecone search failed: {e}"}

        hits = results["result"]["hits"]
        return {
            "ticker": ticker,
            "query": query,
            "matches": [
                {
                    "score": hit["score"],
                    "chunk_text": hit["fields"].get("chunk_text", ""),
                    "form_type": hit["fields"].get("form_type", ""),
                    "filed_date": hit["fields"].get("filed_date", ""),
                    "url": hit["fields"].get("url", ""),
                }
                for hit in hits
            ],
        }
