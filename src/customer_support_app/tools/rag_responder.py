from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from customer_support_app.config import get_embeddings, get_settings


class HelpCenterAgent:
    def __init__(self):
        settings = get_settings()
        self._free_sub_db = self._create_index(
            source_dir=settings.assets_dir / "free",
            persist_dir=settings.chroma_dir / "free",
        )
        self._paid_sub_db = self._create_index(
            source_dir=settings.assets_dir / "paid",
            persist_dir=settings.chroma_dir / "paid",
        )

    def _create_index(self, source_dir: Path, persist_dir: Path):
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
            return vectordb

        docs = self.split_docs(self.load_docs(source_dir))
        return Chroma.from_documents(
            documents=docs, embedding=embeddings, persist_directory=str(persist_dir)
        )

    def free_sub_retriever(self):
        return self._free_sub_db.as_retriever()

    def paid_sub_retriever(self):
        return self._paid_sub_db.as_retriever()

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
