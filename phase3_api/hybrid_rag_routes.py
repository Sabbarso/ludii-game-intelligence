from fastapi import APIRouter, HTTPException, Query
from phase1_ludii_rag.hybrid_rag import HybridRAG

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Hybride"])

# Instance partagée (chargée une seule fois)
_rag_instance = None

def get_rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = HybridRAG()
    return _rag_instance

@router.get("/ask")
async def ask(
    question: str = Query(..., description="Question en langage naturel")
):
    """
    RAG Hybride : Graph Neo4j + Embeddings légers.
    
    Exemples :
    - 'Explique-moi les règles du Senet'
    - 'Quelle est l'origine des échecs ?'
    - 'Quels jeux sont similaires au Go ?'
    - 'Liste les jeux de l'Égypte antique'
    """
    try:
        rag = get_rag()
        response = rag.answer(question)
        return {"status": "success", **response}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/search")
async def search(
    query: str = Query(...),
    limit: int = Query(10)
):
    """Recherche hybride rapide"""
    try:
        rag = get_rag()
        results = rag.search(query, top_k=limit)
        return {"status": "success", "query": query, "results": results}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")