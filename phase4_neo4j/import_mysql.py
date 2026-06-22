import mysql.connector
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Charger les variables d'environnement (.env)
load_dotenv()

# -------------------------------
# Connexion MySQL (XAMPP)
# -------------------------------
try:
    mysql_conn = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",          # mot de passe vide par défaut sur XAMPP
        database="ludiiGames"
    )
    cursor = mysql_conn.cursor(dictionary=True)
    print("✅ Connexion MySQL réussie.")
except Exception as e:
    print(f"❌ Erreur MySQL : {e}")
    exit(1)

# -------------------------------
# Connexion Neo4j
# -------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        session.run("RETURN 1")
    print("✅ Connexion Neo4j réussie.")
except Exception as e:
    print(f"❌ Erreur Neo4j : {e}")
    exit(1)

def exec_neo4j(query, parameters=None):
    """Exécute une requête Cypher avec paramètres."""
    with driver.session() as session:
        session.run(query, parameters or {})

# -------------------------------
# 0. Nettoyage des anciens nœuds
# -------------------------------
print("🧹 Suppression des anciens nœuds (Game, Ruleset, Category, Region, Period)...")
exec_neo4j(
    "MATCH (n) WHERE n:Game OR n:Ruleset OR n:Category OR n:Region OR n:Period DETACH DELETE n"
 )

# -------------------------------
# 1. Import des Périodes
# -------------------------------
print("📅 Import des périodes...")
cursor.execute("SELECT Id, Period FROM periods")
for row in cursor.fetchall():
    exec_neo4j(
        "CREATE (:Period {id: $id, name: $name})",
        {"id": row["Id"], "name": row["Period"]}
    )

# -------------------------------
# 2. Import des Régions
# -------------------------------
print("🌍 Import des régions...")
cursor.execute("SELECT id, Region, Continent FROM regions")
for row in cursor.fetchall():
    exec_neo4j(
        "CREATE (:Region {id: $id, name: $name, continent: $continent})",
        {"id": row["id"], "name": row["Region"], "continent": row["Continent"]}
    )

# -------------------------------
# 3. Import des Catégories
# -------------------------------
print("🏷️ Import des catégories...")
cursor.execute("SELECT Id, Category, Description FROM categories")
for row in cursor.fetchall():
    exec_neo4j(
        "CREATE (:Category {id: $id, name: $name, description: $desc})",
        {"id": row["Id"], "name": row["Category"], "desc": row["Description"]}
    )

# -------------------------------
# 4. Import des Jeux
# -------------------------------
print("🎲 Import des jeux...")
cursor.execute("""
    SELECT Id, Name, NativeName, Description, Origin, knownAliases, Date
    FROM games
    WHERE PublicGame = 1
""")
games = cursor.fetchall()
for g in games:
    exec_neo4j(
        """CREATE (:Game {
            id: $id, name: $name, nativeName: $native,
            description: $desc, origin: $origin,
            aliases: $aliases, date: $date
        })""",
        {
            "id": g["Id"],
            "name": g["Name"],
            "native": g["NativeName"],
            "desc": g["Description"],
            "origin": g["Origin"],
            "aliases": g["knownAliases"],
            "date": str(g["Date"]) if g["Date"] else None
        }
    )

# -------------------------------
# 5. Import des Règles (GameRulesets)
# -------------------------------
print("📜 Import des règles...")
cursor.execute("""
    SELECT Id, GameId, Name, Summary, Description, Rules, Origin, CompletionScore, CulturalScore
    FROM gamerulesets
""")
rulesets = cursor.fetchall()
for rs in rulesets:
    exec_neo4j(
        """CREATE (:Ruleset {
            id: $id, gameId: $gid, name: $name,
            summary: $summary, description: $desc,
            rules: $rules, origin: $origin,
            completionScore: $cs, culturalScore: $cus
        })""",
        {
            "id": rs["Id"],
            "gid": rs["GameId"],
            "name": rs["Name"],
            "summary": rs["Summary"],
            "desc": rs["Description"],
            "rules": rs["Rules"],
            "origin": rs["Origin"],
            "cs": rs["CompletionScore"] if rs["CompletionScore"] is not None else 0.0,
            "cus": rs["CulturalScore"] if rs["CulturalScore"] is not None else 0.0
        }
    )

# -------------------------------
# 6. Relations Game -> Ruleset
# -------------------------------
print("🔗 Relations Game → Ruleset...")
for rs in rulesets:
    exec_neo4j(
        "MATCH (g:Game {id: $gid}), (r:Ruleset {id: $rid}) MERGE (g)-[:HAS_RULESET]->(r)",
        {"gid": rs["GameId"], "rid": rs["Id"]}
    )

# -------------------------------
# 7. Relations Game -> Category
# -------------------------------
print("🔗 Relations Game → Category...")
cursor.execute("SELECT GameId, CategoryId FROM gamecategories")
for row in cursor.fetchall():
    exec_neo4j(
        "MATCH (g:Game {id: $gid}), (c:Category {id: $cid}) MERGE (g)-[:IN_CATEGORY]->(c)",
        {"gid": row["GameId"], "cid": row["CategoryId"]}
    )

# -------------------------------
# 8. Relations Game -> Region
# -------------------------------
print("🔗 Relations Game → Region...")
cursor.execute("SELECT GameId, RegionId, OriginRegion FROM gameregions")
for row in cursor.fetchall():
    origin = (row["OriginRegion"] == 1)
    exec_neo4j(
        "MATCH (g:Game {id: $gid}), (r:Region {id: $rid}) MERGE (g)-[:FROM_REGION {origin: $origin}]->(r)",
        {"gid": row["GameId"], "rid": row["RegionId"], "origin": origin}
    )

# -------------------------------
# 9. Relations Game -> Period
# -------------------------------
print("🔗 Relations Game → Period...")
cursor.execute("SELECT GameId, PeriodId FROM gameperiods")
for row in cursor.fetchall():
    exec_neo4j(
        "MATCH (g:Game {id: $gid}), (p:Period {id: $pid}) MERGE (g)-[:FROM_PERIOD]->(p)",
        {"gid": row["GameId"], "pid": row["PeriodId"]}
    )

# -------------------------------
# 10. Relations Ruleset -> Ruleset (ancêtres)
# -------------------------------
print("🔗 Relations Ruleset → Ruleset (ancestors)...")
cursor.execute("SELECT rulesetId1, rulesetId2 FROM ancestors")
for row in cursor.fetchall():
    exec_neo4j(
        "MATCH (r1:Ruleset {id: $id1}), (r2:Ruleset {id: $id2}) MERGE (r1)-[:VARIANT_OF]->(r2)",
        {"id1": row["rulesetId1"], "id2": row["rulesetId2"]}
    )

# -------------------------------
# 11. Relations Ruleset -> Ruleset (successeurs)
# -------------------------------
print("🔗 Relations Ruleset → Ruleset (successors)...")
cursor.execute("SELECT rulesetId1, rulesetId2 FROM successors")
for row in cursor.fetchall():
    exec_neo4j(
        "MATCH (r1:Ruleset {id: $id1}), (r2:Ruleset {id: $id2}) MERGE (r1)-[:VARIANT_OF]->(r2)",
        {"id1": row["rulesetId1"], "id2": row["rulesetId2"]}
    )

# -------------------------------
# Nettoyage final
# -------------------------------
cursor.close()
mysql_conn.close()
driver.close()
print("\n🎉 Importation terminée avec succès !")
print("Vérifie dans Neo4j Browser : http://localhost:7474")