import re
import numpy as np
from typing import List, Dict
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import os

load_dotenv()

class HybridRAG:
    """RAG Hybride : Graph Neo4j + Embeddings légers (all-MiniLM-L6-v2)"""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "salma1234"))
        )
        
        print("⏳ Chargement du modèle sémantique...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Modèle chargé")
        
        self._game_embeddings = None
        self._game_names = None
        self._all_games = None
    
    # ========== CONSTRUCTION DES EMBEDDINGS ==========
    
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
            text += f"Regions: {', '.join(game['regions'])}. "
            text += f"Periods: {', '.join(game['periods'])}."
            texts.append(text)
        
        self._game_embeddings = self.encoder.encode(texts, show_progress_bar=True)
        print(f"✅ {len(self._game_names)} jeux indexés")
        return self._game_embeddings, self._game_names, self._all_games
    
    # ========== ANALYSE DE QUESTION ==========
    
    def analyze_question(self, question: str) -> Dict:
        """Analyse la question pour déterminer l'intention et les entités"""
        q = question.lower()
        
        # Intentions
        intent = "search"
        if any(w in q for w in ["règle", "regle", "comment jouer", "comment on joue"]):
            intent = "rules"
        elif any(w in q for w in ["origine", "vient", "inventé", "créé", "apparu", "histoire"]):
            intent = "origin"
        elif any(w in q for w in ["similaire", "proche", "ressemble", "semblable"]):
            intent = "similar"
        elif any(w in q for w in ["liste", "tous les", "quels sont", "donne moi", "quels jeu"]):
            intent = "list"
        
        # Régions mentionnées
        region_keywords = {
            "égypte": "Egypt", "egypt": "Egypt", "égyptien": "Egypt",
            "rome": "Rome", "romain": "Rome",
            "grec": "Greece", "grèce": "Greece",
            "chine": "China", "chinois": "China",
            "japon": "Japan", "japonais": "Japan",
            "inde": "India", "indien": "India",
            "afrique": "Africa", "africain": "Africa",
            "europe": "Europe", "européen": "Europe",
            "mésopotamie": "Mesopotamia", "mesopotamia": "Mesopotamia",
            "asie": "Asia", "asiatique": "Asia",
            "amérique": "America", "américain": "America",
        }
        
        detected_region = None
        for kw, region in region_keywords.items():
            if kw in q:
                detected_region = region
                break
        
        # Périodes mentionnées
        period_keywords = {
            "médiéval": "Medieval", "medieval": "Medieval",
            "antique": "Ancient", "ancien": "Ancient",
            "moderne": "Modern", "modern": "Modern",
            "préhistorique": "Prehistoric", "prehistoric": "Prehistoric",
            "renaissance": "Renaissance",
            "contemporain": "Contemporary",
        }
        
        detected_period = None
        for kw, period in period_keywords.items():
            if kw in q:
                detected_period = period
                break
        
        return {
            "intent": intent,
            "region": detected_region,
            "period": detected_period,
            "question": question
        }
    
    # ========== RECHERCHE HYBRIDE ==========
    
    def search(self, question: str, top_k: int = 10) -> List[Dict]:
        """Recherche hybride : sémantique + boost noms + filtre région/période"""
        embeddings, names, all_games = self._build_game_embeddings()
        analysis = self.analyze_question(question)
        
        # 1. Recherche sémantique
        query_embedding = self.encoder.encode([question])
        similarities = cosine_similarity(query_embedding, embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k * 3:][::-1]  # Plus de candidats
        
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
        
        # 2. Booster les noms de jeux présents dans la question
        results = self._boost_game_names(question, results)
        
        # 3. Filtrer par région si mentionnée
        if analysis["region"]:
            results = self._filter_by_region(results, analysis["region"])
        
        # 4. Filtrer par période si mentionnée
        if analysis["period"]:
            results = self._filter_by_period(results, analysis["period"])
        
        # 5. Trier et limiter
        results.sort(key=lambda x: x.get("semantic_score", 0), reverse=True)
        return results[:top_k]
    
    def _boost_game_names(self, question: str, results: List[Dict]) -> List[Dict]:
        """Booste les résultats dont le nom apparaît dans la question"""
        q = question.lower()
        
        for result in results:
            name = result.get("name", "").lower()
            # Boost si le nom exact est dans la question
            if name in q:
                result["semantic_score"] = min(1.0, result["semantic_score"] + 0.6)
            # Boost si des mots du nom sont dans la question
            else:
                name_words = name.split()
                matches = sum(1 for w in name_words if len(w) > 3 and w in q)
                if matches > 0:
                    result["semantic_score"] = min(1.0, result["semantic_score"] + 0.2 * matches)
        
        return results
    
    def _filter_by_region(self, results: List[Dict], region: str) -> List[Dict]:
        """Filtre et booste les résultats par région"""
        region_lower = region.lower()
        for result in results:
            regions = [r.lower() for r in result.get("regions", [])]
            if region_lower in " ".join(regions):
                result["semantic_score"] = min(1.0, result["semantic_score"] + 0.4)
        return results
    
    def _filter_by_period(self, results: List[Dict], period: str) -> List[Dict]:
        """Filtre et booste les résultats par période"""
        period_lower = period.lower()
        for result in results:
            periods = [p.lower() for p in result.get("periods", [])]
            if period_lower in " ".join(periods):
                result["semantic_score"] = min(1.0, result["semantic_score"] + 0.4)
        return results
    
    # ========== GÉNÉRATION DE RÉPONSE ==========
    
    def answer(self, question: str) -> Dict:
        """Répond à une question en langage naturel"""
        analysis = self.analyze_question(question)
        results = self.search(question, top_k=10)
        
        if not results:
            return {
                "question": question,
                "answer": "❓ Aucun jeu trouvé dans la base de données.",
                "results": []
            }
        
        top = results[0]
        answer_text = self._generate_answer(question, analysis, results)
        
        return {
            "question": question,
            "intent": analysis["intent"],
            "region_detected": analysis["region"],
            "period_detected": analysis["period"],
            "answer": answer_text,
            "results": results[:5]
        }
    
    def _generate_answer(self, question: str, analysis: Dict, results: List[Dict]) -> str:
        """Génère une réponse textuelle en français"""
        top = results[0]
        intent = analysis["intent"]
        
        # Si recherche par région
        if analysis["region"]:
            region_games = [r for r in results if analysis["region"].lower() in 
                          " ".join([reg.lower() for reg in r.get("regions", [])])]
            if region_games:
                names = [r['name'] for r in region_games[:10]]
                return f"""
📍 **Jeux de {analysis['region']}** ({len(region_games)} trouvés)

{chr(10).join([f'• **{name}**' for name in names])}

🏆 **Le plus connu : {names[0]}**
📖 {region_games[0].get('description', '')[:300]}
"""
        
        # Si recherche par période
        if analysis["period"]:
            period_games = [r for r in results if analysis["period"].lower() in 
                          " ".join([p.lower() for p in r.get("periods", [])])]
            if period_games:
                names = [r['name'] for r in period_games[:10]]
                return f"""
📅 **Jeux de la période {analysis['period']}** ({len(period_games)} trouvés)

{chr(10).join([f'• **{name}**' for name in names])}
"""
        
        # Règles d'un jeu spécifique
        if intent == "rules":
            rules = self._parse_rules(top.get("rules", ""))
            return f"""
🎯 **Règles de {top['name']}**

📖 {top.get('description', '')[:400]}

🗺️ **Plateau :** {top.get('boardCols', '?')}×{top.get('boardRows', '?')}
♟️ **Pièces :** {', '.join(top.get('pieces', []) or [])}

📜 **Règles :**
{rules}

🌍 **Origine :** {top.get('origin', 'Inconnue')}
📍 **Régions :** {', '.join(top.get('regions', []))}
📅 **Périodes :** {', '.join(top.get('periods', []))}
"""
        
        # Origine
        if intent == "origin":
            return f"""
🌍 **Origine de {top['name']}**

📍 **Régions :** {', '.join(top.get('regions', []))}
📅 **Périodes :** {', '.join(top.get('periods', []))}
🏷️ **Catégories :** {', '.join(top.get('categories', []))}

📖 {top.get('description', '')[:400]}

🔗 **Jeux similaires :** {', '.join([r['name'] for r in results[1:6]])}
"""
        
        # Similitude
        if intent == "similar":
            names = [r['name'] for r in results[1:6]]
            return f"""
🔄 **Jeux similaires à {top['name']}**

{chr(10).join([f'• **{name}**' for name in names])}

Ces jeux partagent des régions, périodes ou catégories communes avec {top['name']}.
"""
        
        # Réponse générique
        names = [r['name'] for r in results[:10]]
        return f"""
🔍 **Résultats pour : "{question}"**

**Meilleur match : {top['name']}** (score: {top.get('semantic_score', 0):.0%})

{chr(10).join([f'• {r["name"]} ({r.get("semantic_score", 0):.0%})' for r in results[:10]])}

📖 {top.get('description', '')[:300]}
"""
    
    def _parse_rules(self, lud_code: str) -> str:
        """Extrait les règles principales du code .lud"""
        if not lud_code:
            return "Règles non disponibles dans la base."
        
        rules = []
        
        # Mécaniques de jeu
        if "Checkmate" in lud_code:
            rules.append("• 🎯 Objectif : Échec et mat (Checkmate)")
        if "Stalemate" in lud_code:
            rules.append("• 🤝 Stalemate possible")
        if "Promotion" in lud_code:
            rules.append("• ⬆️ Promotion des pièces possible")
        if "Castling" in lud_code:
            rules.append("• 🏰 Roque (Castling) autorisé")
        if "capture" in lud_code.lower() or "remove" in lud_code.lower():
            rules.append("• ⚔️ Capture de pièces")
        if "Hop" in lud_code:
            rules.append("• 🦘 Saut par-dessus les pièces")
        if "Step" in lud_code:
            rules.append("• 🚶 Déplacement case par case")
        if "Slide" in lud_code:
            rules.append("• 🏃 Déplacement en ligne droite")
        
        # Pièces
        pieces = re.findall(r'\(piece\s+"([^"]+)"', lud_code)
        if pieces:
            unique_pieces = list(dict.fromkeys(pieces))  # Garder l'ordre, supprimer les doublons
            rules.append(f"• ♟️ Pièces : {', '.join(unique_pieces[:8])}")
        
        # Description
        descriptions = re.findall(r'\(description\s+"([^"]+)"', lud_code)
        if descriptions and not rules:
            rules.insert(0, f"📖 {descriptions[0][:300]}")
        
        return "\n".join(rules) if rules else "Règles détaillées disponibles dans le code source .lud"
    
    def close(self):
        self.driver.close()