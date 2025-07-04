import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Config:
    # Gemini settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Default LLM model
    DEFAULT_LLM_MODEL = "gemini-pro"
    
    # Storage settings
    CHROMA_DB_DIRECTORY = os.getenv("CHROMA_DB_DIRECTORY", "./chroma_db")
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    
    # Optional Neo4j settings for Phase 2
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Chunking settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY is not set in .env file")
            return False
        
        if not os.path.exists(cls.DATA_DIR):
            logger.warning(f"Data directory {cls.DATA_DIR} does not exist. Creating it...")
            os.makedirs(cls.DATA_DIR)
            
        return True
