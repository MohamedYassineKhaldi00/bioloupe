"""
Complete BioLoupe backend with SQLite - fixed startup script
"""
import os
import sys
import asyncio
import logging

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variable for SQLite
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./bioloupe.db')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')  # Will use mock Redis if not available
os.environ.setdefault('ENVIRONMENT', 'development')

import uvicorn
from app import create_app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def startup():
    """Setup application and create database tables if needed"""
    logger.info("Setting up BioLoupe backend...")
    
    # Import after environment setup
    from app.db.base import engine, Base
    from sqlalchemy import text
    
    try:
        if engine is not None:
            # Create tables for SQLite (simpler than migrations)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        else:
            logger.info("Running in test mode without database")
    except Exception as e:
        logger.warning(f"Database setup failed: {e}, continuing without database")

def main():
    """Main function to start the server"""
    try:
        logger.info("Starting BioLoupe backend server...")
        
        # Create the FastAPI app
        app = create_app()
        
        # Run startup
        asyncio.run(startup())
        
        logger.info("🚀 BioLoupe backend is ready!")
        logger.info("📋 Server will start on: http://127.0.0.1:8000")
        logger.info("📖 API docs available at: http://127.0.0.1:8000/docs")
        logger.info("❤️ Health check at: http://127.0.0.1:8000/api/v1/health")
        logger.info("Press Ctrl+C to stop the server")
        
        # Start the server
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()