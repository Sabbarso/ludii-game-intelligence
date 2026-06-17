Voici le contenu du fichier `README.md` à placer à la racine de votre dépôt GitHub.

```markdown
# 🏺 LUDII Game Intelligence

**Intelligence Artificielle pour l'Archéologie Ludique**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-brightgreen.svg)](https://neo4j.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Présentation

**LUDII Game Intelligence** est un système d'intelligence artificielle conçu pour aider les archéologues à **identifier**, **analyser** et **reconstituer** des jeux de société anciens à partir d'artefacts (plateaux, fragments, pièces). 

Il combine :
- La **vision par ordinateur** (YOLOv8) pour détecter plateaux et pièces sur des photos,
- Une **base de connaissances en graphe** (Neo4j) modélisant 1 621 jeux historiques,
- Un **moteur de recherche sémantique** et un **LLM** (Gemini 2.5 Flash) pour répondre aux questions en langage naturel,
- Une **reconstruction 3D** des plateaux identifiés,
- Une **interface utilisateur** (Streamlit) et un **workflow d'orchestration** (n8n).

---

## ✨ Fonctionnalités

- 📷 **Analyse d'image** : téléversez une photo de plateau, YOLO détecte les dimensions et les pièces, le système identifie le jeu.
- 📝 **Description textuelle** : décrivez l'artefact (matériau, forme, symboles, lieu de découverte), le système suggère les jeux les plus probables.
- 🗺️ **Inférence géographique** : à partir d'une région ou d'un lieu de fouille, retrouvez les jeux historiques associés.
- 📏 **Dimensions partielles** : même avec un plateau incomplet, le système propose une identification avec un score de confiance.
- 🏗️ **Reconstruction 3D** : visualisez interactivement le plateau reconstitué avec ses pièces.
- 💬 **Question/Réponse** : interrogez le système en langage naturel sur les règles, l'origine ou l'histoire d'un jeu.
- 🔗 **Jeux similaires** : découvrez des jeux culturellement, temporellement ou thématiquement proches.
- 📊 **Dashboard analytique** : explorez les statistiques de la base (types de plateaux, dimensions, pièces).

---

## 🧱 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Swagger API   │    │   n8n Workflow  │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                         ┌──────┴──────┐
                         │   FastAPI   │
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
       ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐
       │    Neo4j    │   │   Gemini    │   │  Sentence   │
       │   (Graphe)  │   │  2.5 Flash  │   │Transformers │
       └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 🛠️ Stack Technique

| Composant          | Technologie                    | Usage                                      |
|--------------------|--------------------------------|--------------------------------------------|
| Base de données    | Neo4j 5.x                      | Graphe de connaissances (1 621 jeux)       |
| API                | FastAPI                        | Endpoints REST (8 routes)                  |
| Vision             | YOLOv8                         | Détection de plateaux et pièces            |
| LLM                | Gemini 2.5 Flash (Google AI)   | Génération de réponses en français         |
| Embeddings         | all-MiniLM-L6-v2               | Recherche sémantique par similarité cosinus|
| Orchestration      | n8n (Docker)                   | Workflow automatisé                        |
| Interface          | Streamlit                      | Dashboard interactif + reconstruction 3D   |
| Modélisation 3D    | Trimesh                        | Génération de plateaux au format GLB       |
| Visualisation      | Plotly                         | Graphiques du dashboard analytics          |

---

## 📁 Structure du Projet

```
ludii-game-intelligence/
├── phase1_ludii_rag/          # Système RAG (embeddings + Gemini)
│   ├── hybrid_rag.py
│   └── __init__.py
├── phase2_vision/             # Vision par ordinateur
│   ├── board_3d.py            # Reconstruction 3D
│   ├── detect.py              # Détection YOLO
│   └── ...
├── phase3_api/                # API REST
│   ├── main.py                # Point d'entrée FastAPI
│   ├── identify_game_from_yolo.py  # Endpoints YOLO + 3D + similaires
│   ├── hybrid_rag_routes.py   # Endpoints RAG
│   └── ...
├── phase4_neo4j/              # Scripts d'import et d'enrichissement Neo4j
│   ├── pipeline.py
│   ├── import_lud_signatures.py
│   ├── import_regions_periods.py
│   └── ...
├── app.py                     # Interface Streamlit
├── requirements.txt           # Dépendances Python
├── .env                       # Variables d'environnement
└── README.md                  # Ce fichier
```

---

## 🚀 Installation et Démarrage

### Prérequis

- **Python 3.11+**
- **Neo4j 5.x** (local ou Desktop)
- **Docker** (pour n8n, optionnel)
- **Clé API Gemini** (gratuite sur [Google AI Studio](https://aistudio.google.com/))

### 1. Cloner le dépôt

```bash
git clone https://github.com/salma12814/ludii-game-intelligence.git
cd ludii-game-intelligence
```

### 2. Créer l'environnement virtuel et installer les dépendances

```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Créez un fichier `.env` à la racine :

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=votre_mot_de_passe
GEMINI_API_KEY=votre_clé_gemini
```

### 4. Importer les données dans Neo4j

Assurez-vous que Neo4j est lancé, puis exécutez les scripts d'import (si ce n'est pas déjà fait) :

```bash
python phase4_neo4j/import_mysql_to_neo4j.py
python phase4_neo4j/generate_yolo_signatures.py
python phase4_neo4j/import_rules_features.py
```

### 5. Lancer l'API

```bash
uvicorn phase3_api.main:app --reload
```

L'API est accessible sur [http://localhost:8000/docs](http://localhost:8000/docs).

### 6. Lancer l'interface Streamlit

```bash
streamlit run app.py
```

L'interface est accessible sur [http://localhost:8501](http://localhost:8501).

### 7. (Optionnel) Lancer n8n avec Docker

```bash
docker run -d --name n8n -p 5678:5678 n8nio/n8n
```

Puis importez le workflow `ludii_workflow.json` dans l'interface [http://localhost:5678](http://localhost:5678).

---

## 📸 Captures d'écran

### Interface Streamlit – Onglet Description
![Onglet Description](captures/streamlit_description.png)

### Reconstruction 3D d'un plateau
![Reconstruction 3D](captures/streamlit_3d.png)

### Dashboard Analytics
![Dashboard](captures/streamlit_dashboard.png)

### API Swagger
![Swagger](captures/swagger_main.png)

---

## 🧪 Tests

Vous pouvez tester l'API directement via Swagger ou avec `curl` :

```bash
curl "http://localhost:8000/api/v1/rag/ask?question=Explique-moi les règles du Senet"
```

Ou via le webhook n8n :

```bash
curl -X POST http://localhost:5678/webhook/ludii/analyze \
  -H "Content-Type: application/json" \
  -d '{"description":"Plateau en bois trouvé dans une tombe égyptienne"}'
```

---

## 📊 Base de Connaissances

| Entité           | Nombre   |
|------------------|----------|
| Jeux             | 1 621    |
| Règles           | 3 337    |
| Signatures YOLO  | 486      |
| Régions          | 28       |
| Périodes         | 13       |
| Catégories       | 52       |
| Relations totales| ~16 739  |

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour toute suggestion ou amélioration, veuillez ouvrir une issue ou soumettre une pull request.

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🙏 Remerciements

- Base de données [Ludii](https://ludii.games/) pour le corpus de jeux
- Google AI pour l'API Gemini
- Équipe encadrante du projet

---

**🏺 LUDII Game Intelligence – Quand l'IA rencontre l'archéologie ludique**
```

Il vous suffit de copier ce contenu dans un fichier `README.md` à la racine de votre dépôt GitHub. Les captures d'écran doivent être placées dans un dossier `captures/` (ou vous pouvez ajuster les chemins). Ce README couvre l'essentiel de votre projet et donne une bonne première impression aux visiteurs.
