from fastapi import APIRouter, HTTPException
from phase4_neo4j.pipeline import Neo4jPipeline
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/api/v1", tags=["yolo"])

class YOLODetectionResult(BaseModel):
    board_cols: int
    board_rows: int
    total_pieces: int
    pieces: List[Dict]  # [{"type": "rook", "color": "white", "x": 64, "y": 480}, ...]
    confidence: float

@router.post("/identify_game_from_yolo")
async def identify_game(yolo_result: YOLODetectionResult):
    """
    Input: YOLO detection result (board dims + pieces)
    Output: Identified game
    """
    
    try:
        pipeline = Neo4jPipeline()
        
        with pipeline.driver.session() as session:
            # Extraire types de pièces détectées
            detected_piece_types = list(set([p["type"] for p in yolo_result.pieces]))
            
            # STRATEGY 1: Match par dimensions + total pièces (exact match)
            result = session.run("""
                MATCH (sig:YOLOSignature)
                WHERE sig.board_cols = $cols
                AND sig.board_rows = $rows
                AND sig.total_pieces = $total
                MATCH (g:LudiiGame {name: sig.game_name})
                RETURN sig.game_name as game, g.official_description as desc, g.official_rules as rules
                LIMIT 1
            """,
            cols=yolo_result.board_cols,
            rows=yolo_result.board_rows,
            total=yolo_result.total_pieces
            ).data()
            
            if result:
                game = result[0]
                return {
                    "status": "success",
                    "identified_game": game['game'],
                    "confidence": 0.95,
                    "yolo_detection": {
                        "board": [yolo_result.board_cols, yolo_result.board_rows],
                        "total_pieces": yolo_result.total_pieces,
                        "piece_types": detected_piece_types
                    },
                    "game_details": {
                        "description": game['desc'],
                        "rules": game['rules']
                    }
                }
            
            # STRATEGY 2: Match flexible (tolérance erreurs détection)
            result = session.run("""
                MATCH (sig:YOLOSignature)
                WHERE sig.board_cols = $cols
                AND sig.board_rows = $rows
                AND ABS(sig.total_pieces - $total) <= 5
                WITH sig
                MATCH (g:LudiiGame {name: sig.game_name})
                RETURN sig.game_name as game, 
                       g.official_description as desc,
                       g.official_rules as rules,
                       sig.total_pieces as expected_pieces
                ORDER BY ABS(sig.total_pieces - $total)
                LIMIT 1
            """,
            cols=yolo_result.board_cols,
            rows=yolo_result.board_rows,
            total=yolo_result.total_pieces
            ).data()
            
            if result:
                game = result[0]
                match_ratio = yolo_result.total_pieces / game['expected_pieces']
                return {
                    "status": "partial_match",
                    "identified_game": game['game'],
                    "confidence": min(0.85, match_ratio * 0.95),
                    "yolo_detection": {
                        "board": [yolo_result.board_cols, yolo_result.board_rows],
                        "total_pieces": yolo_result.total_pieces,
                        "piece_types": detected_piece_types
                    },
                    "game_details": {
                        "description": game['desc'],
                        "rules": game['rules']
                    }
                }
            
            raise HTTPException(404, "No matching game found in database")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")