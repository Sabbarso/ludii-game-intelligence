# 🏺 LUDII Game Intelligence
### Intelligence Artificielle pour l'Archéologie Ludique

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Neo4j-5.x-008CC1?style=for-the-badge&logo=neo4j&logoColor=white"/>
  <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-FF6F00?style=for-the-badge&logo=opencv&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge"/>
</p>

<p align="center">
  <b>Identifier · Contextualiser · Reconstituer</b><br/>
  Un système IA complet pour l'analyse automatique des jeux de société historiques
</p>

---

## 📖 Présentation

**LUDII Game Intelligence** est une plateforme d'intelligence artificielle conçue pour assister les archéologues dans l'**identification**, l'**analyse historique** et la **reconstruction** de jeux de table anciens à partir d'artefacts physiques (plateaux fragmentaires, pièces isolées, photographies de fouilles).

Le système combine quatre piliers technologiques :

| Pilier | Technologie | Rôle |
|--------|-------------|------|
| 👁️ Vision | YOLOv8 | Détection des pièces et du plateau sur image |
| 🧠 Connaissance | Neo4j (graphe) | 1 621 jeux · 3 337 règles · 16 739 relations |
| 💬 Langage | Gemini 2.0 Flash + RAG | Réponses contextualisées en langage naturel |
| 🏗️ Reconstruction | Trimesh | Modèles 3D interactifs au format GLB |

---

## ✨ Fonctionnalités

```
📷  Analyse d'image      →  Upload photo → YOLO détecte → Graphe identifie
📝  Description libre    →  Texte de l'artefact → Recherche sémantique
🗺️  Lieu de fouille     →  Région/période → Jeux culturellement proches
📏  Dimensions partielles→  Plateau endommagé → Identification tolérante
🏗️  Reconstruction 3D   →  Modèle GLB interactif du plateau reconstitué
💬  Question/Réponse     →  « Quelles sont les règles du Senet ? » → Gemini
🔗  Jeux similaires      →  Traversée du graphe par région, période, catégorie
📊  Dashboard analytics  →  KPIs, distributions, statistiques du corpus
```

---

## 🧱 Architecture du système

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTERFACES UTILISATEUR                       │
│         Streamlit (UI)        Swagger (API)        n8n (Workflows)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                        ┌──────┴──────┐
                        │   FastAPI   │   ← REST API Python 3.11
                        └──────┬──────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────┴──────┐      ┌──────┴──────┐     ┌──────┴──────┐
   │   Neo4j     │      │   Gemini    │     │  Sentence   │
   │  1 621 jeux │      │  2.0 Flash  │     │ Transformers│
   └──────┬──────┘      └─────────────┘     └─────────────┘
          │
   ┌──────┴──────┐
   │   YOLOv8   │   ← Vision par ordinateur
   └─────────────┘
```

---

## 📦 Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Base de données | Neo4j | 5.x |
| API REST | FastAPI | 0.104+ |
| Détection visuelle | YOLOv8 (Ultralytics) | latest |
| Modèle de langage | Gemini 2.0 Flash | Google AI |
| Embeddings sémantiques | all-MiniLM-L6-v2 | Sentence Transformers |
| Orchestration | n8n | 2.25.7 (Docker) |
| Interface utilisateur | Streamlit | 1.32+ |
| Reconstruction 3D | Trimesh | latest |
| Visualisation | Plotly | latest |
| Runtime | Python | 3.11 |

---

## 📊 Base de connaissances

```
  Jeux documentés     ████████████████████  1 621
  Règles (Rulesets)   ████████████████████  3 337
  Signatures YOLO     ████████████████████    486
  Régions historiques ████████████████████     28
  Périodes            ████████████████████     13
  Catégories          ████████████████████     52
  Relations (graphe)  ████████████████████ ~16 739
