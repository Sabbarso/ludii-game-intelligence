import numpy as np
import trimesh
import os

def reconstruct_from_dimensions(cols, rows, shape="square", piece_types=None):
    """Reconstruit un plateau 3D simple et l'exporte en GLB"""
    if piece_types is None:
        piece_types = ["pawn"]
    
    scene = trimesh.Scene()
    cell_size = 1.0
    w = cols * cell_size
    h = rows * cell_size
    
    # Plateau
    board = trimesh.creation.box(extents=[w, h, 0.2])
    board.visual.vertex_colors = np.tile([0.55, 0.35, 0.15], (len(board.vertices), 1))
    scene.add_geometry(board, node_name="board")
    
    # Grille verticale
    for i in range(cols + 1):
        x = -w/2 + i * cell_size
        line = trimesh.creation.cylinder(radius=0.015, height=h)
        line.apply_translation([x, 0, 0.11])
        line.visual.vertex_colors = np.tile([0.3, 0.2, 0.1], (len(line.vertices), 1))
        scene.add_geometry(line, node_name=f"vline_{i}")
    
    # Grille horizontale (rotation via matrice)
    for j in range(rows + 1):
        y = -h/2 + j * cell_size
        line = trimesh.creation.cylinder(radius=0.015, height=w)
        # Rotation de 90° autour de X
        rotation = trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])
        line.apply_transform(rotation)
        line.apply_translation([0, y, 0.11])
        line.visual.vertex_colors = np.tile([0.3, 0.2, 0.1], (len(line.vertices), 1))
        scene.add_geometry(line, node_name=f"hline_{j}")
    
    # Pièces
    colors = {
        "king": [0.9, 0.75, 0.2], "queen": [0.8, 0.8, 0.85],
        "rook": [0.6, 0.3, 0.1], "bishop": [0.8, 0.2, 0.2],
        "knight": [0.2, 0.6, 0.2], "pawn": [0.9, 0.9, 0.75],
        "marker": [0.5, 0.5, 0.5], "disc": [0.7, 0.7, 0.7]
    }
    
    for i in range(min(2, rows)):
        for j in range(cols):
            ptype = piece_types[j % len(piece_types)] if piece_types else "pawn"
            color = colors.get(ptype, [0.8, 0.8, 0.8])
            
            piece = trimesh.creation.cylinder(radius=0.25, height=0.4, sections=12)
            piece.visual.vertex_colors = np.tile(color, (len(piece.vertices), 1))
            
            x = -w/2 + (j + 0.5) * cell_size
            y = -h/2 + (i + 0.5) * cell_size
            piece.apply_translation([x, y, 0.4])
            scene.add_geometry(piece, node_name=f"piece_{i}_{j}")
    
    filepath = "reconstructed.glb"
    scene.export(filepath)
    return filepath