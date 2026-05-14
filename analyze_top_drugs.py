#!/usr/bin/env python3
"""
Generate detailed repurposing analysis for top novel drugs
"""

import ollama
import csv

# Top novel drugs from our results
TOP_DRUGS = [
    {"name": "AL01211", "pubs": 2, "phase": "Phase 2", "condition": "Fabry Disease", "novelty": 95},
    {"name": "PYX-201", "pubs": 6, "phase": "Phase 1", "condition": "Solid Tumors", "novelty": 95},
    {"name": "Epetraborole", "pubs": 27, "phase": "Phase 2", "condition": "Bacterial Infections", "novelty": 80},
]

def analyze_drug(drug_info):
    """Generate repurposing analysis using Ollama."""
    prompt = f"""
    Drug: {drug_info['name']}
    Current Use: {drug_info['condition']}
    Clinical Phase: {drug_info['phase']}
    PubMed Publications: {drug_info['pubs']}
    Novelty Score: {drug_info['novelty']}/100
    
    As a pharmaceutical researcher, provide a concise repurposing analysis:
    
    1. PRIMARY MECHANISM (1 sentence)
    2. TOP 3 REPURPOSING OPPORTUNITIES (other conditions it could treat)
    3. WHY THIS DRUG IS NOVEL (1 sentence)
    4. NEXT RESEARCH STEP (1 recommendation)
    
    Format as bullet points.
    """
    
    print(f"\n🔬 Analyzing {drug_info['name']}...")
    print("-" * 50)
    
    response = ollama.generate(
        model="qwen2.5:7b",
        prompt=prompt,
        options={"temperature": 0.3, "num_predict": 500}
    )
    
    print(response['response'])
    print("-" * 50)
    
    return response['response']

# Run analysis for top drugs
print("="*60)
print("🐕 DrugHound - Deep Repurposing Analysis")
print("="*60)

for drug in TOP_DRUGS:
    analyze_drug(drug)

# Save to file
with open('output/repurposing_analysis.txt', 'w') as f:
    for drug in TOP_DRUGS:
        f.write(f"\n{'='*60}\n")
        f.write(f"DRUG: {drug['name']} (Novelty: {drug['novelty']}/100)\n")
        f.write(f"{'='*60}\n")
        # Re-run analysis for file
        result = analyze_drug(drug)
        f.write(result)
        f.write("\n")

print("\n✅ Deep analysis saved to: output/repurposing_analysis.txt")
