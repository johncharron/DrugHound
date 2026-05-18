"""Enhanced confidence scoring - adds to working version without modifying it"""

import json
from pathlib import Path

class ConfidenceScorer:
    def __init__(self):
        config_path = Path("algorithms/enhanced_config.json")
        if config_path.exists():
            with open(config_path) as f:
                self.config = json.load(f)
        else:
            self.config = {
                "weights": {"publication_novelty": 0.5, "evidence_quality": 0.5},
                "evidence_quality_scores": {"preclinical": 0.5}
            }
    
    def calculate(self, drug_data: dict) -> dict:
        """Calculate enhanced confidence score"""
        
        # Get base novelty from working version
        novelty_score = drug_data.get('novelty_score', 50) / 100
        
        # Determine evidence quality
        trials = drug_data.get('trials', [])
        max_phase = self._get_max_phase(trials)
        evidence_score = self.config['evidence_quality_scores'].get(
            max_phase, self.config['evidence_quality_scores']['preclinical']
        )
        
        # Check safety signals
        safety_score = self._check_safety(drug_data)
        
        # Calculate weighted score
        final = (
            self.config['weights']['publication_novelty'] * novelty_score +
            self.config['weights']['evidence_quality'] * evidence_score +
            self.config['weights']['safety_signal'] * safety_score
        )
        
        return {
            'confidence_score': round(final * 100, 2),
            'breakdown': {
                'novelty': round(novelty_score * 100, 2),
                'evidence_quality': round(evidence_score * 100, 2),
                'safety': round(safety_score * 100, 2)
            },
            'evidence_phase': max_phase,
            'total_trials': len(trials)
        }
    
    def _get_max_phase(self, trials):
        phases = [t.get('phase', '').lower() for t in trials]
        if 'phase 3' in phases: return 'phase_3'
        if 'phase 2' in phases: return 'phase_2'
        if 'phase 1' in phases: return 'phase_1'
        return 'preclinical'
    
    def _check_safety(self, drug_data):
        text = str(drug_data).lower()
        for keyword in self.config.get('safety_keywords', []):
            if keyword in text:
                return self.config.get('safety_penalty', 0.5)
        return 1.0
