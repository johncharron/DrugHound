"""
Algorithm Manager - Dynamically loads and switches algorithms
"""

import importlib
import os
from typing import Dict, Any
from .base_algorithm import NoveltyAlgorithm
from .config_driven_algorithm import ConfigurableAlgorithm

class AlgorithmManager:
    """Manages and switches between different scoring algorithms"""
    
    def __init__(self):
        self.algorithm: NoveltyAlgorithm = None
        self.algorithm_name = "default"
        self.load_algorithm("config_driven")
    
    def load_algorithm(self, name: str) -> None:
        """Load a specific algorithm by name"""
        algorithms = {
            "config_driven": ConfigurableAlgorithm,
            "custom": None  # Will import dynamically
        }
        
        if name == "custom":
            # Dynamically import custom algorithm
            try:
                from .custom_algorithm import MyCustomAlgorithm
                self.algorithm = MyCustomAlgorithm()
                self.algorithm_name = "custom"
            except ImportError:
                print("Custom algorithm not found, using config-driven")
                self.algorithm = ConfigurableAlgorithm()
                self.algorithm_name = "config_driven"
        elif name in algorithms:
            self.algorithm = algorithms[name]()
            self.algorithm_name = name
        else:
            self.algorithm = ConfigurableAlgorithm()
            self.algorithm_name = "config_driven"
    
    def reload_config(self) -> None:
        """Reload configuration without restarting"""
        if isinstance(self.algorithm, ConfigurableAlgorithm):
            self.algorithm.load_config()
    
    def get_score(self, drug_data: Dict) -> Dict:
        """Calculate score using current algorithm"""
        result = self.algorithm.calculate_score(drug_data)
        return {
            "total": result.total,
            "components": result.components,
            "reasoning": result.reasoning,
            "level": result.novelty_level
        }
    
    def get_algorithm_info(self) -> Dict:
        """Get current algorithm information"""
        return self.algorithm.get_algorithm_info()

# Singleton instance
algorithm_manager = AlgorithmManager()
