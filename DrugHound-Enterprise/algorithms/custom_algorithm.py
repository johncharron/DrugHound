"""
Custom Algorithm Template - Copy this to create your own algorithm
"""

from .base_algorithm import NoveltyAlgorithm, DrugScore

class MyCustomAlgorithm(NoveltyAlgorithm):
    """
    Your custom algorithm - modify this file to change behavior
    No need to restart the server - changes take effect on next research
    """
    
    def __init__(self):
        # Customize your weights here
        self.publication_bonus = 50
        self.phase_bonus = 30
        self.rarity_bonus = 20
        
    def calculate_score(self, drug_data: dict) -> DrugScore:
        """YOUR CUSTOM SCORING LOGIC HERE"""
        
        pub_count = drug_data.get('pubmed_count', 0)
        phase = drug_data.get('phase', 'Unknown')
        condition = drug_data.get('condition', '')
        
        # Example custom scoring:
        # Give bonus to drugs with very few publications
        if pub_count == 0:
            pub_score = 100
        elif pub_count < 10:
            pub_score = 90
        elif pub_count < 50:
            pub_score = 70
        else:
            pub_score = 30
        
        # Phase scoring - modify as you like
        phase_map = {
            'Phase 1': 30,
            'Phase 2': 15,
            'Phase 3': 5,
            'Phase 4': 0
        }
        phase_score = phase_map.get(phase, 10)
        
        # Rarity detection - add your own keywords
        rare_keywords = ['rare', 'orphan', 'genetic', 'inherited']
        is_rare = any(kw in condition.lower() for kw in rare_keywords)
        rarity_score = 20 if is_rare else 0
        
        total = pub_score + phase_score + rarity_score
        
        return DrugScore(
            total=total,
            components={
                "publication": pub_score,
                "phase": phase_score,
                "rarity": rarity_score
            },
            reasoning=[
                f"Publications: {pub_count} -> {pub_score} points",
                f"Phase: {phase} -> {phase_score} points",
                f"Rare disease bonus: {rarity_score}"
            ],
            novelty_level="HIGH" if total >= 70 else "MODERATE" if total >= 40 else "LOW"
        )
    
    def get_algorithm_info(self) -> dict:
        return {
            "name": "My Custom Algorithm",
            "version": "1.0.0",
            "description": "Modify this file to change scoring"
        }
    
    def update_weights(self, weights: dict) -> None:
        """Update weights without code changes"""
        if 'publication_bonus' in weights:
            self.publication_bonus = weights['publication_bonus']
        if 'phase_bonus' in weights:
            self.phase_bonus = weights['phase_bonus']
