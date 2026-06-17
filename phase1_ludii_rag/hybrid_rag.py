import re
import time
import requests
import numpy as np
from typing import List, Dict
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import os

load_dotenv()

class HybridRAG:
    """RAG Hybride : Neo4j + Embeddings + Gemini 2.5 Flash avec retry"""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        
        # Neo4j
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "salma1234"))
        )
        
        # Embeddings
        print("⏳ Chargement du modèle sémantique...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Modèle chargé")
        
        # Vérifier Gemini
        if use_llm and self.gemini_api_key:
            print(f"✅ Gemini Flash configuré")
        elif use_llm:
            print("⚠️ Pas de clé Gemini, mode sans LLM")
            self.use_llm = False
        
        self._game_embeddings = None
        self._game_names = None
        self._all_games = None
    
    # ========== EMBEDDINGS ==========
    
    def _build_game_embeddings(self):
        if self._game_embeddings is not None:
            return self._game_embeddings, self._game_names, self._all_games
        
        print("⏳ Construction des embeddings...")
        with self.driver.session() as session:
            result = session.run("""
                MATCH (g:Game)
                OPTIONAL MATCH (g)-[:FROM_REGION]->(r:Region)
                OPTIONAL MATCH (g)-[:FROM_PERIOD]->(p:Period)
                OPTIONAL MATCH (g)-[:IN_CATEGORY]->(c:Category)
                RETURN g.name AS name,
                       coalesce(g.description, '') AS description,
                       coalesce(g.origin, '') AS origin,
                       collect(DISTINCT r.name) AS regions,
                       collect(DISTINCT p.name) AS periods,
                       collect(DISTINCT c.name) AS categories
            """)
            self._all_games = [dict(record) for record in result]
        
        self._game_names = []
        texts = []
        for game in self._all_games:
            self._game_names.append(game['name'])
            text = f"Game: {game['name']}. {game['description'][:300]}. Origin: {game['origin']}. "
            text += f"Regions: {', '.join(game['regions'])}. Periods: {', '.join(game['periods'])}."
            texts.append(text)
        
        self._game_embeddings = self.encoder.encode(texts, show_progress_bar=True)
        print(f"✅ {len(self._game_names)} jeux indexés")
        return self._game_embeddings, self._game_names, self._all_games
    
    # ========== ANALYSE ==========
    
    def analyze_question(self, question: str) -> Dict:
        q = question.lower()
        intent = "search"
        if any(w in q for w in ["règle", "regle", "comment jouer"]): intent = "rules"
        elif any(w in q for w in ["origine", "vient", "inventé", "créé", "histoire"]): intent = "origin"
        elif any(w in q for w in ["similaire", "proche", "ressemble"]): intent = "similar"
        elif any(w in q for w in ["liste", "tous les", "quels sont"]): intent = "list"
        
        region_map = {"égypte":"Egypt","egypt":"Egypt","rome":"Rome","grec":"Greece","chine":"China","japon":"Japan","inde":"India","afrique":"Africa","europe":"Europe","amérique":"America","mésopotamie":"Mesopotamia"}
        period_map = {"médiéval":"Medieval","antique":"Ancient","ancien":"Ancient","moderne":"Modern","préhistorique":"Prehistoric"}
        
        detected_region = next((v for k,v in region_map.items() if k in q), None)
        detected_period = next((v for k,v in period_map.items() if k in q), None)
        
        return {"intent": intent, "region": detected_region, "period": detected_period}
    
    # ========== RECHERCHE ==========
    
    def search(self, question: str, top_k: int = 10) -> List[Dict]:
        embeddings, names, all_games = self._build_game_embeddings()
        analysis = self.analyze_question(question)
        
        query_embedding = self.encoder.encode([question])
        similarities = cosine_similarity(query_embedding, embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k * 3:][::-1]
        
        results = []
        with self.driver.session() as session:
            for idx in top_indices:
                if similarities[idx] > 0.15:
                    result = session.run("""
                        MATCH (g:Game {name: $name})
                        OPTIONAL MATCH (g)-[:FROM_REGION]->(r:Region)
                        OPTIONAL MATCH (g)-[:FROM_PERIOD]->(p:Period)
                        OPTIONAL MATCH (g)-[:IN_CATEGORY]->(c:Category)
                        OPTIONAL MATCH (g)-[:HAS_RULESET]->(rs:Ruleset)-[:HAS_YOLO_SIGNATURE]->(sig:YOLOSignature)
                        RETURN g.name AS name, g.description AS description,
                               g.origin AS origin, g.ludCode AS rules,
                               sig.board_cols AS boardCols, sig.board_rows AS boardRows,
                               sig.required_pieces AS pieces,
                               collect(DISTINCT r.name) AS regions,
                               collect(DISTINCT p.name) AS periods,
                               collect(DISTINCT c.name) AS categories
                    """, name=names[idx])
                    record = result.single()
                    if record:
                        results.append({**dict(record), "semantic_score": float(similarities[idx])})
        
        results = self._boost_game_names(question, results)
        if analysis["region"]: results = self._filter_by_region(results, analysis["region"])
        if analysis["period"]: results = self._filter_by_period(results, analysis["period"])
        
        results.sort(key=lambda x: x.get("semantic_score", 0), reverse=True)
        return results[:top_k]
    
    def _boost_game_names(self, question: str, results: List[Dict]) -> List[Dict]:
        q = question.lower()
        for r in results:
            name = r.get("name", "").lower()
            if name in q: r["semantic_score"] = min(1.0, r["semantic_score"] + 0.6)
            else:
                m = sum(1 for w in name.split() if len(w) > 3 and w in q)
                if m > 0: r["semantic_score"] = min(1.0, r["semantic_score"] + 0.2 * m)
        return results
    
    def _filter_by_region(self, results: List[Dict], region: str) -> List[Dict]:
        rl = region.lower()
        for r in results:
            if rl in " ".join([x.lower() for x in r.get("regions", [])]):
                r["semantic_score"] = min(1.0, r["semantic_score"] + 0.4)
        return results
    
    def _filter_by_period(self, results: List[Dict], period: str) -> List[Dict]:
        pl = period.lower()
        for r in results:
            if pl in " ".join([x.lower() for x in r.get("periods", [])]):
                r["semantic_score"] = min(1.0, r["semantic_score"] + 0.4)
        return results
    
    # ========== RÉPONSE AVEC GEMINI + RETRY ==========
    
    def answer(self, question: str) -> Dict:
        analysis = self.analyze_question(question)
        results = self.search(question, top_k=5)
        
        if not results:
            return {"question": question, "answer": "❓ Aucun jeu trouvé.", "results": []}
        
        if self.use_llm and self.gemini_api_key:
            answer_text = self._answer_with_gemini(question, results)
        else:
            answer_text = self._generate_answer(question, analysis, results)
        
        return {"question": question, "intent": analysis["intent"], "answer": answer_text, "results": results[:5]}
    
    def _answer_with_gemini(self, question: str, results: List[Dict]) -> str:
        """Utilise Gemini avec retry automatique"""
        context = "\n".join([
            f"Jeu {i+1}: {g['name']}\nDescription: {g.get('description','N/A')[:300]}\n"
            f"Origine: {g.get('origin','?')}\nRégions: {', '.join(g.get('regions',[]))}\n"
            f"Périodes: {', '.join(g.get('periods',[]))}\n"
            f"Plateau: {g.get('boardCols','?')}×{g.get('boardRows','?')}"
            for i, g in enumerate(results[:5])
        ])
        
        prompt = f"""Tu es un expert en jeux de société historiques et en archéologie ludique.
Réponds en français, de manière claire, structurée et précise.

CONTEXTE:
{context}

QUESTION: {question}

RÉPONSE (en français, avec des émojis):"""
        
        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{self.gemini_url}?key={self.gemini_api_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600}},
                    timeout=20
                )
                
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                elif resp.status_code == 429:
                    wait = (attempt + 1) * 5
                    print(f"⚠️ Rate limit (429), attente {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"⚠️ Erreur Gemini: {resp.status_code}")
                    return self._generate_answer(question, {}, results)
            except Exception as e:
                print(f"⚠️ Exception: {e}")
                if attempt < 2:
                    time.sleep(3)
        
        print("⚠️ Gemini indisponible après 3 tentatives")
        return self._generate_answer(question, {}, results)
    
    # ========== FALLBACK ==========
    
    def _generate_answer(self, question: str, analysis: Dict, results: List[Dict]) -> str:
        top = results[0] if results else {}
        
        if analysis.get("region"):
            return f"📍 **Jeux de {analysis['region']}**: {', '.join([r['name'] for r in results[:10]])}"
        if analysis.get("period"):
            return f"📅 **Jeux {analysis['period']}**: {', '.join([r['name'] for r in results[:10]])}"
        if analysis.get("intent") == "rules":
            return f"🎯 **{top.get('name','')}**\n📖 {top.get('description','')[:400]}\n🗺️ {top.get('boardCols','?')}×{top.get('boardRows','?')}"
        
        return f"🔍 **{len(results)} résultats**: {', '.join([r['name'] for r in results[:10]])}"
    
    def close(self):
        self.driver.close()