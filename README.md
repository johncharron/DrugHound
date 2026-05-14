[readme.txt](https://github.com/user-attachments/files/18402575/readme.txt)

## 🔑 API Key Setup

**Important:** DrugHound requires a PubMed API key for higher rate limits.

### Getting Your API Key

1. Create an account at https://www.ncbi.nlm.nih.gov/account/
2. Go to Account Settings → API Key Management
3. Generate a new API key (it's free)

### Setting Up Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your API key
nano .env
```

### Example .env file

```
PUBMED_API_KEY=your_actual_api_key_here
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_URL=http://localhost:11434/api/generate
REQUESTS_PER_SECOND=9
```

### Running DrugHound

```bash
source venv/bin/activate
python src/main.py
```

**Security Note:** The .env file is gitignored and will never be committed to the repository. Your API key stays local.

## 📊 Output Files

| File | Description |
|------|-------------|
| output/top_novel_drugs.csv | Ranked drugs with novelty scores |
| output/discovery_results.json | Complete JSON data |
| logs/discovery.log | Execution log |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- ClinicalTrials.gov API
- PubMed E-utilities
- Ollama and qwen2.5-coder

---

Built with 🐕 by John Charron
