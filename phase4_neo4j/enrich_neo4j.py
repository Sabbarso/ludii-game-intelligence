"""
Enrichir Neo4j avec Familles et Civilisations
Crée les relations BELONGS_TO et ORIGINATED_IN
"""

from neo4j import GraphDatabase
import os

print("=" * 80)
print("🔗 NEO4J ENRICHMENT - Families & Civilizations")
print("=" * 80)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # ========== STEP 1: CREATE FAMILIES ==========
        print("\n[1/3] Creating game families...")
        
        families = {
            "Chess-like": ["Chess", "Shogi", "Xiangqi", "Janggi", "Makruk"],
            "Draughts": ["Checkers", "Alquerque", "Fanorona"],
            "Race games": ["Ludo", "Pachisi", "Parchís"],
            "Placement games": ["Nine Mens Morris", "Hnefatafl", "Tablut"],
            "Abstract": ["Go", "Hex", "Connect Four"],
            "Mancala variants": ["Mancala", "Seega", "Walis"],
            "Combinatorial": ["Reversi", "Pente", "Gomoku"]
        }
        
        for family_name, games in families.items():
            # Créer famille
            session.run("""
                MERGE (f:Family {name: $family})
            """, family=family_name)
            
            # Lier jeux à famille
            for game in games:
                session.run("""
                    MATCH (g:LudiiGame {name: $game})
                    MATCH (f:Family {name: $family})
                    MERGE (g)-[:BELONGS_TO]->(f)
                """, game=game, family=family_name)
            
            print(f"   ✅ {family_name}: {len(games)} games linked")
        
        family_count = session.run("""
            MATCH (f:Family) RETURN COUNT(f) as count
        """).single()['count']
        
        print(f"   ✅ Total families: {family_count}")
        
        # ========== STEP 2: CREATE CIVILIZATIONS ==========
        print("\n[2/3] Creating civilizations...")
        
        civilizations = {
            "India": ["Chess", "Pachisi", "Ludo", "Seega"],
            "China": ["Go", "Xiangqi", "Walis"],
            "Japan": ["Shogi", "Reversi"],
            "Korea": ["Janggi", "Baduk"],
            "Scandinavia": ["Hnefatafl", "Tablut"],
            "Europe": ["Nine Mens Morris", "Alquerque", "Checkers"],
            "Spain": ["Parchís"],
            "Africa": ["Mancala", "Fanorona"],
            "Middle East": ["Makruk"],
            "America": ["Connect Four", "Hex"]
        }
        
        for civ_name, games in civilizations.items():
            # Créer civilisation
            session.run("""
                MERGE (c:Civilization {name: $civ})
            """, civ=civ_name)
            
            # Lier jeux à civilisation
            for game in games:
                session.run("""
                    MATCH (g:LudiiGame {name: $game})
                    MATCH (c:Civilization {name: $civ})
                    MERGE (g)-[:ORIGINATED_IN]->(c)
                """, game=game, civ=civ_name)
            
            print(f"   ✅ {civ_name}: {len(games)} games linked")
        
        civ_count = session.run("""
            MATCH (c:Civilization) RETURN COUNT(c) as count
        """).single()['count']
        
        print(f"   ✅ Total civilizations: {civ_count}")
        
        # ========== STEP 3: CREATE VARIANT RELATIONSHIPS ==========
        print("\n[3/3] Creating variant relationships...")
        
        variants = {
            "Checkers": ["Alquerque"],  # Checkers dérivé d'Alquerque
            "Shogi": ["Chess"],         # Shogi similaire à Chess
            "Xiangqi": ["Chess"],       # Xiangqi similaire à Chess
            "Parchís": ["Pachisi"],     # Parchís dérivé de Pachisi
            "Fanorona": ["Alquerque"],  # Fanorona variante
            "Makruk": ["Chess"],        # Makruk variante de Chess
        }
        
        for game, parents in variants.items():
            for parent in parents:
                session.run("""
                    MATCH (g:LudiiGame {name: $game})
                    MATCH (p:LudiiGame {name: $parent})
                    MERGE (g)-[:VARIANT_OF]->(p)
                """, game=game, parent=parent)
            
            print(f"   ✅ {game}: linked to {len(parents)} parent(s)")
        
        # ========== STATISTICS ==========
        print("\n" + "=" * 80)
        print("📊 ENRICHMENT STATS")
        print("=" * 80)
        
        stats = session.run("""
            RETURN
                (MATCH (f:Family) RETURN COUNT(*)) as families,
                (MATCH (c:Civilization) RETURN COUNT(*)) as civilizations,
                (MATCH ()-[:BELONGS_TO]->() RETURN COUNT(*)) as belongs_relations,
                (MATCH ()-[:ORIGINATED_IN]->() RETURN COUNT(*)) as origin_relations,
                (MATCH ()-[:VARIANT_OF]->() RETURN COUNT(*)) as variant_relations
        """).single()
        
        # Count separately due to Neo4j limitations
        families = session.run("MATCH (f:Family) RETURN COUNT(f) as count").single()['count']
        civilizations = session.run("MATCH (c:Civilization) RETURN COUNT(c) as count").single()['count']
        belongs = session.run("MATCH ()-[:BELONGS_TO]->() RETURN COUNT(*) as count").single()['count']
        origins = session.run("MATCH ()-[:ORIGINATED_IN]->() RETURN COUNT(*) as count").single()['count']
        variants = session.run("MATCH ()-[:VARIANT_OF]->() RETURN COUNT(*) as count").single()['count']
        
        print(f"""
✅ Families: {families}
✅ Civilizations: {civilizations}
✅ BELONGS_TO relations: {belongs}
✅ ORIGINATED_IN relations: {origins}
✅ VARIANT_OF relations: {variants}

Total new relations: {belongs + origins + variants}
""")
        
        print("=" * 80)
        print("✅ NEO4J ENRICHMENT COMPLETE")
        print("=" * 80)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

finally:
    driver.close()