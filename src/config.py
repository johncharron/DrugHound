"""Configuration management for DrugHound."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings loaded from environment."""
    
    # PubMed API
    PUBMED_API_KEY = os.getenv('PUBMED_API_KEY', '')
    
    # Ollama settings
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
    
    # Rate limits
    REQUESTS_PER_SECOND = int(os.getenv('REQUESTS_PER_SECOND', '9'))
    
    # Directories
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    LOGS_DIR = os.getenv('LOGS_DIR', 'logs')
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.PUBMED_API_KEY:
            raise ValueError(
                "PUBMED_API_KEY not set. "
                "Create a .env file with your API key."
            )
        return True

# Create singleton instance
config = Config()
