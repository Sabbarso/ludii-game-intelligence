from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "salma1234"))
)

games_data = {
    "Chess": {
        "periods": ["Medieval", "Modern"],
        "regions": ["Northern America", "Eastern Europe", "Northern Europe", "Southern Europe", "Western Europe"],
        "categories": ["Board", "War", "Replacement", "Checkmate", "Chess"],
        "origin": "Europe",
        "yolo_class": "chess_standard",
        "pieces_expected": 32,
        "board_size": [8, 8]
    },
    "Half Chess": {"periods": ["Modern"], "regions": ["Europe"], "categories": ["Board", "War", "Chess"], "origin": "Europe", "yolo_class": "chess_half", "pieces_expected": 16, "board_size": [8, 8]},
    "Los Alamos Chess": {"periods": ["Modern"], "regions": ["Northern America"], "categories": ["Board", "War", "Chess"], "origin": "Northern America", "yolo_class": "chess_losal", "pieces_expected": 12, "board_size": [6, 6]},
    "Symmetric Chess": {"periods": ["Modern"], "regions": ["Europe"], "categories": ["Board", "War", "Chess"], "origin": "Europe", "yolo_class": "chess_symmetric", "pieces_expected": 32, "board_size": [8, 8]},
    "Double Chess": {"periods": ["Modern"], "regions": ["Europe"], "categories": ["Board", "War", "Chess"], "origin": "Europe", "yolo_class": "chess_double", "pieces_expected": 64, "board_size": [16, 8]}
}

with driver.session() as session:
    for game_name, data in games_data.items():
        # Créer Period, Region, Category, Origin
        for period in data["periods"]:
            session.run("MERGE (p:Period {name: $n})", n=period)
            session.run("MATCH (g:LudiiGame {name: $g}) MATCH (p:Period {name: $p}) MERGE (g)-[:FROM_PERIOD]->(p)", g=game_name, p=period)
        
        for region in data["regions"]:
            session.run("MERGE (r:Region {name: $n})", n=region)
            session.run("MATCH (g:LudiiGame {name: $g}) MATCH (r:Region {name: $r}) MERGE (g)-[:FROM_REGION]->(r)", g=game_name, r=region)
        
        for cat in data["categories"]:
            session.run("MERGE (c:Category {name: $n})", n=cat)
            session.run("MATCH (g:LudiiGame {name: $g}) MATCH (c:Category {name: $c}) MERGE (g)-[:IN_CATEGORY]->(c)", g=game_name, c=cat)
        
        session.run("MERGE (o:Origin {name: $n})", n=data["origin"])
        session.run("MATCH (g:LudiiGame {name: $g}) MATCH (o:Origin {name: $o}) MERGE (g)-[:ORIGINATES_FROM]->(o)", g=game_name, o=data["origin"])
        
        # Créer YOLOMapping
        session.run("MERGE (m:YOLOMapping {detected_class: $y}) SET m.game_name=$g, m.pieces_expected=$p, m.board_dimensions=$b", 
                   y=data["yolo_class"], g=game_name, p=data["pieces_expected"], b=data["board_size"])
        
        print(f"✅ {game_name}")

driver.close()