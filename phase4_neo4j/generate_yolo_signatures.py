import os
import re
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

LUD_DIR = r"C:\Users\pc\Documents\data_ludii_2\lud\games"  # adapte le chemin

def parse_lud(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraction du plateau
    # Format typique : (board (square 8)) ou (board (hex 5)) ou (board (rectangle 8 10)) ...
    board_match = re.search(r'\(board\s+\((\w+)\s+(\d+)(?:\s+(\d+))?\)', content)
    if not board_match:
        return None
    
    shape = board_match.group(1)
    if shape == 'square':
        cols = int(board_match.group(2))
        rows = cols
    elif shape == 'rectangle':
        cols = int(board_match.group(2))
        rows = int(board_match.group(3)) if board_match.group(3) else cols
    elif shape == 'hex':
        # Pour simplifier, on prend le nombre comme diamètre, mais il faudra adapter
        cols = int(board_match.group(2))
        rows = cols
    else:
        # Autres formes : on met le premier nombre comme cols, 0 comme rows pour signaler non standard
        cols = int(board_match.group(2))
        rows = int(board_match.group(3)) if board_match.group(3) else 0

    # Extraction des pièces : (piece "King") (piece "Pawn") ...
    piece_types = re.findall(r'\(piece\s+"([^"]+)"\)', content)
    required_pieces = list(set(piece_types))  # dédoublonnées

    # Nombre total de pièces : plus difficile, on peut le fixer à null pour l'instant
    total_pieces = None  # à déterminer éventuellement plus tard

    return {
        'board_cols': cols,
        'board_rows': rows,
        'board_shape': shape,
        'required_pieces': required_pieces,
        'total_pieces': total_pieces
    }

def create_yolo_signature(tx, game_name, ruleset_id, data):
    # Crée ou met à jour un nœud YOLOSignature lié au Ruleset
    tx.run("""
        MATCH (rs:Ruleset {id: $rid})
        MERGE (sig:YOLOSignature {game_name: $name})
        SET sig.board_cols = $cols,
            sig.board_rows = $rows,
            sig.board_shape = $shape,
            sig.required_pieces = $pieces,
            sig.total_pieces = $total
        MERGE (rs)-[:HAS_YOLO_SIGNATURE]->(sig)
    """, name=game_name, rid=ruleset_id, cols=data['board_cols'],
       rows=data['board_rows'], shape=data['board_shape'],
       pieces=data['required_pieces'], total=data['total_pieces'])

# Parcourir les .lud et associer au Ruleset via le nom du jeu
# On peut requêter Neo4j pour trouver le Ruleset par nom de jeu, mais attention il peut y avoir plusieurs règles.
# On prendra le Ruleset principal (MainRuleset) du jeu correspondant au nom du fichier.

with driver.session() as session:
    for root, dirs, files in os.walk(LUD_DIR):
        for file in files:
            if not file.endswith('.lud'):
                continue
            filepath = os.path.join(root, file)
            game_name = os.path.splitext(file)[0]  # Ex: "Chess" à partir de "Chess.lud"
            print(f"Traitement de {game_name}...")
            
            # Chercher le Game correspondant dans Neo4j
            result = session.run("MATCH (g:Game {name: $name}) RETURN g.id AS gameId", name=game_name)
            game_record = result.single()
            if not game_record:
                print(f"  ⚠️ Jeu '{game_name}' non trouvé dans Neo4j.")
                continue
            
            # Trouver le Ruleset principal (MainRuleset) : on prend celui lié au Game avec le plus petit id ou le premier
            rs_result = session.run("""
                MATCH (g:Game {id: $gid})-[:HAS_RULESET]->(rs:Ruleset)
                RETURN rs.id AS rid
                ORDER BY rs.id
                LIMIT 1
            """, gid=game_record["gameId"])
            rs_record = rs_result.single()
            if not rs_record:
                print(f"  ⚠️ Aucun Ruleset pour {game_name}.")
                continue
            
            data = parse_lud(filepath)
            if data is None:
                print(f"  ⚠️ Pas de plateau détecté dans {game_name}.")
                continue
            
            session.execute_write(create_yolo_signature, game_name, rs_record["rid"], data)
            print(f"  ✅ Signature YOLO créée pour {game_name}")

driver.close()