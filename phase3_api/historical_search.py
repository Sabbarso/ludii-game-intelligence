"""
API pour recherche historique et relationnelle avec Neo4j
"""

from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from typing import Optional, List, Dict
import os

router = APIRouter(prefix="/api/v1", tags=["historical"])

# Connexion Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# ========== ENDPOINT 1: Recherche Historique ==========
@router.post("/historical_search")
async def historical_search(game_name: str):
    """
    Cherche l'historique complet d'un jeu:
    - Famille
    - Origine
    - Variantes
    - Règles
    - Pièces
    """
    
    try:
        with driver.session() as session:
            # 1. Famille du jeu
            family_result = session.run("""
                MATCH (g:LudiiGame {name: $game})-[:BELONGS_TO]->(f:Family)
                RETURN f.name as family
            """, game=game_name).single()
            
            family = family_result['family'] if family_result else None
            
            # 2. Origine du jeu
            origin_result = session.run("""
                MATCH (g:LudiiGame {name: $game})-[:ORIGINATED_IN]->(c:Civilization)
                RETURN c.name as civilization
            """, game=game_name).single()
            
            origin = origin_result['civilization'] if origin_result else None
            
            # 3. Variantes du jeu
            variants = session.run("""
                MATCH (g:LudiiGame {name: $game})<-[:VARIANT_OF]-(v:LudiiGame)
                RETURN v.name as variant
            """, game=game_name).data()
            
            variant_names = [v['variant'] for v in variants]
            
            # 4. Jeux dérivés
            derived = session.run("""
                MATCH (g:LudiiGame {name: $game})<-[:DERIVED_FROM]-(d:LudiiGame)
                RETURN d.name as derived
            """, game=game_name).data()
            
            derived_names = [d['derived'] for d in derived]
            
            # 5. Règles du jeu
            rules = session.run("""
                MATCH (g:LudiiGame {name: $game})-[:HAS_RULE]->(r:Rule)
                RETURN r.text, r.category
                LIMIT 10
            """, game=game_name).data()
            
            rules_list = [{"text": r['r.text'], "category": r['r.category']} for r in rules]
            
            # 6. Pièces du jeu
            pieces = session.run("""
                MATCH (g:LudiiGame {name: $game})-[:HAS_PIECE]->(p:Piece)
                RETURN p.name, p.color, p.count_per_player
            """, game=game_name).data()
            
            pieces_list = [
                {
                    "name": p['p.name'],
                    "color": p['p.color'],
                    "count": p['p.count_per_player']
                }
                for p in pieces
            ]
            
            # 7. Infos du jeu
            game_info = session.run("""
                MATCH (g:LudiiGame {name: $game})
                RETURN g.year as year, g.players_max as players, g.complexity as complexity, g.origin as origin
            """, game=game_name).single()
            
            return {
                "game": game_name,
                "family": family,
                "origin": origin,
                "year": game_info['year'] if game_info else None,
                "players": game_info['players'] if game_info else None,
                "complexity": game_info['complexity'] if game_info else None,
                "variants": variant_names,
                "derived_from": derived_names,
                "rules": rules_list,
                "pieces": pieces_list,
                "total_rules": len(rules_list),
                "total_pieces": len(pieces_list)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche: {str(e)}")

# ========== ENDPOINT 2: Jeux Similaires ==========
@router.post("/similar_games")
async def similar_games(game_name: str):
    """
    Trouve des jeux similaires basé sur:
    - Même famille
    - Même origine
    - Même nombre de joueurs
    """
    
    try:
        with driver.session() as session:
            # Même famille
            same_family = session.run("""
                MATCH (g1:LudiiGame {name: $game})-[:BELONGS_TO]->(f:Family)<-[:BELONGS_TO]-(g2:LudiiGame)
                WHERE g1 <> g2
                RETURN g2.name, g2.complexity, g2.year
                ORDER BY g2.complexity
                LIMIT 10
            """, game=game_name).data()
            
            # Même origine
            same_origin = session.run("""
                MATCH (g1:LudiiGame {name: $game})-[:ORIGINATED_IN]->(c:Civilization)<-[:ORIGINATED_IN]-(g2:LudiiGame)
                WHERE g1 <> g2
                RETURN g2.name, g2.complexity, g2.year
                ORDER BY g2.complexity
                LIMIT 10
            """, game=game_name).data()
            
            # Même nombre de joueurs
            same_players = session.run("""
                MATCH (g1:LudiiGame {name: $game})
                MATCH (g2:LudiiGame {players_max: g1.players_max})
                WHERE g1 <> g2
                RETURN g2.name, g2.complexity
                ORDER BY g2.complexity
                LIMIT 10
            """, game=game_name).data()
            
            return {
                "game": game_name,
                "same_family": [
                    {"name": g['g2.name'], "complexity": g['g2.complexity'], "year": g['g2.year']}
                    for g in same_family
                ],
                "same_origin": [
                    {"name": g['g2.name'], "complexity": g['g2.complexity'], "year": g['g2.year']}
                    for g in same_origin
                ],
                "same_players": [
                    {"name": g['g2.name'], "complexity": g['g2.complexity']}
                    for g in same_players
                ]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# ========== ENDPOINT 3: Infos complètes d'une famille ==========
@router.get("/family/{family_name}")
async def get_family_info(family_name: str):
    """
    Récupère toutes les infos d'une famille de jeux
    """
    
    try:
        with driver.session() as session:
            # Jeux dans cette famille
            games = session.run("""
                MATCH (f:Family {name: $family})<-[:BELONGS_TO]-(g:LudiiGame)
                RETURN g.name, g.complexity, g.year, g.origin
                ORDER BY g.name
            """, family=family_name).data()
            
            if not games:
                raise HTTPException(status_code=404, detail=f"Famille '{family_name}' non trouvée")
            
            return {
                "family": family_name,
                "games": [
                    {
                        "name": g['g.name'],
                        "complexity": g['g.complexity'],
                        "year": g['g.year'],
                        "origin": g['g.origin']
                    }
                    for g in games
                ],
                "total_games": len(games)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# ========== ENDPOINT 4: Origines et Civilisations ==========
@router.get("/civilizations")
async def get_civilizations():
    """
    Récupère toutes les civilisations et les jeux associés
    """
    
    try:
        with driver.session() as session:
            civilizations = session.run("""
                MATCH (c:Civilization)<-[:ORIGINATED_IN]-(g:LudiiGame)
                WITH c.name as civilization, collect(g.name) as games, count(g) as count
                RETURN civilization, games, count
                ORDER BY count DESC
            """).data()
            
            return {
                "civilizations": [
                    {
                        "name": c['civilization'],
                        "games": c['games'],
                        "count": c['count']
                    }
                    for c in civilizations
                ]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# ========== ENDPOINT 5: Recherche par critères ==========
@router.post("/search_by_criteria")
async def search_by_criteria(
    family: Optional[str] = None,
    origin: Optional[str] = None,
    players: Optional[int] = None,
    min_complexity: Optional[int] = None,
    max_complexity: Optional[int] = None
):
    """
    Recherche des jeux par critères combinés
    """
    
    try:
        with driver.session() as session:
            # Construire la requête dynamiquement
            where_clauses = []
            params = {}
            
            if family:
                where_clauses.append("(g)-[:BELONGS_TO]->(:Family {name: $family})")
                params['family'] = family
            
            if origin:
                where_clauses.append("(g)-[:ORIGINATED_IN]->(:Civilization {name: $origin})")
                params['origin'] = origin
            
            if players:
                where_clauses.append("g.players_max = $players")
                params['players'] = players
            
            if min_complexity:
                where_clauses.append("g.complexity >= $min_complexity")
                params['min_complexity'] = min_complexity
            
            if max_complexity:
                where_clauses.append("g.complexity <= $max_complexity")
                params['max_complexity'] = max_complexity
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                MATCH (g:LudiiGame)
                WHERE {where_clause}
                RETURN g.name, g.complexity, g.year, g.players_max
                ORDER BY g.name
            """
            
            results = session.run(query, params).data()
            
            return {
                "criteria": {
                    "family": family,
                    "origin": origin,
                    "players": players,
                    "min_complexity": min_complexity,
                    "max_complexity": max_complexity
                },
                "results": [
                    {
                        "name": r['g.name'],
                        "complexity": r['g.complexity'],
                        "year": r['g.year'],
                        "players": r['g.players_max']
                    }
                    for r in results
                ],
                "count": len(results)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")