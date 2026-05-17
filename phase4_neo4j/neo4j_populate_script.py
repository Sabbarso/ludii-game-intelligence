"""
Script Python pour peupler Neo4j automatiquement - SANS ERREUR
Exécute les requêtes UNE PAR UNE pour éviter le problème "Variable already declared"
"""

from neo4j import GraphDatabase
import os

print("=" * 100)
print("🚀 POPULATION NEO4J - CHESS GAMES")
print("=" * 100)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

def execute_query(session, cypher, description=""):
    """Exécuter une requête unique"""
    try:
        result = session.run(cypher)
        summary = result.consume()
        if description:
            print(f"  ✅ {description}")
        return True
    except Exception as e:
        print(f"  ❌ {description}")
        print(f"     Erreur: {e}")
        return False

try:
    with driver.session() as session:
        
        # ========== ÉTAPE 1: PERIODS ==========
        print("\n[1/14] CRÉER LES PERIODS...")
        execute_query(session, 'MERGE (p:Period {name: "Medieval"})', "Period: Medieval")
        execute_query(session, 'MERGE (p:Period {name: "Modern"})', "Period: Modern")
        
        # ========== ÉTAPE 2: REGIONS ==========
        print("\n[2/14] CRÉER LES REGIONS...")
        execute_query(session, 'MERGE (r:Region {name: "Northern America"})', "Region: Northern America")
        execute_query(session, 'MERGE (r:Region {name: "Eastern Europe"})', "Region: Eastern Europe")
        execute_query(session, 'MERGE (r:Region {name: "Northern Europe"})', "Region: Northern Europe")
        execute_query(session, 'MERGE (r:Region {name: "Southern Europe"})', "Region: Southern Europe")
        execute_query(session, 'MERGE (r:Region {name: "Western Europe"})', "Region: Western Europe")
        execute_query(session, 'MERGE (r:Region {name: "Europe"})', "Region: Europe")
        
        # ========== ÉTAPE 3: CATEGORIES ==========
        print("\n[3/14] CRÉER LES CATEGORIES...")
        execute_query(session, 'MERGE (c:Category {name: "Board"})', "Category: Board")
        execute_query(session, 'MERGE (c:Category {name: "War"})', "Category: War")
        execute_query(session, 'MERGE (c:Category {name: "Replacement"})', "Category: Replacement")
        execute_query(session, 'MERGE (c:Category {name: "Checkmate"})', "Category: Checkmate")
        execute_query(session, 'MERGE (c:Category {name: "Chess"})', "Category: Chess")
        
        # ========== ÉTAPE 4: ORIGINS ==========
        print("\n[4/14] CRÉER LES ORIGINS...")
        execute_query(session, 'MERGE (o:Origin {name: "Europe"})', "Origin: Europe")
        execute_query(session, 'MERGE (o:Origin {name: "Northern America"})', "Origin: Northern America")
        
        # ========== ÉTAPE 5: JEUX ==========
        print("\n[5/14] CRÉER LES JEUX...")
        
        chess_query = '''
        MERGE (g:LudiiGame {name: "Chess"})
        SET g.official_populated = true,
            g.official_description = "Ultimately originates from Indian Chaturanga, arrived in Western Europe during the Middle Ages as Shatranj. Over several centuries, after seeming experimentation with movement, the adoption of the modern movement of the queen and bishop made chess what it is today. Modern Chess appeared sometimes during the fourteenth or fifteenth Century, when the vizier piece was replaced by the queen.",
            g.official_rules = "Played on an 8x8 board with pieces with specialized moves: Pawns (8): can move one space forward; Rooks (2): can move any number of spaces orthogonally; Bishops (2): can move any number of spaces diagonally; Knight (2): moves in any direction, one space orthogonally with one space forward diagonally; Queens (1): can move any number of spaces orthogonally or diagonally; Kings (1): can move one space orthogonally or diagonally. Players capture pieces by moving onto a space occupied by an opponent's piece. Player wins when they checkmate the other player's king."
        '''
        execute_query(session, chess_query, "Game: Chess")
        
        half_chess_query = '''
        MERGE (g:LudiiGame {name: "Half Chess"})
        SET g.official_populated = true,
            g.official_description = "Variant of Chess with only half the pieces per side.",
            g.official_rules = "Played like Chess but with only 16 pieces per player instead of 32."
        '''
        execute_query(session, half_chess_query, "Game: Half Chess")
        
        los_alamos_query = '''
        MERGE (g:LudiiGame {name: "Los Alamos Chess"})
        SET g.official_populated = true,
            g.official_description = "Chess variant played on 6x6 board without bishops.",
            g.official_rules = "Played on 6x6 board. Each side has 12 pieces arranged in two rows. The front row consists of 6 pawns, and the back row has 2 rooks, 1 knight, 1 queen, 1 king, 1 rook (from left to right). No bishops are used."
        '''
        execute_query(session, los_alamos_query, "Game: Los Alamos Chess")
        
        symmetric_query = '''
        MERGE (g:LudiiGame {name: "Symmetric Chess"})
        SET g.official_populated = true,
            g.official_description = "Chess variant with symmetric starting position.",
            g.official_rules = "Played like Chess but with a symmetric starting position where the pieces are arranged identically for both players."
        '''
        execute_query(session, symmetric_query, "Game: Symmetric Chess")
        
        double_query = '''
        MERGE (g:LudiiGame {name: "Double Chess"})
        SET g.official_populated = true,
            g.official_description = "Chess variant played on 16x8 board with doubled pieces.",
            g.official_rules = "Played on 16x8 board with 64 pieces per side (two standard chess sets combined). Rules are the same as standard Chess."
        '''
        execute_query(session, double_query, "Game: Double Chess")
        
        # ========== ÉTAPE 6: LIER CHESS ==========
        print("\n[6/14] LIER CHESS AUX PERIODS...")
        execute_query(session, 
            'MATCH (g:LudiiGame {name: "Chess"}) MATCH (p:Period {name: "Medieval"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Chess → Medieval")
        execute_query(session, 
            'MATCH (g:LudiiGame {name: "Chess"}) MATCH (p:Period {name: "Modern"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Chess → Modern")
        
        print("\n[7/14] LIER CHESS AUX REGIONS...")
        regions_chess = ["Northern America", "Eastern Europe", "Northern Europe", "Southern Europe", "Western Europe"]
        for region in regions_chess:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Chess"}}) MATCH (r:Region {{name: "{region}"}}) MERGE (g)-[:FROM_REGION]->(r)',
                f"Chess → {region}")
        
        print("\n[8/14] LIER CHESS AUX CATEGORIES...")
        categories_chess = ["Board", "War", "Replacement", "Checkmate", "Chess"]
        for category in categories_chess:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Chess"}}) MATCH (c:Category {{name: "{category}"}}) MERGE (g)-[:IN_CATEGORY]->(c)',
                f"Chess → {category}")
        
        print("\n[9/14] LIER CHESS À L'ORIGIN...")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Chess"}) MATCH (o:Origin {name: "Europe"}) MERGE (g)-[:ORIGINATES_FROM]->(o)',
            "Chess → Europe")
        
        # ========== ÉTAPE 7-10: LIER AUTRES JEUX ==========
        print("\n[10/14] LIER HALF CHESS AUX ATTRIBUTS...")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Half Chess"}) MATCH (p:Period {name: "Modern"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Half Chess → Modern")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Half Chess"}) MATCH (r:Region {name: "Europe"}) MERGE (g)-[:FROM_REGION]->(r)',
            "Half Chess → Europe")
        for category in ["Board", "War", "Chess"]:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Half Chess"}}) MATCH (c:Category {{name: "{category}"}}) MERGE (g)-[:IN_CATEGORY]->(c)',
                f"Half Chess → {category}")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Half Chess"}) MATCH (o:Origin {name: "Europe"}) MERGE (g)-[:ORIGINATES_FROM]->(o)',
            "Half Chess → Europe")
        
        print("\n[11/14] LIER LOS ALAMOS CHESS AUX ATTRIBUTS...")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Los Alamos Chess"}) MATCH (p:Period {name: "Modern"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Los Alamos Chess → Modern")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Los Alamos Chess"}) MATCH (r:Region {name: "Northern America"}) MERGE (g)-[:FROM_REGION]->(r)',
            "Los Alamos Chess → Northern America")
        for category in ["Board", "War", "Chess"]:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Los Alamos Chess"}}) MATCH (c:Category {{name: "{category}"}}) MERGE (g)-[:IN_CATEGORY]->(c)',
                f"Los Alamos Chess → {category}")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Los Alamos Chess"}) MATCH (o:Origin {name: "Northern America"}) MERGE (g)-[:ORIGINATES_FROM]->(o)',
            "Los Alamos Chess → Northern America")
        
        print("\n[12/14] LIER SYMMETRIC CHESS AUX ATTRIBUTS...")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Symmetric Chess"}) MATCH (p:Period {name: "Modern"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Symmetric Chess → Modern")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Symmetric Chess"}) MATCH (r:Region {name: "Europe"}) MERGE (g)-[:FROM_REGION]->(r)',
            "Symmetric Chess → Europe")
        for category in ["Board", "War", "Chess"]:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Symmetric Chess"}}) MATCH (c:Category {{name: "{category}"}}) MERGE (g)-[:IN_CATEGORY]->(c)',
                f"Symmetric Chess → {category}")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Symmetric Chess"}) MATCH (o:Origin {name: "Europe"}) MERGE (g)-[:ORIGINATES_FROM]->(o)',
            "Symmetric Chess → Europe")
        
        print("\n[13/14] LIER DOUBLE CHESS AUX ATTRIBUTS...")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Double Chess"}) MATCH (p:Period {name: "Modern"}) MERGE (g)-[:FROM_PERIOD]->(p)',
            "Double Chess → Modern")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Double Chess"}) MATCH (r:Region {name: "Europe"}) MERGE (g)-[:FROM_REGION]->(r)',
            "Double Chess → Europe")
        for category in ["Board", "War", "Chess"]:
            execute_query(session,
                f'MATCH (g:LudiiGame {{name: "Double Chess"}}) MATCH (c:Category {{name: "{category}"}}) MERGE (g)-[:IN_CATEGORY]->(c)',
                f"Double Chess → {category}")
        execute_query(session,
            'MATCH (g:LudiiGame {name: "Double Chess"}) MATCH (o:Origin {name: "Europe"}) MERGE (g)-[:ORIGINATES_FROM]->(o)',
            "Double Chess → Europe")
        
        # ========== ÉTAPE 11: CRÉER SIMILAR_TO ==========
        print("\n[14/14] CRÉER LES RELATIONS SIMILAR_TO...")
        variants = ["Half Chess", "Los Alamos Chess", "Symmetric Chess", "Double Chess"]
        for variant in variants:
            execute_query(session,
                f'MATCH (g1:LudiiGame {{name: "{variant}"}}) MATCH (g2:LudiiGame {{name: "Chess"}}) MERGE (g1)-[:SIMILAR_TO]->(g2) MERGE (g2)-[:SIMILAR_TO]->(g1)',
                f"{variant} ↔ Chess")
        
        # ========== VÉRIFICATION ==========
        print("\n[Vérification] Checking data...")
        print("-" * 100)
        
        result = session.run("""
            MATCH (g:LudiiGame {official_populated: true})
            RETURN COUNT(g) as count
        """).single()['count']
        print(f"  ✅ Games with official data: {result}")
        
        result = session.run("""
            MATCH (n:Period)
            RETURN COUNT(n) as count
        """).single()['count']
        print(f"  ✅ Period nodes: {result}")
        
        result = session.run("""
            MATCH (n:Region)
            RETURN COUNT(n) as count
        """).single()['count']
        print(f"  ✅ Region nodes: {result}")
        
        result = session.run("""
            MATCH (n:Category)
            RETURN COUNT(n) as count
        """).single()['count']
        print(f"  ✅ Category nodes: {result}")
        
        result = session.run("""
            MATCH (g:LudiiGame)-[:FROM_PERIOD]->(p:Period)
            RETURN COUNT(*) as count
        """).single()['count']
        print(f"  ✅ FROM_PERIOD relationships: {result}")
        
        result = session.run("""
            MATCH (g:LudiiGame)-[:FROM_REGION]->(r:Region)
            RETURN COUNT(*) as count
        """).single()['count']
        print(f"  ✅ FROM_REGION relationships: {result}")
        
        result = session.run("""
            MATCH (g:LudiiGame)-[:IN_CATEGORY]->(c:Category)
            RETURN COUNT(*) as count
        """).single()['count']
        print(f"  ✅ IN_CATEGORY relationships: {result}")
        
        result = session.run("""
            MATCH (g:LudiiGame)-[:SIMILAR_TO]->(other)
            RETURN COUNT(*) as count
        """).single()['count']
        print(f"  ✅ SIMILAR_TO relationships: {result}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.close()

print("\n" + "=" * 100)
print("✅ NEO4J POPULATION COMPLETED SUCCESSFULLY!")
print("=" * 100)
print("""
Verify in Neo4j Browser:
  
  # Check official data
  MATCH (g:LudiiGame {official_populated: true}) RETURN g.name, g.official_description LIMIT 5
  
  # Check Period relationships
  MATCH (g:LudiiGame)-[:FROM_PERIOD]->(p:Period) RETURN g.name, p.name LIMIT 10
  
  # Check Region relationships
  MATCH (g:LudiiGame)-[:FROM_REGION]->(r:Region) RETURN g.name, r.name LIMIT 10
  
  # Check similar games
  MATCH (g1:LudiiGame)-[:SIMILAR_TO]->(g2:LudiiGame) RETURN g1.name, g2.name
  
  # Check all statistics
  MATCH (n) RETURN labels(n)[0] as type, COUNT(*) as count ORDER BY count DESC
""")