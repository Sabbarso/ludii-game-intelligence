from ultralytics import YOLO
import cv2

def detect_game(image_path):
    # LOAD MODEL
    model = YOLO("phase2_vision/models/chess_ludii_best.pt")  # Ton modèle
    
    # RUN DETECTION
    results = model(image_path)
    
    # EXTRACT DETECTIONS
    detections = results[0]
    boxes = detections.boxes
    
    board_cols = 8
    board_rows = 8
    total_pieces = len(boxes)
    confidence = detections.probs.max() if hasattr(detections, 'probs') else 0.95
    
    pieces_by_type = {}
    
    for box in boxes:
        cls = int(box.cls)
        conf = float(box.conf)
        
        # Map class ID to piece type (adapter selon ton modèle)
        class_names = {
            0: "pawn",
            1: "rook",
            2: "knight",
            3: "bishop",
            4: "queen",
            5: "king"
        }
        
        piece_type = class_names.get(cls, "unknown")
        
        # Détecter couleur (blanc ou noir basé sur position Y ou autre)
        color = "white" if box.xyxy[0][1] > 256 else "black"
        
        piece_name = f"{color}_{piece_type}"
        pieces_by_type[piece_name] = pieces_by_type.get(piece_name, 0) + 1
    
    # PRINT RESULTS
    print("=" * 70)
    print(f"Plateau estime         : {board_cols} colonnes x {board_rows} rangees")
    print(f"Total pieces detectees : {total_pieces}")
    print(f"Confiance moyenne      : {confidence:.3f}")
    print("Detail complet (par couleur) :")
    
    for piece, count in pieces_by_type.items():
        print(f"  {piece:20} : {count}")
    
    print("=" * 70)