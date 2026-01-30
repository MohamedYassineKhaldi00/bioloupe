from .global_search import router as global_search_router
from .publication import router as publication_search_router
from .similarity import router as similarity_router

__all__ = ["global_search_router", "publication_search_router", "similarity_router"]