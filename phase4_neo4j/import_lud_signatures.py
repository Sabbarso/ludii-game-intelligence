import os
import re
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Chemin vers le dossier contenant les fichiers .lud
LUD_DIR = r"C:\Users\pc\Documents\data_ludii_2\lud\games"

def parse_lud_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Supprimer les commentaires (lignes commençant par ;)
    content = re.sub(r';.*', '', content)
    
    # Nom du jeu (game "Nom")
    game_match = re.search(r'\(game\s+"([^"]+)"', content)
    if not game_match:
        return None
    game_name = game_match.group(1).strip()
    
    # ID dans les métadonnées (info ... (id "1234"))
    id_match = re.search(r'\(info[^)]*\(id\s+"(\d+)"\)', content)
    ruleset_id = int(id_match.group(1)) if id_match else None
    
    # Dimensions du plateau
    board_match = re.search(r'\(board\s+\((\w+)(?:\s+(\d+)(?:\s+(\d+))?)?\)', content)
    cols = rows = None
    shape = None
    if board_match:
        shape = board_match.group(1)
        if shape == 'square':
            cols = rows = int(board_match.group(2))
        elif shape == 'rectangle':
            cols = int(board_match.group(2))
            rows = int(board_match.group(3)) if board_match.group(3) else cols
        elif shape == 'hex':
            cols = int(board_match.group(2)) if board_match.group(2) else None
            rows = cols  # approximation
        else:
            cols = int(board_match.group(2)) if board_match.group(2) else None
            rows = int(board_match.group(3)) if board_match.group(3) else cols
    if cols is None:
        return None  # pas de plateau, on ignore
    
    # Pièces
    piece_patterns = re.findall(r'\(piece\s+"([^"]+)"', content)
    # Gérer aussi les définitions par alias : ("ChessRook" "Rook")
    alias_pieces = re.findall(r'\("([^"]+)"\s+"([^"]+)"\)', content)
    for alias, name in alias_pieces:
        if 'Rook' in name or 'King' in name or 'Knight' in name or 'Pawn' in name or 'Queen' in name or 'Bishop' in name:
            piece_patterns.append(name.lower())
    # Nettoyer (minuscules, dédoublonner)
    piece_types = list(set([p.lower() for p in piece_patterns if p.strip()]))
    
    return {
        'game_name': game_name,
        'ruleset_id': ruleset_id,
        'board_cols': cols,
        'board_rows': rows,
        'board_shape': shape,
        'required_pieces': piece_types,
        'total_pieces': None  # à compléter manuellement si besoin
    }

def create_signature(tx, data):
    # Essayer d'abord avec l'ID, si présent
    if data['ruleset_id'] is not None:
        result = tx.run("MATCH (rs:Ruleset {id: $rid}) RETURN rs", rid=data['ruleset_id'])
        rs_record = result.single()
        if rs_record:
            rs_id = rs_record['rs']['id']  # récupération sécurisée
            tx.run("""
                MERGE (sig:YOLOSignature {game_name: $name})
                SET sig.board_cols = $cols, sig.board_rows = $rows, sig.board_shape = $shape,
                    sig.required_pieces = $pieces, sig.total_pieces = $total, sig.source = 'lud_file'
                WITH sig
                MATCH (rs:Ruleset {id: $rid})
                MERGE (rs)-[:HAS_YOLO_SIGNATURE]->(sig)
            """, name=data['game_name'], cols=data['board_cols'], rows=data['board_rows'],
                shape=data['board_shape'], pieces=data['required_pieces'], total=data['total_pieces'],
                rid=rs_id)
            return True
        # Si l'ID n'existe pas en base, on continue avec le nom (ne pas retourner False)
    
    # Liaison par nom (insensible à la casse, avec et sans parenthèses)
    # On prépare deux versions du nom : originale et nettoyée
    candidates = [data['game_name']]
    # Nettoyer en enlevant le contenu entre parenthèses (ex: "Shatranj (Egypt)" -> "Shatranj")
    clean_name = re.sub(r'\s*\(.*?\)\s*', '', data['game_name']).strip()
    if clean_name != data['game_name']:
        candidates.append(clean_name)
    
    for name_candidate in candidates:
        # Chercher un Game dont le nom correspond (insensible à la casse)
        result = tx.run("""
            MATCH (g:Game)
            WHERE toLower(g.name) = toLower($name)
            MATCH (g)-[:HAS_RULESET]->(rs:Ruleset)
            RETURN rs
            LIMIT 1
        """, name=name_candidate)
        rs_record = result.single()
        if rs_record:
            rs_id = rs_record['rs']['id']
            tx.run("""
                MERGE (sig:YOLOSignature {game_name: $sig_name})
                SET sig.board_cols = $cols, sig.board_rows = $rows, sig.board_shape = $shape,
                    sig.required_pieces = $pieces, sig.total_pieces = $total, sig.source = 'lud_file'
                WITH sig
                MATCH (rs:Ruleset {id: $rid})
                MERGE (rs)-[:HAS_YOLO_SIGNATURE]->(sig)
            """, sig_name=data['game_name'], cols=data['board_cols'], rows=data['board_rows'],
                shape=data['board_shape'], pieces=data['required_pieces'], total=data['total_pieces'],
                rid=rs_id)
            return True
    
    # Si aucune liaison n'a réussi, créer la signature orpheline
    tx.run("""
        MERGE (sig:YOLOSignature {game_name: $name})
        SET sig.board_cols = $cols, sig.board_rows = $rows, sig.board_shape = $shape,
            sig.required_pieces = $pieces, sig.total_pieces = $total, sig.source = 'lud_file'
    """, name=data['game_name'], cols=data['board_cols'], rows=data['board_rows'],
        shape=data['board_shape'], pieces=data['required_pieces'], total=data['total_pieces'])
    return False

# --- Main ---
# Supprimer les anciennes signatures issues du parsing précédent (pour repartir de zéro)
with driver.session() as session:
    session.run("MATCH (sig:YOLOSignature {source: 'lud_file'}) DETACH DELETE sig")

# Parcourir les .lud
stats = {'total': 0, 'linked': 0, 'unlinked': 0}
with driver.session() as session:
    for root, dirs, files in os.walk(LUD_DIR):
        for file in files:
            if file.endswith('.lud'):
                filepath = os.path.join(root, file)
                data = parse_lud_file(filepath)
                if data is None:
                    continue
                stats['total'] += 1
                try:
                    linked = session.execute_write(create_signature, data)
                    if linked:
                        stats['linked'] += 1
                        print(f"✅ Lié : {data['game_name']} (ID {data['ruleset_id']})")
                    else:
                        stats['unlinked'] += 1
                        print(f"⚠️ Non lié : {data['game_name']} (ID {data.get('ruleset_id')})")
                except Exception as e:
                    print(f"❌ Erreur sur {data['game_name']} : {e}")

print(f"\nTotal signatures créées : {stats['total']}")
print(f"Liées à un Ruleset : {stats['linked']}")
print(f"Non liées : {stats['unlinked']}")

driver.close()