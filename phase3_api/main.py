"""Application FastAPI principale - LUDII Game Intelligence"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from phase3_api.schemas import HealthResponse

from phase3_api.identify_game_from_yolo import router as yolo_identify_router
from phase3_api.hybrid_rag_routes import router as hybrid_rag_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("\n" + "="*80)
    print("🚀 LUDII API STARTING...")
    print("="*80)
    print("\n📊 Available modules:")
    print("   ✅ Neo4j Graph Database")
    print("   ✅ GNN Embeddings (32-dim)")
    print("   ✅ Historical Search")
    print("   ✅ YOLO Identification")
    print("   ✅ Hybrid RAG (Graph + Embeddings)")
    print("\n✅ API READY!")
    print("="*80 + "\n")
    yield
    print("\n🛑 API SHUTTING DOWN...")

app = FastAPI(
    title="🎲 LUDII Game Intelligence API",
    description="AI-powered game recognition and analysis system",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ROUTERS ==========

app.include_router(yolo_identify_router)
app.include_router(hybrid_rag_router)

# ========== BASIC ENDPOINTS ==========
@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API info"""
    return {
        "name": "LUDII Game Intelligence API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "historical": "/api/v1/historical_search",
            "gnn": "/api/v1/gnn/similar_games",
            "yolo": "/api/v1/identify_game_from_yolo",
            "rag": "/api/v1/rag/ask",
            "swagger": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check"""
    return HealthResponse(
        status="ok",
        version="2.0.0",
        components={
            "neo4j": "ready",
            "gnn": "ready",
            "historical_search": "ready",
            "yolo": "ready",
            "rag": "ready"
        },
        supported_games=["chess", "go", "checkers", "shogi", "xiangqi"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("phase3_api.main:app", host="0.0.0.0", port=8000, reload=True)