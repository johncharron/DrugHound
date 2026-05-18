"""Elasticsearch integration - Optional feature."""
import json
from typing import List, Dict, Optional

class DrugIndexer:
    """Elasticsearch indexer with fallback to in-memory search."""
    
    def __init__(self, host: Optional[str] = None):
        self.available = False
        self.es = None
        self.index_name = 'drughound'
        self.in_memory_cache = []
        
        if host:
            try:
                from elasticsearch import Elasticsearch
                # Ensure host has scheme
                if not host.startswith(('http://', 'https://')):
                    host = f'http://{host}'
                self.es = Elasticsearch([host])
                self.available = self.es.ping()
                if self.available:
                    print(f"✅ Elasticsearch connected at {host}")
                else:
                    print("⚠️ Elasticsearch not available - using in-memory search")
            except Exception as e:
                print(f"⚠️ Elasticsearch not available: {e}")
                print("   Using in-memory search fallback")
    
    def create_index(self):
        """Create index mapping if Elasticsearch is available."""
        if not self.available:
            return
        mapping = {
            "mappings": {
                "properties": {
                    "drug_name": {"type": "text", "analyzer": "standard"},
                    "condition": {"type": "text", "analyzer": "standard"},
                    "mechanism": {"type": "text", "analyzer": "standard"},
                    "novelty_score": {"type": "float"},
                    "pubmed_count": {"type": "integer"},
                    "phase": {"type": "keyword"}
                }
            }
        }
        try:
            self.es.indices.create(index=self.index_name, body=mapping, ignore=400)
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    def index_drug(self, drug_data: Dict):
        """Index a single drug."""
        self.in_memory_cache.append(drug_data)
        if self.available:
            try:
                self.es.index(index=self.index_name, id=drug_data.get('id'), body=drug_data)
            except:
                pass
    
    def bulk_index(self, drugs: List[Dict]):
        """Bulk index multiple drugs."""
        self.in_memory_cache.extend(drugs)
        if self.available:
            try:
                from elasticsearch import helpers
                actions = [{"_index": self.index_name, "_id": d.get('id'), "_source": d} for d in drugs]
                helpers.bulk(self.es, actions)
            except:
                pass
    
    def search(self, query: str, size: int = 20) -> List[Dict]:
        """Search for drugs."""
        if self.available and self.es:
            try:
                body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["drug_name^3", "condition^2", "mechanism"]
                        }
                    },
                    "size": size
                }
                result = self.es.search(index=self.index_name, body=body)
                return [hit['_source'] for hit in result['hits']['hits']]
            except:
                pass
        
        # Fallback to in-memory search
        query_lower = query.lower()
        results = []
        for drug in self.in_memory_cache:
            if (query_lower in drug.get('drug_name', '').lower() or
                query_lower in drug.get('condition', '').lower() or
                query_lower in drug.get('mechanism', '').lower()):
                results.append(drug)
        return results[:size]
