# 🐕 DrugHound Enterprise

**AI-Powered Drug Repurposing Discovery Platform**

DrugHound Enterprise mines live clinical trial data to identify understudied drugs with high repurposing potential.

## 🌐 Live Demo

[https://drughound.duranic.com](https://drughound.duranic.com)

## ✨ Features

### Current (v3.0)
- 🔍 **Real-time Drug Discovery** - Extracts drug candidates from ClinicalTrials.gov
- 📊 **Confidence Scoring** - Novelty + trial-based scoring (0-100%)
- 🖱️ **Clickable Drug Cards** - Modal popups with detailed information
- 🔬 **Clinical Trial Links** - Direct URLs to ClinicalTrials.gov
- 📄 **PubMed Integration** - External search links for publications
- 🎨 **Modern Dashboard** - Dark theme, responsive design
- 🌍 **Public HTTPS Access** - Cloudflare Tunnel for global access

### Coming Soon
- 🤖 **AI Copilot** - Natural language Q&A about drugs
- 📚 **Real Publication Counts** - Direct PubMed API integration
- 🕸️ **Knowledge Graph** - Interactive drug-disease network visualization
- 🧪 **ADMET Prediction** - Toxicity and property predictions

## 🚀 Quick Start

### Prerequisites
- Ubuntu 22.04 (or any Debian-based Linux)
- Python 3.10+
- Internet connection for ClinicalTrials.gov API

### One-Command Deployment (For Server Administrators)

`bash
# Clone the repository
git clone https://github.com/johncharron/DrugHound.git /opt/drughound
cd /opt/drughound

# Install dependencies
pip3 install fastapi uvicorn requests

# Run the application
python3 app.py
`

### For End Users (No Installation Required)

Simply open your web browser to: **https://drughound.duranic.com**

No software installation needed - works on any device with a browser!

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` or `/dashboard` | GET | Main web interface |
| `/api/discover?condition=cancer&limit=20` | GET | Discover drugs for a disease |
| `/api/drug/{drug_name}` | GET | Detailed drug information + trials |

### Example API Response

`json
{
  "condition": "cancer",
  "drugs": [
    {
      "name": "LBL-024",
      "novelty": 95,
      "confidence": 85,
      "trials": 5
    }
  ]
}
`

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| Web Server | Uvicorn |
| API Source | ClinicalTrials.gov |
| Deployment | Proxmox VM |
| Reverse Proxy | Cloudflare Tunnel (server-side only) |
| Process Manager | systemd |

## 📁 Project Structure

`/opt/drughound/
├── app.py              # Main FastAPI application
├── requirements.txt    # Python dependencies
└── README.md          # This file`

## 🔧 Maintenance Commands (Server Admin Only)

`bash
# Check service status
sudo systemctl status drughound

# View logs
sudo journalctl -u drughound -f

# Restart the service
sudo systemctl restart drughound

# Update application
cd /opt/drughound
git pull
sudo systemctl restart drughound
`

## 👥 For End Users

DrugHound is a web application - end users simply need:

1. A web browser (Chrome, Firefox, Safari, Edge)
2. Internet connection
3. The URL: **https://drughound.duranic.com**

**No software installation needed!** Just click and use.

## 🤝 Contributing

Contributions welcome! Please ensure:
1. Tests pass locally
2. Code follows existing patterns
3. API responses remain backward compatible

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- ClinicalTrials.gov for the API
- FastAPI for the web framework
- Cloudflare for tunneling

## 📞 Support

- GitHub Issues: [https://github.com/johncharron/DrugHound/issues](https://github.com/johncharron/DrugHound/issues)
- Live Demo: [https://drughound.duranic.com](https://drughound.duranic.com)

---

**Built with 🐕 for drug discovery researchers**