```

Couvrant **5 continents**, **13 périodes chronologiques** (de l'Antiquité à nos jours)
et **52 catégories** de jeux, du Senet égyptien aux échecs contemporains.

---

## 📁 Structure du projet

```
ludii-game-intelligence/
│
├── phase1_ludii_rag/               # Système RAG hybride
│   ├── hybrid_rag.py               #   Embeddings + Gemini + fallback Neo4j
│   └── __init__.py
│
├── phase2_vision/                  # Vision par ordinateur
│   ├── board_detector.py           #   Détection du plateau
│   ├── piece_detector.py           #   Détection des pièces
│   ├── board_3d.py                 #   Reconstruction 3D (Trimesh → GLB)
│   └── detect.py                   #   Script de détection
│
├── phase3_api/                     # API REST FastAPI
│   ├── main.py                     #   Point d'entrée — routers
│   ├── identify_game_from_yolo.py  #   Identification + 3D + similarité
│   ├── hybrid_rag_routes.py        #   Endpoints RAG / question-réponse
│   ├── historical_search.py        #   Recherche géo-temporelle
│   ├── gnn_routes.py               #   Similarité GNN
│   └── schemas.py                  #   Modèles Pydantic
│
├── phase4_neo4j/                   # Pipeline de données Neo4j
│   ├── pipeline.py                 #   Connexion et utilitaires
│   ├── import_mysql_to_neo4j.py    #   Import MySQL → Neo4j
│   ├── import_lud_signatures.py    #   Parsing .lud → YOLOSignature
│   ├── import_regions_periods.py   #   Régions, périodes, catégories
│   └── import_rules_features.py    #   Vecteurs de règles + distances
│
├── app.py                          # Interface Streamlit
├── requirements.txt                # Dépendances Python
├── .env.example                    # Template variables d'environnement
└── README.md
```

---

## 🚀 Installation

### Prérequis

- Python 3.11+
- Neo4j 5.x ([Neo4j Desktop](https://neo4j.com/download/))
- Docker (pour n8n — optionnel)
- Clé API Gemini ([Google AI Studio](https://aistudio.google.com/) — gratuit)

### 1. Cloner le dépôt

```bash
git clone https://github.com/salma12814/ludii-game-intelligence.git
cd ludii-game-intelligence
```

### 2. Environnement virtuel et dépendances

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` :

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=votre_mot_de_passe
GEMINI_API_KEY=votre_clé_api_gemini
```

### 4. Construire le graphe Neo4j

Assurez-vous que Neo4j est démarré, puis exécutez les scripts dans l'ordre :

```bash
python phase4_neo4j/import_mysql_to_neo4j.py      # 1 621 jeux, 3 337 règles
python phase4_neo4j/import_lud_signatures.py       # 486 signatures YOLO
python phase4_neo4j/import_regions_periods.py      # Régions, périodes, catégories
python phase4_neo4j/import_rules_features.py       # Distances géo/temporelles
```

### 5. Lancer l'API

```bash
uvicorn phase3_api.main:app --reload --host 127.0.0.1 --port 8000
```

→ Documentation interactive : [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Lancer l'interface Streamlit

```bash
streamlit run app.py
```

→ Interface utilisateur : [http://localhost:8501](http://localhost:8501)

### 7. (Optionnel) Lancer n8n

```bash
docker run -d --name n8n -p 5678:5678 n8nio/n8n
```

→ Importer `ludii_workflow.json` dans [http://localhost:5678](http://localhost:5678)

---

## 🌐 URLs des services

| Service | URL |
|---------|-----|
| API FastAPI | http://localhost:8000 |
| Documentation Swagger | http://localhost:8000/docs |
| Interface Streamlit | http://localhost:8501 |
| Orchestration n8n | http://localhost:5678 |
| Neo4j Browser | http://localhost:7474 |

---

## 🧪 Exemples d'utilisation

**Identification par dimensions (API) :**

```bash
curl -X POST http://localhost:8000/api/v1/identify_game_from_yolo \
  -H "Content-Type: application/json" \
  -d '{"board_cols": 8, "board_rows": 8, "total_pieces": 32, "pieces": []}'
```

**Question en langage naturel (API) :**

```bash
curl "http://localhost:8000/api/v1/rag/ask?question=Explique-moi les règles du Senet"
```

**Via webhook n8n :**

```bash
curl -X POST http://localhost:5678/webhook/ludii/analyze \
  -H "Content-Type: application/json" \
  -d '{"description": "Plateau en bois trouvé dans une tombe égyptienne, 30 cases"}'
```

---

## 📸 Captures d'écran

> Placez vos captures dans un dossier `captures/` à la racine du dépôt.

| Interface | Aperçu |
|-----------|--------|
| Streamlit — Identification par image | `captures/streamlit_image.png` |
| Streamlit — Question/Réponse RAG | `captures/streamlit_rag.png` |
| Streamlit — Reconstruction 3D | `captures/streamlit_3d.png` |
| Streamlit — Dashboard analytics | `captures/streamlit_dashboard.png` |
| API — Swagger UI | `captures/swagger_ui.png` |
| Neo4j Browser — Graphe | `captures/neo4j_browser.png` |

---

## 🤝 Contribution

Les contributions sont les bienvenues.

1. Forkez le dépôt
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Commitez vos changements : `git commit -m 'feat: description'`
4. Pushez : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

---

## 📄 Licence

Ce projet est distribué sous licence **MIT**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

<p align="center">
  <b>🏺 LUDII Game Intelligence</b> — IA pour l'Archéologie Ludique<br/>
  <a href="https://github.com/salma12814/ludii-game-intelligence">github.com/salma12814/ludii-game-intelligence</a>
</p>
