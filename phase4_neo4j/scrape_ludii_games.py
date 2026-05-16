import requests
from bs4 import BeautifulSoup
from neo4j import GraphDatabase
import time

print("=" * 70)
print("🎲 SCRAPER LUDII GAMES")
print("=" * 70)

# ========== STEP 1: SCRAPER LUDII.GAMES ==========
print("\n[1/3] Scraping ludii.games/library.php...")

try:
    url = "https://ludii.games/library.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    all_links = soup.find_all('a')
    print(f"   Total de liens trouvés: {len(all_links)}")
    
    games = []
    navigation_words = ['home', 'sign in', 'register', 'forum', 'downloads', 
                       'references', 'concepts', 'contribute', 'tutorials', 
                       'tournaments', 'contact', 'about', 'ludii', 'library']
    
    for link in all_links:
        text = link.text.strip()
        
        if len(text) > 2 and text.lower() not in navigation_words:
            if text not in games:
                games.append(text)
    
    print(f"✅ Trouvé {len(games)} jeux uniques")
    
    print("\n   Premiers jeux détectés:")
    for i, game in enumerate(games[:20]):
        print(f"   {i+1:2d}. {game}")
    
except Exception as e:
    print(f"❌ Erreur scraping: {e}")
    print("Utilisation de données de fallback...")
    
    games = [
        'Ludo', 'Chess', 'Go', 'Checkers', 'Reversi', 'Hnefatafl',
        'Mancala', 'Nine Mens Morris', 'Tablut', 'Alquerque', 'Pachisi',
        'Shogi', 'Xiangqi', 'Janggi', 'Parchís', 'Gomoku', 'Connect Four',
        'Hex', 'Breakthrough', 'Pente', 'Fanorona', 'Seega', 'Walis'
    ]

# ========== STEP 2: CONNEXION NEO4J ==========
print(f"\n[2/3] Connexion à Neo4j...")

try:
    driver = GraphDatabase.driver(
        "neo4j://127.0.0.1:7687",
        auth=("neo4j", "salma1234")
    )
    
    with driver.session() as session:
        result = session.run("RETURN 'Connected' AS msg")
        msg = result.single()['msg']
    
    print(f"✅ Connecté à Neo4j")
    
except Exception as e:
    print(f"❌ Erreur connexion Neo4j: {e}")
    exit(1)

# ========== STEP 3: INSÉRER DANS NEO4J ==========
print(f"\n[3/3] Insertion dans Neo4j...")

try:
    inserted_count = 0
    
    with driver.session() as session:
        existing = session.run("MATCH (g:LudiiGame) RETURN COUNT(g) as count").single()
        existing_count = existing['count']
        print(f"   Jeux existants: {existing_count}")
        
        for i, game in enumerate(games, 1):
            try:
                session.run("""
                    MERGE (g:LudiiGame {name: $name})
                    SET g.source = 'ludii_official'
                    RETURN g
                """, name=game)
                
                inserted_count += 1
                
                if i % 10 == 0:
                    print(f"   Progression: {i}/{len(games)}")
                
            except Exception as e:
                print(f"   ⚠️  Erreur pour {game}: {e}")
        
        final_count = session.run("MATCH (g:LudiiGame) RETURN COUNT(g) as count").single()
        final_total = final_count['count']
    
    print(f"✅ Insertion terminée!")
    
except Exception as e:
    print(f"❌ Erreur insertion: {e}")
    exit(1)

print("\n" + "=" * 70)
print("🎉 SUCCÈS!")
print("=" * 70)
print(f"""
Résultats:
  • Jeux scrapés: {len(games)}
  • Jeux insérés: {inserted_count}
  • Total dans Neo4j: {final_total}
""")

print("=" * 70)

driver.close()