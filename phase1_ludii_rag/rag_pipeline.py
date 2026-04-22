import chromadb, uuid, json, sys, os
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction
)

# Permet d'importer ludii_parser depuis le même dossier
sys.path.insert(0, os.path.dirname(__file__))
from ludii_parser import LudParser

CHROMA_PATH     = "./phase1_ludii_rag/datasets/chromadb"
EMBED_MODEL     = "all-MiniLM-L6-v2"
COLLECTION_NAME = "ludii_rules"

class LudiiRAG:

    def __init__(self):
        print("Loading embedding model (first run = download ~80MB)...")
        self.embedder = SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedder,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"ChromaDB ready - {self.collection.count()} chunks indexed")

    def ingest_game(self, parsed_game, source="ludii_official"):
        chunks = parsed_game.to_text_chunks()
        if not chunks:
            return
        ids       = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {
                "game_name": parsed_game.name,
                "chunk_idx": str(i),
                "source":    source,
                "players":   str(parsed_game.players or "unknown")
            }
            for i in range(len(chunks))
        ]
        self.collection.upsert(
            ids=ids, documents=chunks, metadatas=metadatas
        )
        print(f"  OK {parsed_game.name} - {len(chunks)} chunks")

    def ingest_from_json(self, json_path: str):
        parser = LudParser()
        with open(json_path, encoding="utf-8") as f:
            games = json.load(f)
        print(f"\nIngesting {len(games)} games into ChromaDB...")
        for g in games:
            if g.get("lud_content") or g.get("rules_text"):
                parsed = parser.parse(
                    g.get("lud_content", ""),
                    g["name"],
                    rules_text=g.get("rules_text", "")
                )
                self.ingest_game(parsed)
        print(f"\nTotal indexed: {self.collection.count()} chunks")

    def retrieve(self, query: str, n_results=3,
                 game_filter=None) -> list:
        count = self.collection.count()
        if count == 0:
            return []
        where = {"game_name": game_filter} if game_filter else None
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where=where,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"Retrieve error: {e}")
            return []
        retrieved = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            retrieved.append({
                "text":       doc,
                "metadata":   meta,
                "similarity": round(1 - dist, 3)
            })
        return retrieved

if __name__ == "__main__":
    rag = LudiiRAG()
    json_path = "./phase1_ludii_rag/datasets/raw_lud/games_index.json"

    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found - run ludii_scraper.py first")
        sys.exit(1)

    if rag.collection.count() == 0:
        rag.ingest_from_json(json_path)
    else:
        print(f"Already indexed ({rag.collection.count()} chunks), skipping.")

    # Test retrieval
    tests = [
        ("how do pieces move in Ludo?", None),
        ("how does the bishop move?", "Chess"),
        ("how to win in Reversi?", "Reversi"),
    ]
    print("\n--- Retrieval tests ---")
    for query, game_filter in tests:
        results = rag.retrieve(query, n_results=2, game_filter=game_filter)
        print(f"\nQuery: '{query}'")
        for r in results:
            print(f"  [{r['similarity']}] "
                  f"[{r['metadata']['game_name']}] "
                  f"{r['text'][:70]}...")