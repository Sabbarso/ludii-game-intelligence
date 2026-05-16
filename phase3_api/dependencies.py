"""
Dependencies pour FastAPI - Injection de dépendances
"""

from functools import lru_cache
from typing import Optional

# ========== Vision Dependencies ==========
try:
    from phase2_vision.board_detector import BoardGameDetector
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    BoardGameDetector = None

# ========== NLP Pipeline Dependencies ==========
try:
    from phase1_ludii_rag.nlp_pipeline import LudiiNLPPipeline
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    LudiiNLPPipeline = None

# ========== Neo4j Pipeline ==========
from phase4_neo4j.pipeline import Neo4jPipeline

# ========== Singletons (cached) ==========
_detector_instance: Optional[BoardGameDetector] = None
_pipeline_instance: Optional[LudiiNLPPipeline] = None
_neo4j_instance: Optional[Neo4jPipeline] = None


def get_detector() -> Optional[BoardGameDetector]:
    """
    Get or create BoardGameDetector instance
    Returns None if vision module not available
    """
    global _detector_instance
    
    if not VISION_AVAILABLE:
        print("⚠️  Vision module not available")
        return None
    
    if _detector_instance is None:
        try:
            _detector_instance = BoardGameDetector()
            print("✅ Detector loaded")
        except Exception as e:
            print(f"❌ Error loading detector: {e}")
            return None
    
    return _detector_instance


def get_pipeline() -> Optional[LudiiNLPPipeline]:
    """
    Get or create LudiiNLPPipeline instance
    Returns None if NLP module not available
    """
    global _pipeline_instance
    
    if not NLP_AVAILABLE:
        print("⚠️  NLP Pipeline not available")
        return None
    
    if _pipeline_instance is None:
        try:
            _pipeline_instance = LudiiNLPPipeline()
            print("✅ NLP Pipeline loaded")
        except Exception as e:
            print(f"❌ Error loading pipeline: {e}")
            return None
    
    return _pipeline_instance


def get_neo4j_pipeline() -> Neo4jPipeline:
    """
    Get or create Neo4jPipeline instance
    """
    global _neo4j_instance
    
    if _neo4j_instance is None:
        _neo4j_instance = Neo4jPipeline()
    
    return _neo4j_instance


# ========== Info Functions ==========
def get_system_info() -> dict:
    """Get system information (what's available)"""
    return {
        "vision_available": VISION_AVAILABLE,
        "nlp_available": NLP_AVAILABLE,
        "neo4j_available": True,
    }