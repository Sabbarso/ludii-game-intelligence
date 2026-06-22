from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from phase4_neo4j.pipeline import Neo4jPipeline
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import subprocess
import re
from phase2_vision.board_3d import reconstruct_from_dimensions
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1", tags=["yolo"])

class YOLODetectionResult(BaseModel):
    board_cols: int
    board_rows: int
    total_pieces: int
    pieces: List[Dict]
    confidence: float

class PartialBoardRequest(BaseModel):
    board_cols: Optional[int] = None
    board_rows: Optional[int] = None
    total_pieces: Optional[int] = None
    pieces: List[Dict] = []
    confidence: float = 0.5
    tolerance: int = 1

def build_response(game_record, yolo_result, detected_types, partial=False):
    expected_total = game_record.get("expected_total")
    match_ratio = 1.0
    if expected_total and yolo_result.total_pieces:
        match_ratio = min(1.0, yolo_result.total_pieces / expected_total)
    confidence = 0.95 if not partial else min(0.85, match_ratio * 0.9)
    return {
        "status": "success" if not partial else "partial_match",
        "identified_game": game_record["game"],
        "confidence": confidence,
        "yolo_detection": {
            "board": [yolo_result.board_cols, yolo_result.board_rows],
            "total_pieces": yolo_result.total_pieces,
            "piece_types": detected_types
        },
        "game_details": {
            "description": game_record["desc"],
            "expected_pieces": expected_total,
            "expected_piece_types": game_record.get("pieces", [])
        }
    }

