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
            
            # Query: Match exact
            game = session.run("""
                MATCH (sig:YOLOSignature)
                WHERE sig.board_cols = $cols
                AND sig.board_rows = $rows
                AND sig.total_pieces = $total
                AND ALL(piece IN sig.required_pieces WHERE piece IN $detected)
                MATCH (g:LudiiGame {name: sig.game_name})
                RETURN sig.game_name as game, g.official_description as desc, g.official_rules as rules, 0.95 as confidence
                LIMIT 1
            """,
            cols=yolo_result.board_cols,
            rows=yolo_result.board_rows,
            total=yolo_result.total_pieces,
            detected=detected_piece_types
            ).single()
            
            if game:
                return {
                    "status": "success",
                    "identified_game": game['game'],
                    "confidence": game['confidence'],
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
            
            # Query: Match flexible (si erreur)
            game = session.run("""
                MATCH (sig:YOLOSignature)
                WHERE sig.board_cols = $cols
                AND sig.board_rows = $rows
                AND ABS(sig.total_pieces - $total) <= 5
                WITH sig, 
                     size([p IN sig.required_pieces WHERE p IN $detected]) as matched,
                     size(sig.required_pieces) as required
                WHERE matched >= (required * 0.7)
                MATCH (g:LudiiGame {name: sig.game_name})
                RETURN sig.game_name as game, 
                       (matched * 100.0 / required) as match_ratio,
                       g.official_description as desc,
                       g.official_rules as rules
                ORDER BY match_ratio DESC
                LIMIT 1
            """,
            cols=yolo_result.board_cols,
            rows=yolo_result.board_rows,
            total=yolo_result.total_pieces,
            detected=detected_piece_types
            ).single()
            
            if game:
                return {
                    "status": "partial_match",
                    "identified_game": game['game'],
                    "confidence": game['match_ratio'] / 100,
                    "yolo_detection": {
                        "board": [yolo_result.board_cols, yolo_result.board_rows],
                        "total_pieces": yolo_result.total_pieces,
                        "piece_types": detected_piece_types
                    }
                }
            
            raise HTTPException(404, "No matching game found")
    
    except Exception as e:
        raise HTTPException(500, str(e))