import requests
from bs4 import BeautifulSoup
import os, time, json

BASE_URL   = "https://ludii.games"
OUTPUT_DIR = "./phase1_ludii_rag/datasets/raw_lud"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class LudiiScraper:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (LudoIntelligence Research Bot)"
        })

    def fetch_game_list(self):
        print("Fetching game list from ludii.games...")
        try:
            resp = self.session.get(f"{BASE_URL}/library.php", timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            games = []
            for link in soup.select("a[href*='game=']"):
                name = link.text.strip()
                url  = BASE_URL + "/" + link["href"]
                if name:
                    games.append({"name": name, "url": url})
            print(f"Found {len(games)} games")
            return games if games else self.get_fallback_games()
        except Exception as e:
            print(f"Scraping failed: {e} - using fallback data")
            return self.get_fallback_games()

    def fetch_game_rules(self, game: dict) -> dict:
        # ← FIX : si URL vide, retourner directement les données fallback
        if not game.get("url"):
            return game

        try:
            resp = self.session.get(game["url"], timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            rules_div = (soup.find("div", class_="ludRules") or
                         soup.find("div", id="rules") or
                         soup.find("div", class_="description"))
            rules_text = (rules_div.get_text(separator="\n").strip()
                          if rules_div else "")
            lud_link = soup.find(
                "a", href=lambda h: h and h.endswith(".lud")
            )
            lud_content = ""
            if lud_link:
                lud_url = BASE_URL + lud_link["href"]
                lud_content = self.session.get(lud_url, timeout=10).text
            return {
                "name":        game["name"],
                "url":         game["url"],
                "rules_text":  rules_text,
                "lud_content": lud_content
            }
        except Exception as e:
            print(f"  Failed {game['name']}: {e}")
            return {**game, "rules_text": "", "lud_content": ""}

    def scrape_all(self, limit=None, delay=1.5):
        games = self.fetch_game_list()
        if limit:
            games = games[:limit]
        results = []
        for i, game in enumerate(games):
            print(f"  [{i+1}/{len(games)}] {game['name']}")
            data = self.fetch_game_rules(game)
            results.append(data)
            if data.get("lud_content"):
                safe = game["name"].replace(" ", "_").lower()
                path = os.path.join(OUTPUT_DIR, safe + ".lud")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data["lud_content"])
            time.sleep(delay)
        index_path = os.path.join(OUTPUT_DIR, "games_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nDone - {len(results)} games saved to {OUTPUT_DIR}")
        return results

    def get_fallback_games(self):
        return [
            {
                "name": "Ludo",
                "url": "",
                "rules_text": (
                    "Players move 4 pawns from home to finish. "
                    "Roll a 6 to enter a pawn on the board. "
                    "Landing on opponent sends them back to start. "
                    "First player to bring all pawns home wins."
                ),
                "lud_content": (
                    '(game "Ludo" (players 4) '
                    '(equipment {(board (spiral 56 4))'
                    '(piece "Counter" Each)}) '
                    '(rules (end (result Mover Win))))'
                )
            },
            {
                "name": "Chess",
                "url": "",
                "rules_text": (
                    "Each player has 16 pieces on an 8x8 board. "
                    "Pawns move forward one square or two on first move. "
                    "Rooks move horizontally or vertically any number of squares. "
                    "Bishops move diagonally any number of squares. "
                    "Knights move in an L-shape. Queen combines rook and bishop. "
                    "Checkmate the opponent king to win."
                ),
                "lud_content": (
                    '(game "Chess" (players 2) '
                    '(equipment {(board (square 8))'
                    '(piece "Pawn" Each)}) '
                    '(rules (end (result Mover Win))))'
                )
            },
            {
                "name": "Reversi",
                "url": "",
                "rules_text": (
                    "Players place discs on an 8x8 board. "
                    "A valid move traps one or more opponent discs between yours. "
                    "Trapped discs flip to your color. "
                    "If you cannot move you must pass. "
                    "Game ends when neither player can move. "
                    "Player with most discs wins."
                ),
                "lud_content": (
                    '(game "Reversi" (players 2) '
                    '(equipment {(board (square 8))'
                    '(piece "Disc" Each)}) '
                    '(rules (end (result Mover Win))))'
                )
            },
            {
                "name": "Checkers",
                "url": "",
                "rules_text": (
                    "Pieces move diagonally forward one square. "
                    "Capture by jumping over opponent pieces diagonally. "
                    "Multiple captures in one turn are allowed. "
                    "Reach the last row to become a King. "
                    "Kings move both forward and backward diagonally."
                ),
                "lud_content": (
                    '(game "Checkers" (players 2) '
                    '(equipment {(board (square 8))'
                    '(piece "Piece" Each)}) '
                    '(rules (end (result Mover Win))))'
                )
            },
            {
                "name": "TicTacToe",
                "url": "",
                "rules_text": (
                    "Players alternate placing X or O on a 3x3 grid. "
                    "First to align 3 symbols horizontally vertically "
                    "or diagonally wins. "
                    "If board fills with no winner the game is a draw."
                ),
                "lud_content": (
                    '(game "TicTacToe" (players 2) '
                    '(equipment {(board (square 3))'
                    '(piece "Marker" Each)}) '
                    '(rules (end (result Mover Win))))'
                )
            }
        ]


if __name__ == "__main__":
    scraper = LudiiScraper()
    data = scraper.scrape_all(limit=5)
    print(f"\nSample: {data[0]['name']} - {len(data[0]['rules_text'])} chars")