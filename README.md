# 🐕 DrugHound

**DrugHound** is an AI-powered drug repurposing discovery engine that identifies understudied drugs with high potential for new therapeutic applications.

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ollama](https://img.shields.io/badge/ollama-qwen2.5--coder-orange.svg)](https://ollama.ai)

## 🎯 What It Does

DrugHound mines clinical trial data and scientific literature to find **novel drug repurposing opportunities** - existing drugs that could treat different diseases than originally intended.

## 🔍 How It Works

1. Search ClinicalTrials.gov for recent studies
2. Extract drug names from interventions
3. Count PubMed publications (fewer = more novel)
4. Calculate novelty score (0-100)
5. Generate AI-powered repurposing analysis

## 📊 Latest Results

Top novel drug candidates identified:

| Drug | Novelty Score | Publications | Phase | Primary Condition |
|------|--------------|--------------|-------|-------------------|
| PYX-201 | 95 (VERY HIGH) | 6 | Phase 1 | Solid Tumors |
| AL01211 | 95 (VERY HIGH) | 2 | Phase 2 | Fabry Disease |
| Epetraborole | 80 (HIGH) | 27 | Phase 2 | Bacterial Infections |

### Repurposing Insights

**AL01211** (2 publications) shows potential for:
- Renal Diseases (chronic kidney disease)
- Cardiovascular Disorders
- Neurological Conditions

**PYX-201** (6 publications) shows potential for:
- Autoimmune Diseases
- Neurodegenerative Disorders
- Infectious Diseases

## 🚀 Quick Start

### Prerequisites

Install Ollama and pull the model:

curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b
text


### Installation

git clone https://github.com/johncharron/DrugHound.git
cd DrugHound
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/drughound.py
text


### Configuration

Copy the environment template and add your PubMed API key:

cp .env.template .env
nano .env
text


## 📁 Project Structure

DrugHound/
├── src/
│ ├── drughound.py # Main discovery engine
│ └── config.py # Configuration
├── analyze_top_drugs.py # LLM repurposing analysis
├── output/ # Results (CSV, analysis)
├── requirements.txt # Dependencies
└── README.md # This file
text


## 📊 Output Files

| File | Description |
|------|-------------|
| output/top_novel_drugs.csv | Ranked drugs with novelty scores |
| output/repurposing_analysis.txt | AI-generated repurposing insights |

## 🔬 Generating Deep Analysis

Run the LLM-powered repurposing analysis:

python analyze_top_drugs.py
text


## 📚 Data Sources

- ClinicalTrials.gov - U.S. National Library of Medicine
- PubMed - NCBI/NIH database
- Ollama - Local LLM (qwen2.5-coder:7b)

## 🧠 Novelty Scoring

Drugs are scored 0-100 based on:
- Publication count (0-50 pts): Fewer publications = higher score
- Clinical phase (0-30 pts): Earlier phase = higher score
- Rarity (0-20 pts): Rare diseases = bonus

| Score | Level | Meaning |
|-------|-------|---------|
| 90-100 | VERY HIGH | Understudied, prime repurposing candidate |
| 70-89 | HIGH | Emerging research opportunity |
| 50-69 | MODERATE | Some existing research |
| Below 50 | LOW | Well-studied, less novel |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ⚖️ Disclaimer

DrugHound is a research tool for generating hypotheses. All findings should be:
- Verified with primary literature
- Validated through proper scientific methods
- Reviewed by medical professionals

The AI-generated analyses are for informational purposes only.

## 📝 License

MIT License

## 🙏 Acknowledgments

- ClinicalTrials.gov for open trial data
- PubMed/NCBI for literature access
- Ollama for local LLM capabilities

---

Built with 🐕 by John Charron

Star this repository if you find it useful!
