"""ChromaDB 记忆存储"""
try:
    import chromadb
except ImportError:
    chromadb = None
from src.backend.core.config import get
from src.backend.core.logger import get_logger

log = get_logger("memory")


class Memory:
    def __init__(self):
        if chromadb is None:
            raise ImportError("chromadb is not installed")
        db_path = get("memory.db_path", "data/chromadb")
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("conversations")
        log.info(f"ChromaDB 已初始化: {db_path}")

    def add(self, text: str, metadata: dict | None = None):
        import uuid
        doc_id = uuid.uuid4().hex[:12]
        kwargs = {"documents": [text], "ids": [doc_id]}
        if metadata:
            kwargs["metadatas"] = [metadata]
        self.collection.add(**kwargs)

    def query(self, text: str, n_results: int = 5) -> list[str]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(query_texts=[text], n_results=n_results)
        return results["documents"][0] if results["documents"] else []
