from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "salma1234"))
)

games_signatures = {
    "Chess": {
        "board_cols": 8,
        "board_rows": 8,
        "total_pieces": 32,
        "required_pieces": ["rook", "knight", "bishop", "queen", "king", "pawn"],
        "has_bishop": True,
        "has_pawn": True,
        "has_knight": True,
        "has_rook": True,
        "has_queen": True,
        "has_king": True,
        "confidence_threshold": 0.85
    },
    "Half Chess": {
        "board_cols": 8,
        "board_rows": 8,
        "total_pieces": 16,
        "required_pieces": ["rook", "knight", "bishop", "queen", "king", "pawn"],
        "has_bishop": True,
        "has_pawn": True,
        "has_knight": True,
        "has_rook": True,
        "has_queen": True,
        "has_king": True,
        "confidence_threshold": 0.80
    },
    "Los Alamos Chess": {
        "board_cols": 6,
        "board_rows": 6,
        "total_pieces": 12,
        "required_pieces": ["rook", "knight", "queen", "king", "pawn"],
        "has_bishop": False,
        "has_pawn": True,
        "has_knight": True,
        "has_rook": True,
        "has_queen": True,
        "has_king": True,
        "confidence_threshold": 0.75
    }
}

with driver.session() as session:
    for game_name, sig_data in games_signatures.items():
        # 1. Mettre à jour LudiiGame
        session.run("""
            MATCH (g:LudiiGame {name: $name})
            SET g.board_cols = $cols,
                g.board_rows = $rows,
                g.total_pieces = $total,
                g.has_bishop = $bishop,
                g.has_pawn = $pawn,
                g.has_knight = $knight,
                g.has_rook = $rook,
                g.has_queen = $queen,
                g.has_king = $king
        """,
        name=game_name,
        cols=sig_data["board_cols"],
        rows=sig_data["board_rows"],
        total=sig_data["total_pieces"],
        bishop=sig_data["has_bishop"],
        pawn=sig_data["has_pawn"],
        knight=sig_data["has_knight"],
        rook=sig_data["has_rook"],
        queen=sig_data["has_queen"],
        king=sig_data["has_king"]
        )
        
        # 2. Créer YOLOSignature
        session.run("""
            MERGE (sig:YOLOSignature {game_name: $name})
            SET sig.board_cols = $cols,
                sig.board_rows = $rows,
                sig.total_pieces = $total,
                sig.required_pieces = $pieces,
                sig.confidence_threshold = $threshold
        """,
        name=game_name,
        cols=sig_data["board_cols"],
        rows=sig_data["board_rows"],
        total=sig_data["total_pieces"],
        pieces=sig_data["required_pieces"],
        threshold=sig_data["confidence_threshold"]
        )
        
        # 3. Lier LudiiGame à YOLOSignature
        session.run("""
            MATCH (g:LudiiGame {name: $name})
            MATCH (sig:YOLOSignature {game_name: $name})
            MERGE (g)-[:HAS_YOLO_SIGNATURE]->(sig)
        """, name=game_name)
        
        print(f"✅ {game_name}: {sig_data['board_cols']}x{sig_data['board_rows']}, {sig_data['total_pieces']} pieces")

driver.close()
print("\n✅ YOLOSignature structure created!")