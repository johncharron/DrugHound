"""Simple AI Copilot - natural language Q&A about discovered drugs"""

import subprocess
import json
from typing import Optional, Dict

class SimpleCopilot:
    def __init__(self):
        self.ollama_available = self._check_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(['ollama', '--version'], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def ask(self, question: str, drug_context: Optional[str] = None) -> Dict:
        """Answer question about drug discovery"""
        
        if not self.ollama_available:
            return {
                'answer': "AI Copilot requires Ollama. Install with: curl -fsSL https://ollama.com/install.sh | sh",
                'citations': [],
                'available': False
            }
        
        # Build prompt with context
        context = f"Drug context: {drug_context}" if drug_context else "General drug discovery question"
        
        prompt = f"""You are DrugHound AI, a drug discovery expert.
        
Context: {context}

Question: {question}

Answer concisely with specific, actionable insights. If unsure, say so."""
        
        try:
            # Run Ollama
            result = subprocess.run(
                ['ollama', 'run', 'llama3.2', prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'answer': result.stdout.strip(),
                'citations': [],
                'available': True
            }
        except subprocess.TimeoutExpired:
            return {'answer': "Query timed out. Try a simpler question.", 'citations': [], 'available': True}
        except Exception as e:
            return {'answer': f"Error: {str(e)}", 'citations': [], 'available': True}
    
    def suggest_similar_drugs(self, drug_name: str, current_drugs: list) -> list:
        """AI-powered drug similarity suggestions"""
        if not self.ollama_available:
            return current_drugs[:3]
        
        prompt = f"Based on drug naming patterns, suggest 3 drugs similar to {drug_name}. Return only drug names, one per line."
        
        try:
            result = subprocess.run(
                ['ollama', 'run', 'llama3.2', prompt],
                capture_output=True,
                text=True,
                timeout=15
            )
            suggestions = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
            return suggestions[:3]
        except:
            return current_drugs[:3]
