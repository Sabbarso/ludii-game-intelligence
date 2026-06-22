from fastapi import APIRouter, HTTPException, Query
from phase1_ludii_rag.hybrid_rag import HybridRAG

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Gemini"])

_rag_instance = None

def get_rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = HybridRAG(use_llm=True)
    return _rag_instance

@router.get("/ask")
async def ask(question: str = Query(..., description="Question en langage naturel")):
    """
    RAG avec Gemini 2.5 Flash.
    Ex: 'Explique-moi les règles du Senet'
    """
    try:
        rag = get_rag()
        # FORCER Gemini
        rag.use_llm = True
        if not rag.gemini_api_key:
            return {"status": "error", "message": "Clé Gemini non configurée dans .env"}
        
        response = rag.answer(question)
        return {"status": "success", "llm": "Gemini 2.5 Flash", **response}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/search")
async def search(query: str = Query(...), limit: int = Query(10)):
    """Recherche rapide sans LLM"""
    try:
        rag = get_rag()
        results = rag.search(query, top_k=limit)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")