@router.post("/detect_game_from_image")
async def detect_game_from_image(file: UploadFile = File(...)):
    """Upload image → YOLO détecte → Identifie jeu"""
    try:
        temp_dir = "temp_yolo_images"
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = f"{temp_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        try:
            result = subprocess.run(
                f"python phase2_vision/detect.py {file_path}",
                capture_output=True,
                text=True,
                timeout=30
            )
            yolo_output = result.stdout
        except:
            raise HTTPException(500, "YOLO detection failed")
        
        board_cols = 8
        board_rows = 8
        total_pieces = 32
        pieces = []
        confidence = 0.0
        
        lines = yolo_output.split("\n")
        
        for line in lines:
            if "Total pieces detectees" in line:
                try:
                    total_pieces = int(line.split(":")[-1].strip())
                except:
                    pass
            if "Confiance moyenne" in line:
                try:
                    confidence = float(line.split(":")[-1].strip())
                except:
                    pass
            if "Plateau estime" in line:
                try:
                    match = re.search(r'(\d+).*x\s*(\d+)', line)
                    if match:
                        board_cols = int(match.group(1))
                        board_rows = int(match.group(2))
                except:
                    pass
        
        in_detail = False
        for line in lines:
            if "Detail complet (par couleur)" in line:
                in_detail = True
                continue
            if in_detail and ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    piece_color_type = parts[0].strip()
                    try:
                        count = int(parts[1].strip())
                        if "_" in piece_color_type:
                            color, piece_type = piece_color_type.rsplit("_", 1)
                            for _ in range(count):
                                pieces.append({"type": piece_type, "color": color, "x": 0, "y": 0})
                    except:
                        pass
        
        if not pieces:
            pieces = [{"type": "rook", "color": "white", "x": 0, "y": 0}]
        
        yolo_result = YOLODetectionResult(
            board_cols=board_cols, board_rows=board_rows,
            total_pieces=total_pieces, pieces=pieces, confidence=confidence
        )
        
        return await identify_game(yolo_result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/identify_game_from_yolo")
async def identify_game(yolo_result: YOLODetectionResult):
    """Identification exacte (dimensions + pièces)"""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            detected_types = list(set(p.get("type", "").lower() for p in yolo_result.pieces if p.get("type")))
            cols = yolo_result.board_cols
            rows = yolo_result.board_rows
            total = yolo_result.total_pieces

            query = """
                MATCH (rs:Ruleset)-[:HAS_YOLO_SIGNATURE]->(sig:YOLOSignature)
                WHERE sig.board_cols = $cols AND sig.board_rows = $rows
                MATCH (rs)<-[:HAS_RULESET]-(g:Game)
                WITH g, sig,
                     CASE
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND sig.total_pieces = $total THEN 3
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND abs(sig.total_pieces - $total) <= 5 THEN 2
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NULL THEN 0
                       ELSE 1
                     END AS pieceScore,
                     CASE
                       WHEN sig.required_pieces IS NOT NULL AND size(sig.required_pieces) > 0 AND size($detected) > 0
                       THEN toFloat(size([p IN sig.required_pieces WHERE p IN $detected])) / size(sig.required_pieces)
                       ELSE 0
                     END AS typeRatio
                WHERE pieceScore > 0 OR typeRatio > 0
                RETURN g.name AS game, g.description AS desc,
                       sig.required_pieces AS pieces, sig.total_pieces AS expected_total,
                       sig.board_cols AS actual_cols, sig.board_rows AS actual_rows,
                       (pieceScore + typeRatio) AS relevance
                ORDER BY relevance DESC, pieceScore DESC, typeRatio DESC
                LIMIT 1
            """
            result = session.run(query, cols=cols, rows=rows, total=total, detected=detected_types).data()
            
            if result:
                game = result[0]
                partial = game.get("relevance", 0) < 3.0
                response = build_response(game, yolo_result, detected_types, partial=partial)
                response["actual_dimensions"] = [game["actual_cols"], game["actual_rows"]]
                response["relevance_score"] = game["relevance"]
                return response
            else:
                raise HTTPException(404, "No matching game found in database")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/identify_partial_board")
async def identify_partial_board(request: PartialBoardRequest):
    """Identification avec tolérance pour plateaux endommagés"""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            detected_types = list(set(p.get("type", "").lower() for p in request.pieces if p.get("type")))
            cols = request.board_cols
            rows = request.board_rows
            total = request.total_pieces
            tolerance = request.tolerance

            query = """
                MATCH (rs:Ruleset)-[:HAS_YOLO_SIGNATURE]->(sig:YOLOSignature)
                WHERE ($cols IS NULL OR abs(sig.board_cols - $cols) <= $tolerance)
                  AND ($rows IS NULL OR abs(sig.board_rows - $rows) <= $tolerance)
                MATCH (rs)<-[:HAS_RULESET]-(g:Game)
                WITH g, sig,
                     CASE
                       WHEN $cols IS NOT NULL AND $rows IS NOT NULL
                       THEN (4 - abs(sig.board_cols - $cols) - abs(sig.board_rows - $rows)) / 2.0
                       WHEN $cols IS NOT NULL
                       THEN (2 - abs(sig.board_cols - $cols)) / 2.0
                       WHEN $rows IS NOT NULL
                       THEN (2 - abs(sig.board_rows - $rows)) / 2.0
                       ELSE 1.0
                     END AS dimScore,
                     CASE
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND sig.total_pieces = $total THEN 3
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND abs(sig.total_pieces - $total) <= 5 THEN 2
                       WHEN $total IS NOT NULL AND sig.total_pieces IS NULL THEN 0
                       ELSE 1
                     END AS pieceScore,
                     CASE
                       WHEN sig.required_pieces IS NOT NULL AND size(sig.required_pieces) > 0 AND size($detected) > 0
                       THEN toFloat(size([p IN sig.required_pieces WHERE p IN $detected])) / size(sig.required_pieces)
                       ELSE 0
                     END AS typeRatio,
                     CASE WHEN sig.total_pieces IS NOT NULL THEN 0.5 ELSE 0 END AS completenessBonus
                WHERE pieceScore > 0 OR typeRatio > 0
                RETURN g.name AS game, g.description AS desc,
                       sig.required_pieces AS pieces, sig.total_pieces AS expected_total,
                       sig.board_cols AS actual_cols, sig.board_rows AS actual_rows,
                       (dimScore + pieceScore + typeRatio + completenessBonus) AS relevance
                ORDER BY relevance DESC, pieceScore DESC, typeRatio DESC
                LIMIT 5
            """
            results = session.run(query, cols=cols, rows=rows, total=total, detected=detected_types, tolerance=tolerance).data()
            
            if results:
                games = []
                for game in results:
                    games.append({
                        "game": game["game"],
                        "relevance": game["relevance"],
                        "actual_dimensions": [game["actual_cols"], game["actual_rows"]],
                        "expected_pieces": game["expected_total"],
                        "description": game["desc"],
                        "expected_piece_types": game["pieces"]
                    })
                
                max_relevance = max(g["relevance"] for g in games) if games else 0
                
                return {
                    "status": "success",
                    "candidates": games,
                    "best_match": games[0]["game"] if games else None,
                    "confidence": min(0.95, max_relevance / 5.0) if max_relevance > 0 else 0.5,
                    "yolo_detection": {
                        "board": [cols, rows],
                        "total_pieces": total,
                        "piece_types": detected_types,
                        "tolerance_used": tolerance
                    }
                }
            
            raise HTTPException(404, "No matching game found in database")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/similar_games")
async def similar_games(
    game_name: str = Query(..., description="Nom du jeu identifié"),
    limit: int = Query(5, description="Nombre de jeux similaires à retourner")
):
    """Retourne les jeux similaires par région, période ou catégorie."""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            query = """
                MATCH (g:Game)
                WHERE toLower(g.name) = toLower($name)
                OPTIONAL MATCH (g)-[:FROM_REGION]->(r:Region)<-[:FROM_REGION]-(gRegion:Game)
                WHERE gRegion.name <> g.name
                WITH g, collect(DISTINCT {game: gRegion.name, type: 'Région', value: r.name, score: 3}) AS regionGames
                OPTIONAL MATCH (g)-[:FROM_PERIOD]->(p:Period)<-[:FROM_PERIOD]-(gPeriod:Game)
                WHERE gPeriod.name <> g.name
                WITH g, regionGames, collect(DISTINCT {game: gPeriod.name, type: 'Période', value: p.name, score: 2}) AS periodGames
                OPTIONAL MATCH (g)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(gCat:Game)
                WHERE gCat.name <> g.name
                WITH g, regionGames, periodGames, collect(DISTINCT {game: gCat.name, type: 'Catégorie', value: c.name, score: 1}) AS catGames
                WITH regionGames + periodGames + catGames AS allSimilar
                UNWIND allSimilar AS sim
                WITH sim.game AS game, sim.type AS type, sim.value AS value, sim.score AS score
                ORDER BY score DESC, game
                RETURN game, collect(DISTINCT {type: type, value: value})[0] AS similarity, score
                ORDER BY score DESC, game
                LIMIT $limit
            """
            results = session.run(query, name=game_name, limit=limit).data()
            
            if results:
                return {
                    "status": "success",
                    "game": game_name,
                    "similar_games": [
                        {
                            "game": r["game"],
                            "similarity_type": r["similarity"]["type"],
                            "shared": r["similarity"]["value"],
                            "score": r["score"]
                        } for r in results
                    ]
                }
            
            return {"status": "success", "game": game_name, "similar_games": [], "message": "Aucun jeu similaire trouvé"}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/similar_games_by_type")
async def similar_games_by_type(
    game_name: str = Query(...),
    similarity_type: str = Query("all"),
    limit: int = Query(5)
):
    """Retourne les jeux similaires filtrés par type."""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            query_region = """MATCH (g:Game) WHERE toLower(g.name) = toLower($name) MATCH (g)-[:FROM_REGION]->(r:Region)<-[:FROM_REGION]-(g2:Game) WHERE g2.name <> g.name RETURN g2.name AS game, 'Région' AS type, r.name AS value LIMIT $limit"""
            query_period = """MATCH (g:Game) WHERE toLower(g.name) = toLower($name) MATCH (g)-[:FROM_PERIOD]->(p:Period)<-[:FROM_PERIOD]-(g2:Game) WHERE g2.name <> g.name RETURN g2.name AS game, 'Période' AS type, p.name AS value LIMIT $limit"""
            query_category = """MATCH (g:Game) WHERE toLower(g.name) = toLower($name) MATCH (g)-[:IN_CATEGORY]->(c:Category)<-[:IN_CATEGORY]-(g2:Game) WHERE g2.name <> g.name RETURN g2.name AS game, 'Catégorie' AS type, c.name AS value LIMIT $limit"""
            
            if similarity_type == "region":
                results = session.run(query_region, name=game_name, limit=limit).data()
            elif similarity_type == "period":
                results = session.run(query_period, name=game_name, limit=limit).data()
            elif similarity_type == "category":
                results = session.run(query_category, name=game_name, limit=limit).data()
            else:
                r1 = session.run(query_region, name=game_name, limit=2).data()
                r2 = session.run(query_period, name=game_name, limit=2).data()
                r3 = session.run(query_category, name=game_name, limit=2).data()
                results = r1 + r2 + r3
            
            if results:
                return {
                    "status": "success", "game": game_name, "similarity_type": similarity_type,
                    "similar_games": [{"game": r["game"], "type": r["type"], "shared": r["value"]} for r in results]
                }
            return {"status": "success", "game": game_name, "similar_games": []}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/reconstruct_game")
async def reconstruct_game(request: PartialBoardRequest):
    """Reconstruction automatique d'un jeu à partir d'un plateau partiel."""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            detected_types = list(set(p.get("type", "").lower() for p in request.pieces if p.get("type")))
            cols = request.board_cols
            rows = request.board_rows
            total = request.total_pieces
            tolerance = request.tolerance

            query = """
                MATCH (rs:Ruleset)-[:HAS_YOLO_SIGNATURE]->(sig:YOLOSignature)
                WHERE ($cols IS NULL OR abs(sig.board_cols - $cols) <= $tolerance)
                  AND ($rows IS NULL OR abs(sig.board_rows - $rows) <= $tolerance)
                MATCH (rs)<-[:HAS_RULESET]-(g:Game)
                OPTIONAL MATCH (g)-[:FROM_REGION]->(r:Region)
                OPTIONAL MATCH (g)-[:FROM_PERIOD]->(p:Period)
                WITH g, sig, r, p,
                     CASE WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND sig.total_pieces = $total THEN 3
                          WHEN $total IS NOT NULL AND sig.total_pieces IS NOT NULL AND abs(sig.total_pieces - $total) <= 5 THEN 2 ELSE 0 END AS pieceScore,
                     CASE WHEN sig.required_pieces IS NOT NULL AND size(sig.required_pieces) > 0 AND size($detected) > 0
                          THEN toFloat(size([x IN sig.required_pieces WHERE x IN $detected])) / size(sig.required_pieces) ELSE 0 END AS typeRatio
                WHERE pieceScore > 0 OR typeRatio > 0
                RETURN g.name AS game, g.description AS desc, g.ludCode AS ludCode,
                       g.origin AS origin, sig.board_cols AS actual_cols, sig.board_rows AS actual_rows,
                       sig.required_pieces AS pieceTypes, sig.total_pieces AS expectedPieces,
                       collect(DISTINCT r.name) AS regions, collect(DISTINCT p.name) AS periods,
                       (pieceScore + typeRatio) AS relevance
                ORDER BY relevance DESC LIMIT 1
            """
            result = session.run(query, cols=cols, rows=rows, total=total, detected=detected_types, tolerance=tolerance).data()
            
            if not result:
                raise HTTPException(404, "Aucun jeu identifié")
            
            game = result[0]
            rules_text = extract_rules_from_lud(game.get("ludCode", ""))
            board_layout = generate_board_layout(game["actual_cols"], game["actual_rows"], game.get("pieceTypes", []), game.get("expectedPieces"))
            
            return {
                "status": "success", "identified_game": game["game"],
                "confidence": min(0.95, game["relevance"] / 3.0),
                "reconstruction": {
                    "board_dimensions": {"cols": game["actual_cols"], "rows": game["actual_rows"], "total_cells": game["actual_cols"] * game["actual_rows"]},
                    "pieces": {"types": game.get("pieceTypes", []), "total_expected": game.get("expectedPieces"), "detected": len(request.pieces), "missing": (game.get("expectedPieces") or 0) - len(request.pieces) if game.get("expectedPieces") else "inconnu"},
                    "board_layout": board_layout,
                    "rules": {"summary": game["desc"], "detailed_rules": rules_text[:2000] if rules_text else "Règles non disponibles"},
                    "historical_context": {"regions": game.get("regions", []), "periods": game.get("periods", []), "origin": game.get("origin")}
                },
                "original_detection": {"board": [cols, rows], "pieces_found": detected_types, "tolerance_used": tolerance}
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

def extract_rules_from_lud(lud_code: str) -> str:
    if not lud_code: return ""
    rules = []
    descriptions = re.findall(r'"([^"]*)"', lud_code)
    for desc in descriptions:
        if len(desc) > 20 and not desc.startswith('{') and not desc.startswith('('):
            rules.append(desc.strip())
            if len(rules) >= 5: break
    if "Checkmate" in lud_code: rules.append("Objectif : Mettre le roi adverse en échec et mat")
    if "Stalemate" in lud_code: rules.append("Stalemate possible")
    if "capture" in lud_code.lower() or "remove" in lud_code.lower(): rules.append("Capture de pièces")
    if "Promotion" in lud_code: rules.append("Promotion des pions")
    if "Castling" in lud_code: rules.append("Roque (Castling)")
    return "\n".join(rules) if rules else "Règles disponibles dans le code source"

def generate_board_layout(cols: int, rows: int, piece_types: list, total_pieces: int) -> dict:
    layout = {"type": "grid", "dimensions": f"{cols}×{rows}", "total_cells": cols * rows, "ascii_representation": generate_ascii_board(cols, rows, piece_types)}
    if cols == 8 and rows == 8 and "pawn" in piece_types:
        layout["suggested_setup"] = {"white_pieces": "♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜ + 8 ♟", "black_pieces": "♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜ + 8 ♟"}
    return layout

def generate_ascii_board(cols: int, rows: int, piece_types: list) -> str:
    if cols > 20 or rows > 20: return f"[Plateau {cols}×{rows}]"
    symbols = {"king":"♚","queen":"♛","rook":"♜","bishop":"♝","knight":"♞","pawn":"♟"}
    display = [symbols.get(p.lower(), "●") for p in piece_types] if piece_types else ["●"]
    lines = ["+" + "---+" * cols]
    for row in range(rows):
        lines.append("|" + "   |" * cols)
        if row == 0 and display:
            lines.append("|" + "".join([f" {display[c % len(display)]} |" for c in range(cols)]))
        elif row == rows - 1 and display:
            lines.append("|" + "".join([f" {display[(c+1) % len(display)]} |" for c in range(cols)]))
        else:
            lines.append("|" + "   |" * cols)
        lines.append("+" + "---+" * cols)
    return "\n".join(lines)

@router.post("/reconstruct_3d")
async def reconstruct_3d(request: PartialBoardRequest):
    """Reconstruction 3D - match Neo4j + 3D fidèle au jeu trouvé"""
    try:
        pipeline = Neo4jPipeline()
        with pipeline.driver.session() as session:
            # Chercher le jeu qui correspond EXACTEMENT aux dimensions (tolérance 0)
            query = """
                MATCH (rs:Ruleset)-[:HAS_YOLO_SIGNATURE]->(sig:YOLOSignature)
                WHERE sig.board_cols = $cols AND sig.board_rows = $rows
                MATCH (rs)<-[:HAS_RULESET]-(g:Game)
                RETURN g.name AS game, g.description AS desc,
                       sig.board_cols AS cols, sig.board_rows AS rows,
                       sig.board_shape AS shape, sig.required_pieces AS pieces
                ORDER BY 
                  CASE WHEN sig.total_pieces = $total THEN 0 ELSE 1 END,
                  size(sig.required_pieces) DESC
                LIMIT 1
            """
            result = session.run(query, 
                cols=request.board_cols, rows=request.board_rows,
                total=request.total_pieces or 32
            ).data()
            
            if result:
                game = result[0]
                cols = game["cols"] or request.board_cols or 8
                rows = game["rows"] or request.board_rows or 8
                game_name = game["game"]
                description = game.get("desc", "")
                pieces = game.get("pieces", []) or ["pawn"]
            else:
                # Fallback si aucun match exact
                cols = request.board_cols or 8
                rows = request.board_rows or 8
                game_name = f"Plateau {cols}×{rows}"
                description = ""
                pieces = ["pawn"]
            
            # Reconstruction 3D avec les bonnes dimensions et pièces
            filepath = reconstruct_from_dimensions(cols, rows, "square", pieces)
            
            return {
                "status": "success",
                "game": game_name,
                "description": description,
                "dimensions": [cols, rows],
                "pieces": pieces,
                "model_3d": f"/api/v1/view_3d/{os.path.basename(filepath)}"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
        raise HTTPException(500, str(e))

@router.get("/view_3d/{filename}")
async def view_3d(filename: str):
    """Sert le fichier 3D"""
    filepath = filename
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="model/gltf-binary")
    alt = os.path.join(os.getcwd(), filename)
    if os.path.exists(alt):
        return FileResponse(alt, media_type="model/gltf-binary")
    raise HTTPException(404, "Fichier 3D non trouvé")