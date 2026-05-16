from neo4j import GraphDatabase
import os

class LudiiPopulator:
    def __init__(self, uri, user, password):
        """
        Pour Neo4j Desktop, utiliser:
        - uri: "neo4j://127.0.0.1:7687"
        - user: "neo4j"
        - password: salma1234
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    # def clear_db(self):
        # with self.driver.session() as session:
            # session.run("MATCH (n) DETACH DELETE n")
        # print("✅ Base vidée")
    
    def create_constraints(self):
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT ludii_game_id IF NOT EXISTS FOR (g:LudiiGame) REQUIRE g.id IS UNIQUE")
            except:
                pass
            try:
                session.run("CREATE CONSTRAINT ludii_rule_id IF NOT EXISTS FOR (r:Rule) REQUIRE r.id IS UNIQUE")
            except:
                pass
            try:
                session.run("CREATE INDEX ludii_game_name IF NOT EXISTS FOR (g:LudiiGame) ON (g.name)")
            except:
                pass
        print("✅ Contraintes créées")
    
    def populate_games(self):
        """Créer tous les jeux Ludii"""
        games = [
            {"id": "game_chess", "name": "Chess", "origin": "India/Persia", "year": 600, "players": 2, "complexity": 9},
            {"id": "game_checkers", "name": "Checkers", "origin": "Spain", "year": 1500, "players": 2, "complexity": 6},
            {"id": "game_ludo", "name": "Ludo", "origin": "India", "year": 1896, "players": 4, "complexity": 3},
            {"id": "game_reversi", "name": "Reversi", "origin": "Japan", "year": 1883, "players": 2, "complexity": 8},
            {"id": "game_go", "name": "Go", "origin": "China", "year": -2500, "players": 2, "complexity": 10},
            {"id": "game_hnefatafl", "name": "Hnefatafl", "origin": "Scandinavia", "year": 500, "players": 2, "complexity": 7},
            {"id": "game_mancala", "name": "Mancala", "origin": "Africa", "year": 1000, "players": 2, "complexity": 5},
            {"id": "game_nmmm", "name": "Nine Mens Morris", "origin": "Europe", "year": 1200, "players": 2, "complexity": 6},
            {"id": "game_tablut", "name": "Tablut", "origin": "Scandinavia", "year": 800, "players": 2, "complexity": 7},
            {"id": "game_alquerque", "name": "Alquerque", "origin": "Spain", "year": 1500, "players": 2, "complexity": 5},
            {"id": "game_pachisi", "name": "Pachisi", "origin": "India", "year": 500, "players": 4, "complexity": 4},
            {"id": "game_parchis", "name": "Parchís", "origin": "Spain", "year": 1860, "players": 4, "complexity": 3},
            {"id": "game_shogi", "name": "Shogi", "origin": "Japan", "year": 900, "players": 2, "complexity": 9},
            {"id": "game_xiangqi", "name": "Xiangqi", "origin": "China", "year": 800, "players": 2, "complexity": 9},
            {"id": "game_janggi", "name": "Janggi", "origin": "Korea", "year": 1400, "players": 2, "complexity": 8},
        ]
        
        with self.driver.session() as session:
            for i, game in enumerate(games, 1):
                session.run("""
                    CREATE (g:LudiiGame {
                        id: $id,
                        name: $name,
                        origin: $origin,
                        year: $year,
                        players_max: $players,
                        complexity: $complexity
                    })
                """, game)
                print(f"  [{i}/{len(games)}] {game['name']}")
        
        print(f"✅ {len(games)} jeux créés")
    
    def populate_rules(self):
        """Ajouter des règles"""
        rules_by_game = {
            "game_chess": [
                {"category": "movement", "text": "Pawns move forward one square, or two on first move"},
                {"category": "movement", "text": "Rooks move horizontally or vertically any number of squares"},
                {"category": "movement", "text": "Bishops move diagonally any number of squares"},
                {"category": "movement", "text": "Knights move in L-shape: 2+1 squares"},
                {"category": "movement", "text": "Queens combine rook and bishop powers"},
                {"category": "movement", "text": "Kings move one square in any direction"},
                {"category": "win_condition", "text": "Checkmate the opponent king to win"},
                {"category": "special", "text": "Castling allowed under certain conditions"},
                {"category": "special", "text": "En passant capture for pawns"},
            ],
            "game_ludo": [
                {"category": "movement", "text": "Roll dice to move pawns"},
                {"category": "entry", "text": "Need 6 to enter pawn on board"},
                {"category": "capture", "text": "Landing on opponent sends them back to home"},
                {"category": "movement", "text": "Move from home to finish in 56 spaces"},
                {"category": "win_condition", "text": "First to bring all pawns home wins"},
            ],
            "game_reversi": [
                {"category": "placement", "text": "Place disc to trap opponent discs between yours"},
                {"category": "capture", "text": "Trapped discs flip to your color"},
                {"category": "pass", "text": "Pass if no valid move available"},
                {"category": "board", "text": "Board is 8x8 with 64 squares"},
                {"category": "win_condition", "text": "Most discs when board fills wins"},
            ],
            "game_go": [
                {"category": "placement", "text": "Place stone on empty intersection"},
                {"category": "capture", "text": "Surround opponent stones to capture them"},
                {"category": "territory", "text": "Surround empty space for territory points"},
                {"category": "ko_rule", "text": "Cannot immediately recapture single stone"},
                {"category": "win_condition", "text": "Most territory plus prisoners wins"},
            ],
            "game_checkers": [
                {"category": "movement", "text": "Pieces move diagonally forward one square"},
                {"category": "capture", "text": "Capture by jumping over opponent piece"},
                {"category": "multiple_capture", "text": "Multiple captures in one turn allowed"},
                {"category": "promotion", "text": "Reach last row to become king"},
                {"category": "king_movement", "text": "Kings move both forward and backward"},
                {"category": "win_condition", "text": "Capture all opponent pieces to win"},
            ],
        }
        
        with self.driver.session() as session:
            for game_id, rules in rules_by_game.items():
                for i, rule in enumerate(rules):
                    rule_id = f"{game_id}_rule_{i}"
                    session.run("""
                        CREATE (r:Rule {
                            id: $rule_id,
                            category: $category,
                            text: $text,
                            source: 'ludii_official'
                        })
                    """, {
                        "rule_id": rule_id,
                        "category": rule["category"],
                        "text": rule["text"]
                    })
                    
                    session.run("""
                        MATCH (g:LudiiGame {id: $game_id})
                        MATCH (r:Rule {id: $rule_id})
                        MERGE (g)-[:HAS_RULE]->(r)
                    """, {"game_id": game_id, "rule_id": rule_id})
        
        print("✅ Règles créées")
    
    def populate_pieces(self):
        """Ajouter des pièces"""
        pieces_by_game = {
            "game_chess": [
                {"id": "p_chess_wpawn", "name": "Pawn", "color": "white", "count": 8},
                {"id": "p_chess_bpawn", "name": "Pawn", "color": "black", "count": 8},
                {"id": "p_chess_wrook", "name": "Rook", "color": "white", "count": 2},
                {"id": "p_chess_brook", "name": "Rook", "color": "black", "count": 2},
                {"id": "p_chess_wknight", "name": "Knight", "color": "white", "count": 2},
                {"id": "p_chess_bknight", "name": "Knight", "color": "black", "count": 2},
                {"id": "p_chess_wbishop", "name": "Bishop", "color": "white", "count": 2},
                {"id": "p_chess_bbishop", "name": "Bishop", "color": "black", "count": 2},
                {"id": "p_chess_wqueen", "name": "Queen", "color": "white", "count": 1},
                {"id": "p_chess_bqueen", "name": "Queen", "color": "black", "count": 1},
                {"id": "p_chess_wking", "name": "King", "color": "white", "count": 1},
                {"id": "p_chess_bking", "name": "King", "color": "black", "count": 1},
            ],
            "game_ludo": [
                {"id": "p_ludo_red", "name": "Pawn", "color": "red", "count": 4},
                {"id": "p_ludo_blue", "name": "Pawn", "color": "blue", "count": 4},
                {"id": "p_ludo_green", "name": "Pawn", "color": "green", "count": 4},
                {"id": "p_ludo_yellow", "name": "Pawn", "color": "yellow", "count": 4},
            ],
            "game_checkers": [
                {"id": "p_checkers_red", "name": "Piece", "color": "red", "count": 12},
                {"id": "p_checkers_black", "name": "Piece", "color": "black", "count": 12},
            ],
            "game_reversi": [
                {"id": "p_reversi_black", "name": "Disc", "color": "black", "count": 32},
                {"id": "p_reversi_white", "name": "Disc", "color": "white", "count": 32},
            ],
            "game_go": [
                {"id": "p_go_black", "name": "Stone", "color": "black", "count": 181},
                {"id": "p_go_white", "name": "Stone", "color": "white", "count": 181},
            ],
        }
        
        with self.driver.session() as session:
            for game_id, pieces in pieces_by_game.items():
                for piece in pieces:
                    session.run("""
                        CREATE (p:Piece {
                            id: $id,
                            name: $name,
                            color: $color,
                            count_per_player: $count
                        })
                    """, piece)
                    
                    session.run("""
                        MATCH (g:LudiiGame {id: $game_id})
                        MATCH (p:Piece {id: $piece_id})
                        MERGE (g)-[:HAS_PIECE]->(p)
                    """, {"game_id": game_id, "piece_id": piece["id"]})
        
        print("✅ Pièces créées")
    
    def populate_boards(self):
        """Ajouter infos plateaux"""
        boards = {
            "game_chess": {"type": "square", "size": 8, "cells": 64},
            "game_checkers": {"type": "square", "size": 8, "cells": 32},
            "game_ludo": {"type": "spiral", "size": 56, "cells": 56},
            "game_reversi": {"type": "square", "size": 8, "cells": 64},
            "game_go": {"type": "square", "size": 19, "cells": 361},
            "game_hnefatafl": {"type": "square", "size": 11, "cells": 121},
            "game_mancala": {"type": "linear", "size": 2, "cells": 12},
            "game_nmmm": {"type": "custom", "size": 9, "cells": 9},
        }
        
        with self.driver.session() as session:
            for game_id, board_info in boards.items():
                board_id = f"{game_id}_board"
                session.run("""
                    CREATE (b:Board {
                        id: $board_id,
                        type: $type,
                        size: $size,
                        cells: $cells
                    })
                """, {
                    "board_id": board_id,
                    "type": board_info["type"],
                    "size": board_info["size"],
                    "cells": board_info["cells"]
                })
                
                session.run("""
                    MATCH (g:LudiiGame {id: $game_id})
                    MATCH (b:Board {id: $board_id})
                    MERGE (g)-[:HAS_BOARD]->(b)
                """, {"game_id": game_id, "board_id": board_id})
        
        print("✅ Plateaux créés")
    
    def get_stats(self):
        """Afficher stats finales"""
        with self.driver.session() as session:
            nodes = session.run("MATCH (n) RETURN count(n) AS count").single()
            rels = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()
            
            print("\n" + "="*60)
            print("STATS FINALES")
            print("="*60)
            print(f"Nodes: {nodes['count']}")
            print(f"Relations: {rels['count']}")
            
            # Par type
            types = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] AS label, count(*) AS count 
                ORDER BY count DESC
            """)
            
            for record in types:
                print(f"  {record['label']}: {record['count']}")
    
    def run(self):
        try:
            print("\n" + "="*60)
            print("NEO4J LUDII POPULATOR (DESKTOP)")
            print("="*60 + "\n")
            
            self.clear_db()
            self.create_constraints()
            self.populate_games()
            self.populate_rules()
            self.populate_pieces()
            self.populate_boards()
            self.get_stats()
            
            print("\n✅ PEUPLAGE COMPLET!")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close()

if __name__ == "__main__":
    # 📝 ADAPTER CES VALEURS:
    NEO4J_URI = "neo4j://127.0.0.1:7687"  # ← Correct URI with neo4j:// protocol
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "salma1234"  # ← Votre mot de passe
    
    populator = LudiiPopulator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    populator.run()