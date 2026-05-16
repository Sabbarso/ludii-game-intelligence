"""
GNN Training - Entraîne un Graph Neural Network sur les données Neo4j
Utilise PyTorch Geometric pour apprendre des embeddings de jeux similaires
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
from neo4j import GraphDatabase
import json
import os
from typing import Dict, List, Tuple
import numpy as np

print("=" * 80)
print("🧠 GNN TRAINING - LUDII GAMES")
print("=" * 80)

# ========== CONFIG ==========
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "salma1234")
MODEL_PATH = "./models/gnn_model.pt"
MAPPING_PATH = "./models/node_mapping.json"
EMBEDDING_DIM = 64

# ========== STEP 1: FETCH DATA FROM NEO4J ==========
print("\n[1/5] Fetching data from Neo4j...")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Compter les jeux
        count_result = session.run("MATCH (g:LudiiGame) RETURN COUNT(g) as count").single()
        num_games = count_result['count']
        print(f"   ✅ Total games: {num_games}")
        
        # Récupérer tous les jeux
        games = session.run("""
            MATCH (g:LudiiGame)
            RETURN g.name as name, g.complexity as complexity, 
                   g.players_max as players, g.year as year
            ORDER BY g.name
        """).data()
        
        print(f"   ✅ Games loaded: {len(games)}")
        
        # Récupérer les edges (HAS_RULE, HAS_PIECE, etc.)
        edges = session.run("""
            MATCH (g1:LudiiGame)-[r]-(g2:LudiiGame)
            RETURN g1.name as source, g2.name as target, type(r) as relation_type
            LIMIT 5000
        """).data()
        
        print(f"   ✅ Game-to-game edges: {len(edges)}")
        
        # Récupérer edges vers Rule, Piece, Board
        rule_edges = session.run("""
            MATCH (g:LudiiGame)-[:HAS_RULE]->(r:Rule)
            RETURN g.name as game, r.id as rule_id
        """).data()
        
        piece_edges = session.run("""
            MATCH (g:LudiiGame)-[:HAS_PIECE]->(p:Piece)
            RETURN g.name as game, p.id as piece_id
        """).data()
        
        print(f"   ✅ HAS_RULE edges: {len(rule_edges)}")
        print(f"   ✅ HAS_PIECE edges: {len(piece_edges)}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ========== STEP 2: CREATE NODE MAPPING ==========
print("\n[2/5] Creating node mapping...")

try:
    # Map game names to indices
    node_mapping = {}
    node_features = []
    
    for idx, game in enumerate(games):
        node_mapping[game['name']] = idx
        
        # Feature engineering: [complexity, players, year_normalized, community_size]
        complexity = game['complexity'] if game['complexity'] else 5
        players = game['players'] if game['players'] else 2
        year = (game['year'] if game['year'] else 1000) / 2500.0  # normalize
        
        # Placeholder pour la taille communauté (sera calculée avec edges)
        community_size = 0
        
        features = [complexity / 10.0, players / 4.0, year, community_size]
        node_features.append(features)
    
    node_features = np.array(node_features, dtype=np.float32)
    
    print(f"   ✅ {len(node_mapping)} nodes mapped")
    print(f"   ✅ Features shape: {node_features.shape}")
    
    # Save mapping for later use
    os.makedirs("./models", exist_ok=True)
    with open(MAPPING_PATH, 'w') as f:
        json.dump(node_mapping, f, indent=2)
    print(f"   ✅ Mapping saved to {MAPPING_PATH}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ========== STEP 3: BUILD GRAPH ==========
print("\n[3/5] Building PyTorch Geometric graph...")

try:
    edge_list = []
    edge_weight = []
    
    # Ajouter les edges entre jeux
    for edge in edges:
        source_idx = node_mapping.get(edge['source'])
        target_idx = node_mapping.get(edge['target'])
        
        if source_idx is not None and target_idx is not None:
            # Bidirectional edges
            edge_list.append([source_idx, target_idx])
            edge_list.append([target_idx, source_idx])
            edge_weight.append(1.0)
            edge_weight.append(1.0)
    
    # Ajouter edges HAS_RULE/HAS_PIECE comme auto-loops avec poids
    for rule_edge in rule_edges:
        game_idx = node_mapping.get(rule_edge['game'])
        if game_idx is not None:
            # Auto-loop avec petit poids
            edge_list.append([game_idx, game_idx])
            edge_weight.append(0.1)
    
    edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    
    print(f"   ✅ Edges: {edge_index.shape}")
    print(f"   ✅ Edge density: {edge_index.shape[1] / (num_games ** 2):.4f}")
    
    # Create features tensor
    x = torch.tensor(node_features, dtype=torch.float32)
    
    # Pad features to 64 dimensions for GNN input
    if x.shape[1] < EMBEDDING_DIM:
        padding = torch.zeros(x.shape[0], EMBEDDING_DIM - x.shape[1])
        x = torch.cat([x, padding], dim=1)
    
    print(f"   ✅ Node features: {x.shape}")
    
    # Create PyTorch Geometric Data object
    data = Data(x=x, edge_index=edge_index)
    
    print(f"   ✅ Graph created: {data}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ========== STEP 4: DEFINE GNN MODEL ==========
print("\n[4/5] Defining GNN model...")

class GNN(torch.nn.Module):
    def __init__(self, input_dim=64, hidden_dim=64, output_dim=32, num_layers=3):
        super(GNN, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        
        # GCN layers
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)
        self.conv3 = GCNConv(output_dim, output_dim)
        
        # Batch normalization
        self.bn1 = torch.nn.BatchNorm1d(hidden_dim)
        self.bn2 = torch.nn.BatchNorm1d(output_dim)
        
    def forward(self, x, edge_index):
        # Layer 1
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        
        # Layer 2
        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.relu(x)
        x = F.dropout(x, p=0.2, training=self.training)
        
        # Layer 3
        x = self.conv3(x, edge_index)
        
        return x

try:
    model = GNN(input_dim=EMBEDDING_DIM, hidden_dim=64, output_dim=32)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   ✅ Model created")
    print(f"   ✅ Total parameters: {total_params:,}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ========== STEP 5: TRAIN GNN ==========
print("\n[5/5] Training GNN...")

try:
    # Training setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"   📍 Device: {device}")
    
    model = model.to(device)
    data = data.to(device)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    loss_fn = torch.nn.MSELoss()
    
    # Training loop - unsupervised: minimize reconstruction error
    num_epochs = 50
    losses = []
    
    print(f"   Starting training for {num_epochs} epochs...")
    
    for epoch in range(num_epochs):
        model.train()
        
        # Forward pass
        embeddings = model(data.x, data.edge_index)
        
        # Reconstruction loss: embeddings should be similar for connected nodes
        loss = 0
        edge_pairs = data.edge_index.t()
        
        for i, j in edge_pairs[:1000]:  # Limit to avoid OOM
            i, j = i.item(), j.item()
            sim = torch.cosine_similarity(embeddings[i].unsqueeze(0), 
                                         embeddings[j].unsqueeze(0))
            loss += (1 - sim).mean()  # Maximize similarity
        
        loss = loss / min(1000, edge_pairs.shape[0])
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        losses.append(loss.item())
        
        if (epoch + 1) % 10 == 0:
            print(f"   Epoch {epoch+1}/{num_epochs} - Loss: {loss.item():.6f}")
    
    print(f"   ✅ Training complete!")
    print(f"   ✅ Final loss: {losses[-1]:.6f}")
    
    # Get final embeddings
    model.eval()
    with torch.no_grad():
        final_embeddings = model(data.x, data.edge_index)
    
    print(f"   ✅ Final embeddings shape: {final_embeddings.shape}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ========== SAVE MODEL ==========
print(f"\n💾 Saving model to {MODEL_PATH}...")

try:
    os.makedirs("./models", exist_ok=True)
    
    # Save model state
    torch.save({
        'model_state_dict': model.state_dict(),
        'embeddings': final_embeddings.cpu().numpy(),
        'node_mapping': node_mapping,
        'config': {
            'input_dim': EMBEDDING_DIM,
            'hidden_dim': 64,
            'output_dim': 32,
            'num_games': num_games,
            'num_edges': edge_index.shape[1]
        }
    }, MODEL_PATH)
    
    print(f"   ✅ Model saved")
    
    # Save embeddings separately for API use
    embeddings_path = "./models/embeddings.npy"
    np.save(embeddings_path, final_embeddings.cpu().numpy())
    print(f"   ✅ Embeddings saved to {embeddings_path}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ========== STATS & VALIDATION ==========
print("\n" + "=" * 80)
print("📊 TRAINING SUMMARY")
print("=" * 80)
print(f"""
✅ Data Processing:
   • Total games: {num_games}
   • Total edges: {edge_index.shape[1]}
   • Feature dimension: {x.shape[1]}

✅ Model:
   • Input dimension: {EMBEDDING_DIM}
   • Hidden dimension: 64
   • Output dimension: 32
   • Total parameters: {total_params:,}

✅ Training:
   • Epochs: {num_epochs}
   • Final loss: {losses[-1]:.6f}
   • Device: {device}

✅ Output Files:
   • Model: {MODEL_PATH}
   • Embeddings: ./models/embeddings.npy
   • Mapping: {MAPPING_PATH}

📝 Next step: 
   Use embeddings for:
   1. Game similarity search (cosine similarity)
   2. Missing piece reconstruction (GAN decoder)
   3. Rule recommendation system
""")

driver.close()
print("=" * 80)