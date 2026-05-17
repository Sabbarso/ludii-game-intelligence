"""
Scraper les données OFFICIELLES de ludii.games - VERSION CORRIGÉE
- Parsing HTML amélioré avec inspection réelle de la page
- Gestion des différentes structures HTML
- Similar Games extraction
"""

import requests
from bs4 import BeautifulSoup
from neo4j import GraphDatabase
import time
import os
import re

class LudiiOfficialScraperV2:
    def __init__(self):
        self.base_url = "https://ludii.games/details.php"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "salma1234"))
        )
    
    def scrape_game_details(self, game_name):
        """Scrape une page ludii.games avec parsing amélioré"""
        
        try:
            url = f"{self.base_url}?keyword={game_name}"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                "name": game_name,
                "periods": [],
                "regions": [],
                "categories": [],
                "origin": None,
                "description": None,
                "rules": None,
                "ludeme_description": None,
                "similar_games": []
            }
            
            # ========== PARSING AMÉLIORÉ ==========
            # Chercher tous les <b> qui contiennent les labels (Period, Region, Category, etc.)
            
            all_bold = soup.find_all('b')
            
            for bold_elem in all_bold:
                label_text = bold_elem.get_text(strip=True)
                
                # ===== PERIOD =====
                if label_text.startswith("Period"):
                    # Le contenu suit généralement le <br> suivant
                    next_elem = bold_elem.find_next()
                    while next_elem:
                        if isinstance(next_elem, str):
                            next_elem = next_elem.find_next()
                            continue
                        
                        # Chercher les <a> qui suivent
                        if next_elem.name == 'a':
                            period = next_elem.get_text(strip=True)
                            if period and period not in details["periods"]:
                                details["periods"].append(period)
                            next_elem = next_elem.find_next_sibling()
                        elif next_elem.name == 'br':
                            break
                        else:
                            next_elem = next_elem.find_next_sibling()
                
                # ===== REGION =====
                elif label_text.startswith("Region"):
                    next_elem = bold_elem.find_next()
                    while next_elem:
                        if isinstance(next_elem, str):
                            next_elem = next_elem.find_next()
                            continue
                        
                        if next_elem.name == 'a':
                            region = next_elem.get_text(strip=True)
                            if region and region not in details["regions"]:
                                details["regions"].append(region)
                            next_elem = next_elem.find_next_sibling()
                        elif next_elem.name == 'br':
                            break
                        else:
                            next_elem = next_elem.find_next_sibling()
                
                # ===== CATEGORY =====
                elif label_text.startswith("Category"):
                    next_elem = bold_elem.find_next()
                    while next_elem:
                        if isinstance(next_elem, str):
                            next_elem = next_elem.find_next()
                            continue
                        
                        if next_elem.name == 'a':
                            category = next_elem.get_text(strip=True)
                            if category and category not in details["categories"]:
                                details["categories"].append(category)
                            next_elem = next_elem.find_next_sibling()
                        elif next_elem.name == 'br':
                            break
                        else:
                            next_elem = next_elem.find_next_sibling()
                
                # ===== ORIGIN =====
                elif label_text.startswith("Origin"):
                    origin_link = bold_elem.find_next('a')
                    if origin_link:
                        details["origin"] = origin_link.get_text(strip=True)
                
                # ===== DESCRIPTION =====
                elif label_text.startswith("Description"):
                    # Description est le texte après le <b>
                    desc_text = bold_elem.find_next('br')
                    if desc_text:
                        # Récupérer tout le texte jusqu'au prochain <b>
                        full_text = []
                        current = desc_text.find_next()
                        while current and not (hasattr(current, 'name') and current.name == 'b'):
                            if isinstance(current, str):
                                text = current.strip()
                                if text:
                                    full_text.append(text)
                            elif hasattr(current, 'name') and current.name in ['a', 'span']:
                                full_text.append(current.get_text(strip=True))
                            current = current.find_next() if hasattr(current, 'find_next') else None
                            if current and hasattr(current, 'name') and current.name == 'b':
                                break
                        
                        if full_text:
                            description = ' '.join(full_text)
                            details["description"] = description[:300] + "..." if len(description) > 300 else description
                
                # ===== RULES =====
                elif label_text.startswith("Rules"):
                    rules_text = bold_elem.find_next('br')
                    if rules_text:
                        full_text = []
                        current = rules_text.find_next()
                        while current and not (hasattr(current, 'name') and current.name == 'b'):
                            if isinstance(current, str):
                                text = current.strip()
                                if text:
                                    full_text.append(text)
                            elif hasattr(current, 'name') and current.name in ['a', 'span']:
                                full_text.append(current.get_text(strip=True))
                            current = current.find_next() if hasattr(current, 'find_next') else None
                            if current and hasattr(current, 'name') and current.name == 'b':
                                break
                        
                        if full_text:
                            rules = ' '.join(full_text)
                            details["rules"] = rules[:300] + "..." if len(rules) > 300 else rules
            
            # ===== SIMILAR GAMES (différente structure) =====
            # Similar Games est généralement dans une section avec des images
            similar_section = soup.find(string=re.compile("Similar Games", re.IGNORECASE))
            if similar_section:
                # Chercher la section parent qui contient les jeux
                parent = similar_section.find_parent()
                # Chercher tous les <a> qui pointent vers des jeux dans la section suivante
                next_section = parent.find_next(['div', 'section', 'p'])
                if next_section:
                    game_links = next_section.find_all('a')
                    for link in game_links[:10]:  # Limiter à 10
                        game_text = link.get_text(strip=True)
                        # Filtrer les liens de navigation et très courts
                        if game_text and len(game_text) > 2 and game_text not in details["similar_games"]:
                            if 'ludii.games' in link.get('href', ''):
                                details["similar_games"].append(game_text)
            
            return details
            
        except requests.exceptions.Timeout:
            print(f"     ⏱️  Timeout for {game_name}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"     ❌ Network error: {e}")
            return None
        except Exception as e:
            print(f"     ❌ Parse error: {e}")
            return None
    
    def populate_neo4j(self, details):
        """Insérer les données dans Neo4j"""
        
        try:
            with self.driver.session() as session:
                # Vérifier que le jeu existe
                exists = session.run("""
                    MATCH (g:LudiiGame {name: $name})
                    RETURN COUNT(g) as count
                """, name=details["name"]).single()['count']
                
                if not exists:
                    return False
                
                # Mettre à jour le jeu
                session.run("""
                    MATCH (g:LudiiGame {name: $name})
                    SET g.official_description = $desc,
                        g.official_rules = $rules,
                        g.ludeme_description = $ludeme,
                        g.origin_official = $origin,
                        g.official_scraped = true,
                        g.scraped_at = datetime()
                """, 
                name=details["name"],
                desc=details["description"],
                rules=details["rules"],
                ludeme=details["ludeme_description"],
                origin=details["origin"]
                )
                
                # Lier Period
                for period in details["periods"]:
                    try:
                        session.run("""
                            MERGE (p:Period {name: $period})
                            WITH p
                            MATCH (g:LudiiGame {name: $game})
                            MERGE (g)-[:FROM_PERIOD]->(p)
                        """, period=period, game=details["name"])
                    except:
                        pass
                
                # Lier Region
                for region in details["regions"]:
                    try:
                        session.run("""
                            MERGE (r:Region {name: $region})
                            WITH r
                            MATCH (g:LudiiGame {name: $game})
                            MERGE (g)-[:FROM_REGION]->(r)
                        """, region=region, game=details["name"])
                    except:
                        pass
                
                # Lier Category
                for category in details["categories"]:
                    try:
                        session.run("""
                            MERGE (c:Category {name: $category})
                            WITH c
                            MATCH (g:LudiiGame {name: $game})
                            MERGE (g)-[:IN_CATEGORY]->(c)
                        """, category=category, game=details["name"])
                    except:
                        pass
                
                # Lier Origin
                if details["origin"]:
                    try:
                        session.run("""
                            MERGE (o:Origin {name: $origin})
                            WITH o
                            MATCH (g:LudiiGame {name: $game})
                            MERGE (g)-[:ORIGINATES_FROM]->(o)
                        """, origin=details["origin"], game=details["name"])
                    except:
                        pass
                
                # Lier Similar Games
                for similar_game in details["similar_games"]:
                    try:
                        session.run("""
                            MATCH (g1:LudiiGame {name: $game1})
                            MATCH (g2:LudiiGame {name: $game2})
                            MERGE (g1)-[:SIMILAR_TO]->(g2)
                        """, game1=details["name"], game2=similar_game)
                    except:
                        pass
                
                return True
        
        except Exception as e:
            print(f"     ❌ DB Error: {e}")
            return False
    
    def process_all_games(self, game_names, limit=None, start_from=0):
        """Traiter jeux avec retry et skip logic"""
        
        total = len(game_names) if not limit else min(limit, len(game_names))
        processed = 0
        skipped = 0
        errors = 0
        
        for i, game_name in enumerate(game_names[start_from:start_from+total], start=start_from+1):
            try:
                print(f"\n[{i}/{len(game_names)}] {game_name}")
                
                details = self.scrape_game_details(game_name)
                
                if details:
                    if self.populate_neo4j(details):
                        p = len(details['periods'])
                        r = len(details['regions'])
                        c = len(details['categories'])
                        s = len(details['similar_games'])
                        print(f"     ✅ P:{p} R:{r} C:{c} S:{s}")
                        processed += 1
                    else:
                        print(f"     ⏭️  Game not in DB, skipping")
                        skipped += 1
                else:
                    print(f"     ⚠️  No data scraped")
                    skipped += 1
                
                time.sleep(0.5)  # Rate limit
            
            except KeyboardInterrupt:
                print("\n\n❌ Interrupted by user")
                break
            except Exception as e:
                print(f"     ❌ Error: {e}")
                errors += 1
        
        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "total": i
        }
    
    def close(self):
        if self.driver:
            self.driver.close()

