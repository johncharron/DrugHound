"""PubMed API client for DrugHound."""

import logging
import time
import requests
from typing import Dict, Optional
from src.config import config

logger = logging.getLogger(__name__)

class PubMedClient:
    """Client for PubMed E-utilities API."""
    
    def __init__(self):
        """Initialize PubMed client with config."""
        self.api_key = config.PUBMED_API_KEY
        self.rate_limit = config.REQUESTS_PER_SECOND
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.last_request_time = 0.0
        
        if not self.api_key:
            logger.warning("No PubMed API key found. Rate limits will be lower.")
    
    def get_publication_count(self, drug: str, years_back: int = 3) -> int:
        """Get publication count for a drug."""
        # Implementation here
        pass
