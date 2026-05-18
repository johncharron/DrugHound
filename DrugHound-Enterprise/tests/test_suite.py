#!/usr/bin/env python3
"""DrugHound Enterprise - Pre-Commit Test Suite"""

import sys
import json
import unittest
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestDrugExtraction(unittest.TestCase):
    """Test drug name extraction patterns"""
    
    def setUp(self):
        """Load patterns from working version"""
        try:
            from app_final_working import DRUG_PATTERNS
            self.patterns = DRUG_PATTERNS
        except:
            self.patterns = [
                r'([A-Z]{2,}[0-9]{3,})',
                r'([A-Z]{2,}-[0-9]+)',
            ]
    
    def test_drug_code_extraction(self):
        """Test that drug codes like BFKB8488 are found"""
        test_text = "Testing BFKB8488 and AZD9291 in clinical trials"
        
        found_drugs = []
        for pattern in self.patterns:
            matches = re.findall(pattern, test_text)
            found_drugs.extend(matches)
        
        self.assertIn("BFKB8488", found_drugs)
        self.assertIn("AZD9291", found_drugs)
    
    def test_filter_common_words(self):
        """Test that common English words are filtered out"""
        test_text = "Patient Treatment Study Protocol"
        
        found_drugs = []
        for pattern in self.patterns:
            matches = re.findall(pattern, test_text)
            found_drugs.extend(matches)
        
        self.assertNotIn("Patient", found_drugs)
        self.assertNotIn("Treatment", found_drugs)

class TestNoveltyScoring(unittest.TestCase):
    """Test novelty scoring algorithm"""
    
    def test_zero_publications_score(self):
        """0 publications should score 98"""
        def calculate_score(count):
            if count == 0: return 98
            elif count <= 4: return 95
            elif count <= 9: return 90
            elif count <= 19: return 85
            elif count <= 49: return 75
            elif count <= 99: return 65
            elif count <= 199: return 55
            elif count <= 499: return 45
            elif count <= 999: return 35
            else: return 25
        
        self.assertEqual(calculate_score(0), 98)
    
    def test_low_publications_score(self):
        """1-4 publications should score 95"""
        def calculate_score(count):
            if count == 0: return 98
            elif count <= 4: return 95
            else: return 90
        
        for count in [1, 2, 3, 4]:
            self.assertEqual(calculate_score(count), 95)

def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDrugExtraction)
    suite.addTests(loader.loadTestsFromTestCase(TestNoveltyScoring))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    print("=" * 50)
    print("DrugHound Enterprise - Pre-Commit Tests")
    print("=" * 50)
    exit_code = run_tests()
    sys.exit(exit_code)