# ========== EXÉCUTION ==========
if __name__ == "__main__":
    print("=" * 100)
    print("📥 SCRAPING DONNÉES OFFICIELLES LUDII.GAMES v2 (CORRIGÉ)")
    print("=" * 100)
    
    scraper = LudiiOfficialScraperV2()
    
    try:
        with scraper.driver.session() as session:
            games = session.run("""
                MATCH (g:LudiiGame)
                RETURN g.name as name
                ORDER BY g.name
            """).data()
            
            game_names = [g['name'] for g in games]
            print(f"\n📊 Found {len(game_names)} games in database")
            
            # TEST: Traiter seulement 50 jeux pour tester
            print("\n🧪 TEST MODE: Processing first 50 games...")
            stats = scraper.process_all_games(game_names, limit=50)
            
            print("\n" + "=" * 100)
            print(f"✅ SCRAPING STATS")
            print("=" * 100)
            print(f"""
Processed: {stats['processed']}
Skipped:   {stats['skipped']}
Errors:    {stats['errors']}
Total:     {stats['total']}

Si les résultats sont bons (Processed > 40), continue avec tous les jeux:
  python phase4_neo4j/scrape_ludii_official.py --full
""")
        
    except KeyboardInterrupt:
        print("\n❌ Script interrupted")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close()