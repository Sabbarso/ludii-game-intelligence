"""
Neo4j Pipeline - Utilitaires pour accéder aux données Neo4j depuis l'API
"""

from neo4j import GraphDatabase
import os
from typing import List, Dict, Optional

class Neo4jPipeline:
    """Pipeline pour interagir avec Neo4j"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "salma1234")
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j connected")
        except Exception as e:
            print(f"⚠️  Neo4j connection failed: {e}")
            self.driver = None
    
    def get_game_info(self, game_name: str) -> Dict:
        """Get complete game information"""
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (g:LudiiGame {name: $name})
                    RETURN {
                        name: g.name,
                        year: g.year,
                        complexity: g.complexity,
                        players: g.players_max,
                        origin: g.origin,
                        source: g.source
                    } as game
                """, name=game_name).single()
                
                return result['game'] if result else {}
        except Exception as e:
            print(f"Error getting game info: {e}")
            return {}
    
    def search_games(self, query: str) -> List[Dict]:
        """Search games by name (partial match)"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                results = session.run("""
                    MATCH (g:LudiiGame)
                    WHERE g.name CONTAINS $query
                    RETURN {
                        name: g.name,
                        complexity: g.complexity,
                        year: g.year
                    } as game
                    LIMIT 20
                """, query=query).data()
                
                return [r['game'] for r in results]
        except Exception as e:
            print(f"Error searching games: {e}")
            return []
    
    def get_all_games(self) -> List[str]:
        """Get all game names"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                results = session.run("""
                    MATCH (g:LudiiGame)
                    RETURN g.name as name
                    ORDER BY g.name
                """).data()
                
                return [r['name'] for r in results]
        except Exception as e:
            print(f"Error getting all games: {e}")
            return []
    
    def get_game_rules(self, game_name: str) -> List[Dict]:
        """Get rules for a game"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                results = session.run("""
                    MATCH (g:LudiiGame {name: $name})-[:HAS_RULE]->(r:Rule)
                    RETURN {
                        text: r.text,
                        category: r.category
                    } as rule
                    LIMIT 20
                """, name=game_name).data()
                
                return [r['rule'] for r in results]
        except Exception as e:
            print(f"Error getting rules: {e}")
            return []
    
    def get_game_pieces(self, game_name: str) -> List[Dict]:
        """Get pieces for a game"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                results = session.run("""
                    MATCH (g:LudiiGame {name: $name})-[:HAS_PIECE]->(p:Piece)
                    RETURN {
                        name: p.name,
                        color: p.color,
                        count: p.count_per_player
                    } as piece
                    LIMIT 20
                """, name=game_name).data()
                
                return [r['piece'] for r in results]
        except Exception as e:
            print(f"Error getting pieces: {e}")
            return []
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()

# Global instance
_pipeline = None

def get_pipeline() -> Neo4jPipeline:
    """Get or create pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = Neo4jPipeline()
    return _pipeline