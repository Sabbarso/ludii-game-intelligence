import re
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ParsedGame:
    name:           str
    players:        Optional[int] = None
    board_type:     str           = ""
    pieces:         list          = field(default_factory=list)
    rules_raw:      str           = ""
    win_conditions: list          = field(default_factory=list)

    def to_text_chunks(self) -> list:
        chunks = []
        chunks.append(
            f"Game: {self.name}. "
            f"Players: {self.players}. "
            f"Board: {self.board_type}."
        )
        if self.pieces:
            chunks.append(
                f"Pieces in {self.name}: {', '.join(self.pieces)}."
            )
        if self.rules_raw:
            chunks.append(
                f"Rules for {self.name}: {self.rules_raw[:600]}"
            )
        if self.win_conditions:
            chunks.append(
                f"Win conditions for {self.name}: "
                f"{', '.join(self.win_conditions)}."
            )
        return chunks

class LudParser:

    def parse(self, lud_content: str, game_name: str = "",
              rules_text: str = "") -> ParsedGame:
        game = ParsedGame(
            name=game_name or self._extract_name(lud_content)
        )
        game.players        = self._extract_players(lud_content)
        game.board_type     = self._extract_board(lud_content)
        game.pieces         = self._extract_pieces(lud_content)
        game.win_conditions = self._extract_win_conditions(lud_content)
        game.rules_raw      = rules_text or self._extract_rules_block(lud_content)
        return game

    def _extract_name(self, c):
        m = re.search(r'\(game\s+"([^"]+)"', c)
        return m.group(1) if m else "Unknown"

    def _extract_players(self, c):
        m = re.search(r'\(players\s+(\d+)\)', c)
        return int(m.group(1)) if m else None

    def _extract_board(self, c):
        m = re.search(r'\(board\s+([^)]+)\)', c)
        return m.group(1).strip() if m else ""

    def _extract_pieces(self, c):
        return re.findall(r'\(piece\s+"([^"]+)"', c)

    def _extract_rules_block(self, c):
        m = re.search(r'\(rules(.*?)\)\s*\)', c, re.DOTALL)
        return m.group(1).strip()[:800] if m else ""

    def _extract_win_conditions(self, c):
        found = re.findall(r'(Win|Draw|Loss)\)', c)
        return list(set(found))

if __name__ == "__main__":
    parser = LudParser()
    sample = ('(game "Ludo" (players 4) '
              '(equipment {(piece "Counter" Each)}) '
              '(rules (end (result Mover Win))))')
    game = parser.parse(
        sample, "Ludo",
        rules_text="Players roll dice to move pawns. First to finish wins."
    )
    print(f"Name:    {game.name}")
    print(f"Players: {game.players}")
    print(f"Pieces:  {game.pieces}")
    print(f"\nChunks ({len(game.to_text_chunks())}):")
    for i, c in enumerate(game.to_text_chunks()):
        print(f"  [{i}] {c[:80]}")