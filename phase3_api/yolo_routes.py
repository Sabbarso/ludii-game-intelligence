from fastapi import APIRouter, HTTPException
from phase4_neo4j.pipeline import Neo4jPipeline
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["yolo"])

class YOLODetection(BaseModel):
    yolo_class: str
    detected_pieces: List[str] = []
    board_dimensions: Optional[List[int]] = None
    confidence: float = 0.0

@router.post("/detect_from_yolo")
async def detect_game(detection: YOLODetection):
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            result = session.run("""
                MATCH (m:YOLOMapping {detected_class: $yolo})
                MATCH (g:LudiiGame {name: m.game_name})
                OPTIONAL MATCH (g)-[:SIMILAR_TO]->(similar)
                RETURN m.game_name as game, m.pieces_expected as pieces, collect(similar.name) as similar
            """, yolo=detection.yolo_class).single()
            
            if not result:
                raise HTTPException(404, "Game not found")
            
            return {
                "identified_game": result['game'],
                "detected_pieces": detection.detected_pieces,
                "expected_pieces": result['pieces'],
                "confidence": detection.confidence,
                "similar_games": [s for s in result['similar'] if s]
            }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/yolo/classes")
async def get_classes():
    pipeline = Neo4jPipeline()
    with pipeline.driver.session() as session:
        result = session.run("MATCH (m:YOLOMapping) RETURN m.detected_class as c, m.game_name as g").data()
        return {"classes": result}