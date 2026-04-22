import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from rag_pipeline  import LudiiRAG
from ludii_scraper import LudiiScraper
from ludii_parser  import LudParser
from dotenv import load_dotenv
load_dotenv()


class LudiiNLPPipeline:

    def __init__(self):
        self.rag     = LudiiRAG()
        self.scraper = LudiiScraper()
        self.parser  = LudParser()
        self.api_key = os.getenv("GROQ_API_KEY", "")

        if not self.api_key:
            print("WARNING: GROQ_API_KEY not found in .env")
        else:
            print(f"Groq API key loaded: {self.api_key[:8]}...")

    # ── KNOWLEDGE BASE ──────────────────────────────────────

    def build_knowledge_base(self, limit=5):
        """Scrape + parse + ingère dans ChromaDB"""
        if self.rag.collection.count() > 0:
            print(f"Already {self.rag.collection.count()} "
                  f"chunks - skipping build.")
            return

        print("Building knowledge base...")
        try:
            games_data = self.scraper.scrape_all(limit=limit)
        except Exception:
            games_data = self.scraper.get_fallback_games()

        for g in games_data:
            parsed = self.parser.parse(
                g.get("lud_content", ""),
                g["name"],
                rules_text=g.get("rules_text", "")
            )
            self.rag.ingest_game(parsed)

        print(f"Knowledge base ready - "
              f"{self.rag.collection.count()} chunks")

    # ── COMPLETION ──────────────────────────────────────────

    def complete_damaged_rule(self, damaged_rule: str,
                               game_name: str = None) -> dict:
        """RAG + Groq LLM pour compléter une règle endommagée"""

        # 1. Retrieval
        query = (f"{game_name}: {damaged_rule}"
                 if game_name else damaged_rule)
        context = self.rag.retrieve(
            query, n_results=3, game_filter=game_name
        )
        if not context:
            context = self.rag.retrieve(damaged_rule, n_results=3)
        if not context:
            return {
                "completed_rule": damaged_rule,
                "confidence":     0.0,
                "sources":        [],
                "context_used":   []
            }

        # 2. Prompt augmenté
        ctx_text = "\n".join(
            f"[{c['metadata']['game_name']}] {c['text']}"
            for c in context
        )
        prompt = (
            "You are a board game rules expert.\n"
            "Using these official Ludii game rules as context, "
            "complete the damaged rule.\n\n"
            f"CONTEXT:\n{ctx_text}\n\n"
            f"DAMAGED RULE:\n{damaged_rule}\n\n"
            "Write ONLY the completed rule, nothing else."
        )

        # 3. Groq LLM
        completed = self._call_llm(prompt)
        avg_sim   = sum(c["similarity"] for c in context) / len(context)
        sources   = list({c["metadata"]["game_name"] for c in context})

        return {
            "completed_rule": completed,
            "confidence":     round(avg_sim, 3),
            "sources":        sources,
            "context_used":   context
        }

    # ── GROQ API CALL ───────────────────────────────────────

    def _call_llm(self, prompt: str) -> str:
        """Appel Groq API — Llama3 gratuit"""
        if not self.api_key:
            return "[Add GROQ_API_KEY to .env]"
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",   # modèle gratuit Groq
                messages=[
                    {
                        "role":    "system",
                        "content": "You are a board game rules expert. "
                                   "Complete damaged rules concisely."
                    },
                    {
                        "role":    "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.3   # bas = réponses plus précises
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[Groq error: {e}]"

    # ── EVALUATION ──────────────────────────────────────────

    def evaluate_on_dataset(self, dataset_path: str,
                             n_samples=10) -> dict:
        """Évalue le pipeline sur le dataset endommagé"""
        import json

        with open(dataset_path, encoding="utf-8") as f:
            dataset = json.load(f)

        samples = dataset[:n_samples]
        scores  = []

        print(f"\nEvaluating on {len(samples)} samples...")
        for item in samples:
            result = self.complete_damaged_rule(
                item["damaged"],
                game_name=item["game"]
            )
            original_words  = set(item["original"].lower().split())
            completed_words = set(
                result["completed_rule"].lower().split()
            )
            overlap = (len(original_words & completed_words) /
                       len(original_words)
                       if original_words else 0)
            scores.append({
                "game":       item["game"],
                "strategy":   item["strategy"],
                "overlap":    round(overlap, 3),
                "confidence": result["confidence"]
            })

        avg_overlap = sum(s["overlap"]     for s in scores) / len(scores)
        avg_conf    = sum(s["confidence"]  for s in scores) / len(scores)

        print(f"\nResults on {len(scores)} samples:")
        print(f"  Avg overlap    : {avg_overlap:.3f}")
        print(f"  Avg confidence : {avg_conf:.3f}")

        return {
            "scores":          scores,
            "avg_overlap":     round(avg_overlap, 3),
            "avg_confidence":  round(avg_conf, 3)
        }


# ── MAIN ────────────────────────────────────────────────────

if __name__ == "__main__":

    pipeline = LudiiNLPPipeline()

    # Étape 1 : base de connaissances
    pipeline.build_knowledge_base(limit=5)

    # Étape 2 : tests de complétion
    tests = [
        ("Players take turns rolling ___. Move ___ spaces forward.",
         "Ludo"),
        ("Bishops move ___ any number of squares.",
         "Chess"),
        ("Trap opponent ___ between yours to ___ them.",
         "Reversi"),
        ("Pieces move ___ forward one square.",
         "Checkers"),
    ]

    print("\n" + "="*55)
    print("COMPLETION TESTS")
    print("="*55)

    for damaged, game in tests:
        r = pipeline.complete_damaged_rule(
            damaged, game_name=game
        )
        print(f"\n[{game}]")
        print(f"  Input      : {damaged}")
        print(f"  Completed  : {r['completed_rule']}")
        print(f"  Confidence : {r['confidence']}")
        print(f"  Sources    : {r['sources']}")

    # Étape 3 : évaluation sur dataset
    dataset_path = (
        "./phase1_ludii_rag/datasets/eval_dataset.json"
    )
    if os.path.exists(dataset_path):
        print("\n" + "="*55)
        print("EVALUATION ON DAMAGED DATASET")
        print("="*55)
        pipeline.evaluate_on_dataset(dataset_path, n_samples=10)
    else:
        print("\nDataset not found - run create_damaged_dataset.py first")