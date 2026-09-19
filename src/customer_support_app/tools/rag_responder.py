import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from customer_support_app.config import get_embeddings, get_settings

logger = logging.getLogger(__name__)

TIERS = ("free", "paid")


class HelpCenterAgent:
    def __init__(self):
        settings = get_settings()
        self._tier_dirs = {
            tier: (settings.assets_dir / tier, settings.chroma_dir / tier) for tier in TIERS
        }
        self._dbs = {
            tier: self._create_index(tier, source_dir, persist_dir)
            for tier, (source_dir, persist_dir) in self._tier_dirs.items()
        }

    def _create_index(self, tier: str, source_dir: Path, persist_dir: Path):
        embeddings = get_embeddings()

        # Chroma.from_documents has no id-based dedup: calling it against an
        # existing persist_dir on every process start (every Streamlit
        # session, every CLI run) would re-embed and re-insert the same
        # documents each time, silently accumulating duplicate chunks and
        # degrading retrieval. Reuse the persisted collection if it's
        # already populated instead of reindexing unconditionally.
        vectordb = Chroma(
            embedding_function=embeddings, persist_directory=str(persist_dir)
        )
        if vectordb._collection.count() > 0:
            self._warn_if_stale(tier, vectordb, source_dir)
            return vectordb

        return self._build_index(source_dir, persist_dir, embeddings)

    @classmethod
    def _build_index(cls, source_dir: Path, persist_dir: Path, embeddings):
        chunks, ids = cls.load_chunks(source_dir)
        return Chroma.from_documents(
            documents=chunks, embedding=embeddings, ids=ids, persist_directory=str(persist_dir)
        )

    def free_sub_retriever(self):
        return self._dbs["free"].as_retriever()

    def paid_sub_retriever(self):
        return self._dbs["paid"].as_retriever()

    def reindex(self, tiers: Iterable[str] = TIERS) -> Dict[str, int]:
        """Drops and rebuilds the given tiers' collections from assets/.

        Returns the number of chunks indexed per tier. This is the supported way
        to pick up KB edits; it does not need the index directory deleted by hand.
        """
        counts = {}
        for tier in tiers:
            source_dir, persist_dir = self._tier_dirs[tier]
            self._dbs[tier].delete_collection()
            self._dbs[tier] = self._build_index(source_dir, persist_dir, get_embeddings())
            counts[tier] = self._dbs[tier]._collection.count()
        return counts

    def index_status(self, tier: str) -> Dict[str, object]:
        """Compares a tier's persisted index against the current assets/ text.

        Chunks are compared by (file name, text), not by id, so indexes built
        before stable ids existed are judged on content.
        """
        source_dir, _ = self._tier_dirs[tier]
        return self._compare(self._dbs[tier], source_dir)

    @classmethod
    def _compare(cls, vectordb, source_dir: Path) -> Dict[str, object]:
        chunks, _ = cls.load_chunks(source_dir)
        expected = Counter((Path(c.metadata["source"]).name, c.page_content) for c in chunks)
        stored = vectordb._collection.get(include=["documents", "metadatas"])
        actual = Counter(
            (Path(meta["source"]).name, text)
            for text, meta in zip(stored["documents"], stored["metadatas"])
        )
        missing = sum((expected - actual).values())
        extra = sum((actual - expected).values())
        return {
            "ok": missing == 0 and extra == 0,
            "missing": missing,
            "extra": extra,
            "expected_chunks": sum(expected.values()),
            "indexed_chunks": sum(actual.values()),
        }

    def _warn_if_stale(self, tier: str, vectordb, source_dir: Path) -> None:
        status = self._compare(vectordb, source_dir)
        if not status["ok"]:
            logger.warning(
                "Knowledge-base index for the '%s' tier is out of date with assets/ "
                "(%d chunks missing, %d stale) - answers will use the old content. "
                "Rebuild with: python scripts/reindex_kb.py",
                tier,
                status["missing"],
                status["extra"],
            )

    @classmethod
    def load_docs(cls, directory: Path):
        """
        Load documents from the given directory.
        """
        # The knowledge base is plain .txt files - use TextLoader directly
        # rather than DirectoryLoader's default `unstructured`-based loader,
        # whose generic NLP partitioning pipeline is extremely slow overkill
        # for plain text and can take many minutes for even a handful of files.
        loader = DirectoryLoader(
            str(directory),
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()

        return documents

    @classmethod
    def split_docs(cls, documents, chunk_size=2000, chunk_overlap=500):
        """
        Split the documents into chunks.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        docs = text_splitter.split_documents(documents)

        return docs

    @classmethod
    def load_chunks(cls, directory: Path) -> Tuple[List, List[str]]:
        """Chunks for every file under `directory`, with stable ids.

        Files are processed in sorted order and each chunk is named
        "<path relative to directory>#<chunk number>", so rebuilding from
        unchanged assets always produces identical ids, on any machine.
        """
        directory = Path(directory).resolve()
        documents = sorted(cls.load_docs(directory), key=lambda d: str(d.metadata["source"]))
        chunks = cls.split_docs(documents)
        counters: Dict[str, int] = defaultdict(int)
        ids = []
        for chunk in chunks:
            rel = Path(chunk.metadata["source"]).resolve().relative_to(directory).as_posix()
            ids.append(f"{rel}#{counters[rel]}")
            counters[rel] += 1
        return chunks, ids
