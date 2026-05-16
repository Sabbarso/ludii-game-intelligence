"""
GNN Routes - Endpoints pour recommandations basées sur embeddings
"""

from fastapi import APIRouter, HTTPException
import torch
import numpy as np
import json
import os
from typing import List, Dict

router = APIRouter(prefix="/api/v1", tags=["gnn"])

# ========== CONFIG ==========
MODEL_PATH = "./models/gnn_model.pt"
EMBEDDINGS_PATH = "./models/embeddings.npy"
MAPPING_PATH = "./models/node_mapping.json"

# Load embeddings and mapping (cache)
embeddings = None
node_mapping = None
reverse_mapping = None

def load_gnn_data():
    """Charge les données GNN (embeddings et mapping)"""
    global embeddings, node_mapping, reverse_mapping
    
    try:
        if embeddings is None:
            embeddings = np.load(EMBEDDINGS_PATH)
            print(f"✅ Embeddings loaded: {embeddings.shape}")
        
        if node_mapping is None:
            with open(MAPPING_PATH, 'r') as f:
                node_mapping = json.load(f)
            reverse_mapping = {v: k for k, v in node_mapping.items()}
            print(f"✅ Node mapping loaded: {len(node_mapping)} games")
    
    except FileNotFoundError as e:
        raise Exception(f"GNN models not found: {e}. Run train_gnn.py first")

# ========== ENDPOINT 1: Game Similarity (GNN-based) ==========
@router.post("/gnn/similar_games")
async def gnn_similar_games(game_name: str, top_k: int = 10):
    """
    Trouve les jeux les plus similaires en utilisant les embeddings GNN
    
    Basé sur cosine similarity entre embeddings
    """
    try:
        load_gnn_data()
        
        # Vérifier que le jeu existe
        if game_name not in node_mapping:
            raise HTTPException(
                status_code=404, 
                detail=f"Game '{game_name}' not found in GNN model"
            )
        
        game_idx = node_mapping[game_name]
        game_embedding = embeddings[game_idx]
        
        # Calculer cosine similarity avec tous les autres jeux
        similarities = []
        for idx, embedding in enumerate(embeddings):
            if idx == game_idx:
                continue
            
            # Cosine similarity
            cos_sim = np.dot(game_embedding, embedding) / (
                np.linalg.norm(game_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            
            game_name_result = reverse_mapping[idx]
            similarities.append({
                "name": game_name_result,
                "similarity": float(cos_sim)
            })
        
        # Sort par similarity et retourner top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        top_games = similarities[:top_k]
        
        return {
            "query_game": game_name,
            "similar_games": top_games,
            "count": len(top_games)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT 2: Find Community ==========
@router.get("/gnn/community/{game_name}")
async def gnn_community(game_name: str, threshold: float = 0.5):
    """
    Trouve la communauté de jeux similaires au-dessus d'un threshold
    """
    try:
        load_gnn_data()
        
        if game_name not in node_mapping:
            raise HTTPException(status_code=404, detail=f"Game not found")
        
        game_idx = node_mapping[game_name]
        game_embedding = embeddings[game_idx]
        
        community = []
        for idx, embedding in enumerate(embeddings):
            if idx == game_idx:
                continue
            
            cos_sim = np.dot(game_embedding, embedding) / (
                np.linalg.norm(game_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            
            if cos_sim >= threshold:
                community.append({
                    "name": reverse_mapping[idx],
                    "similarity": float(cos_sim)
                })
        
        community.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            "game": game_name,
            "community_size": len(community),
            "threshold": threshold,
            "members": community
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT 3: Embedding Visualization ==========
@router.get("/gnn/embedding/{game_name}")
async def get_embedding(game_name: str):
    """
    Récupère l'embedding GNN d'un jeu (pour visualisation)
    """
    try:
        load_gnn_data()
        
        if game_name not in node_mapping:
            raise HTTPException(status_code=404, detail=f"Game not found")
        
        game_idx = node_mapping[game_name]
        embedding = embeddings[game_idx]
        
        return {
            "game": game_name,
            "embedding_dim": len(embedding),
            "embedding": embedding.tolist()  # Convertir en list pour JSON
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT 4: Clustering Games ==========
@router.post("/gnn/cluster_games")
async def cluster_games(games: List[str], method: str = "kmeans"):
    """
    Cluster plusieurs jeux basé sur leurs embeddings GNN
    
    Retourne la matrice de similarité et groupes
    """
    try:
        load_gnn_data()
        from sklearn.cluster import KMeans
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Récupérer les embeddings
        game_embeddings = []
        game_names = []
        
        for game in games:
            if game not in node_mapping:
                continue
            game_idx = node_mapping[game]
            game_embeddings.append(embeddings[game_idx])
            game_names.append(game)
        
        if not game_embeddings:
            raise HTTPException(status_code=404, detail="No games found")
        
        X = np.array(game_embeddings)
        
        # Compute similarity matrix
        sim_matrix = cosine_similarity(X).tolist()
        
        # Clustering
        if len(game_names) >= 2:
            n_clusters = min(3, len(game_names))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(X).tolist()
        else:
            clusters = [0] * len(game_names)
        
        return {
            "games": game_names,
            "num_clusters": len(set(clusters)),
            "clusters": clusters,
            "similarity_matrix": sim_matrix
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== ENDPOINT 5: Recommend Next Game ==========
@router.post("/gnn/recommend_next")
async def recommend_next(current_games: List[str], top_k: int = 5):
    """
    Recommande le prochain jeu basé sur les jeux actuels
    
    Utilise la moyenne des embeddings pour trouver les jeux les plus proches
    """
    try:
        load_gnn_data()
        
        # Récupérer les embeddings des jeux actuels
        current_embeddings = []
        for game in current_games:
            if game in node_mapping:
                idx = node_mapping[game]
                current_embeddings.append(embeddings[idx])
        
        if not current_embeddings:
            raise HTTPException(status_code=404, detail="No games found")
        
        # Moyenne des embeddings
        avg_embedding = np.mean(current_embeddings, axis=0)
        
        # Trouver les jeux les plus proches
        similarities = []
        for idx, embedding in enumerate(embeddings):
            game_name = reverse_mapping[idx]
            
            # Skip si jeu est déjà joué
            if game_name in current_games:
                continue
            
            cos_sim = np.dot(avg_embedding, embedding) / (
                np.linalg.norm(avg_embedding) * np.linalg.norm(embedding) + 1e-8
            )
            
            similarities.append({
                "name": game_name,
                "similarity": float(cos_sim)
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            "current_games": current_games,
            "recommendations": similarities[:top_k],
            "recommendation_count": len(similarities[:top_k])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))