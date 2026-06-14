import csv
import ctypes
from neo4j import GraphDatabase
from dotenv import load_dotenv

csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))
load_dotenv()

driver = GraphDatabase.driver(
    "bolt://localhost:7687", 
    auth=("neo4j", "salma1234")
)

csv_path = r"C:\Users\pc\Documents\ludii_data\Data\RulesetFormatted.csv"

print("📖 Lecture de RulesetFormatted.csv...")

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    
    count = 0
    no_match = 0
    
    with driver.session() as session:
        for row in reader:
            if not row or len(row) < 3:
                continue
            
            csv_name = row[0].strip()
            ruleset_id = int(row[2].strip()) if row[2].strip().isdigit() else None
            lud_code = row[3] if len(row) > 3 else None
            
            matched_name = None
            
            # 1. Match exact
            r = session.run("MATCH (g:Game {name: $n}) RETURN g.name", n=csv_name)
            if r.single():
                matched_name = csv_name
            
            # 2. Sans parenthèses
            if not matched_name and '(' in csv_name:
                clean = csv_name.split('(')[0].strip()
                r = session.run("MATCH (g:Game {name: $n}) RETURN g.name", n=clean)
                if r.single():
                    matched_name = clean
            
            # 3. Le nom Neo4j contient le nom CSV
            if not matched_name:
                r = session.run("MATCH (g:Game) WHERE g.name CONTAINS $n RETURN g.name LIMIT 1", n=csv_name)
                rec = r.single()
                if rec:
                    matched_name = rec["g.name"]
            
            # 4. Le nom CSV est contenu dans le nom Neo4j
            if not matched_name:
                r = session.run("MATCH (g:Game) WHERE g.name STARTS WITH $n RETURN g.name LIMIT 1", n=csv_name)
                rec = r.single()
                if rec:
                    matched_name = rec["g.name"]
            
            if matched_name:
                if ruleset_id:
                    session.run("MATCH (g:Game {name: $n}) SET g.mappedRulesetId = $rid", n=matched_name, rid=ruleset_id)
                    session.run("MATCH (g:Game {name: $n}) MATCH (rs:Ruleset {id: $rid}) MERGE (g)-[:HAS_RULESET]->(rs)", n=matched_name, rid=ruleset_id)
                
                if lud_code:
                    session.run("MATCH (g:Game {name: $n}) SET g.ludCode = $lud", n=matched_name, lud=lud_code[:3000])
                
                count += 1
            else:
                no_match += 1
            
            if (count + no_match) % 200 == 0:
                print(f"  ✅ {count} enrichis | ⚠️ {no_match} sans match")
    
    print(f"\n🎉 {count} jeux enrichis")
    print(f"⚠️ {no_match} sans correspondance")

driver.close()