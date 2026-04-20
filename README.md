# ?? Ludii Game Intelligence

AI-powered system for analyzing 200+ Ludii games.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
docker-compose up -d
```

## Quick Start

Phase 1: Ludii RAG
```bash
python phase1_ludii_rag/ludii_scraper.py
```

Phase 3: API
```bash
uvicorn phase3_api.main:app --reload
```
