"""Multi-format report generation for DrugHound Enterprise."""

import os
from datetime import datetime
from jinja2 import Template
import pdfkit
import markdown
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

class ReportGenerator:
    def __init__(self, output_dir='reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(self, drugs_data: pd.DataFrame, analysis: dict) -> str:
        """Generate interactive HTML report."""
        template = Template('''
<!DOCTYPE html>
<html>
<head>
    <title>DrugHound Enterprise Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .high-novelty { background-color: #d4edda; }
        .medium-novelty { background-color: #fff3cd; }
        .chart-container { margin: 30px 0; }
    </style>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <h1>🐕 DrugHound Enterprise Report</h1>
    <p>Generated: {{ timestamp }}</p>
    <hr>
    
    <h2>Executive Summary</h2>
    <p>Total drugs analyzed: {{ total_drugs }}</p>
    <p>High-novelty candidates: {{ high_novelty_count }}</p>
    
    <h2>Top Novel Drug Candidates</h2>
    <div class="chart-container" id="novelty-chart"></div>
    
    </table>
        <thead>
            <tr><th>Drug</th><th>Novelty Score</th><th>Publications</th><th>Phase</th><th>Condition</th></tr>
        </thead>
        <tbody>
        {% for drug in top_drugs %}
        <tr class="{% if drug.novelty_score >= 80 %}high-novelty{% endif %}">
            <td>{{ drug.drug }}</td>
            <td>{{ drug.novelty_score }}</td>
            <td>{{ drug.pubmed_count }}</td>
            <td>{{ drug.phase }}</td>
            <td>{{ drug.condition }}</td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
    
    <h2>Repurposing Opportunities</h2>
    {% for drug, analysis in repurposing.items() %}
    <h3>{{ drug }}</h3>
    <ul>
    {% for opp in analysis.repurposing_opportunities %}
        <li><strong>{{ opp.condition }}</strong>: {{ opp.rationale }} (Evidence: {{ opp.confidence }})</li>
    {% endfor %}
    </ul>
    {% endfor %}
    
    <script>
        var data = [{
            x: {{ novelty_scores|tojson }},
            y: {{ drug_names|tojson }},
            type: 'bar',
            orientation: 'h',
            marker: {color: {{ novelty_colors|tojson }}}
        }];
        var layout = {title: 'Novelty Scores by Drug', xaxis: {title: 'Score'}};
        Plotly.newPlot('novelty-chart', data, layout);
    </script>
</body>
</html>
        ''')
        
        html_content = template.render(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_drugs=len(drugs_data),
            high_novelty_count=len(drugs_data[drugs_data['novelty_score'] >= 80]),
            top_drugs=drugs_data.head(20).to_dict('records'),
            repurposing=analysis,
            novelty_scores=drugs_data['novelty_score'].head(10).tolist(),
            drug_names=drugs_data['drug'].head(10).tolist(),
            novelty_colors=['#28a745' if s >= 80 else '#ffc107' if s >= 60 else '#dc3545' for s in drugs_data['novelty_score'].head(10).tolist()]
        )
        
        html_path = os.path.join(self.output_dir, 'drughound_report.html')
        with open(html_path, 'w') as f:
            f.write(html_content)
        return html_path
    
    def generate_pdf_report(self, html_path: str) -> str:
        """Convert HTML to PDF."""
        pdf_path = html_path.replace('.html', '.pdf')
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        pdfkit.from_file(html_path, pdf_path, options=options)
        return pdf_path
    
    def generate_excel_report(self, drugs_data: pd.DataFrame) -> str:
        """Generate Excel report with multiple sheets."""
        excel_path = os.path.join(self.output_dir, 'drughound_report.xlsx')
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            drugs_data.to_excel(writer, sheet_name='Top Drugs', index=False)
            
            # Summary statistics
            summary = pd.DataFrame({
                'Metric': ['Total Drugs', 'High Novelty (80+)', 'Medium Novelty (60-79)', 'Low Novelty (<60)'],
                'Value': [
                    len(drugs_data),
                    len(drugs_data[drugs_data['novelty_score'] >= 80]),
                    len(drugs_data[(drugs_data['novelty_score'] >= 60) & (drugs_data['novelty_score'] < 80)]),
                    len(drugs_data[drugs_data['novelty_score'] < 60])
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
        return excel_path
    
    def generate_json_export(self, drugs_data: pd.DataFrame, analysis: dict) -> str:
        """Export complete data as JSON."""
        import json
        json_path = os.path.join(self.output_dir, 'drughound_data.json')
        output = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'version': 'Enterprise',
                'total_drugs': len(drugs_data)
            },
            'drugs': drugs_data.to_dict('records'),
            'repurposing_analysis': analysis
        }
        with open(json_path, 'w') as f:
            json.dump(output, f, indent=2)
        return json_path

def create_visualization(drugs_data):
    """Create interactive visualizations."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=drugs_data['drug'].head(15),
        y=drugs_data['novelty_score'].head(15),
        marker_color=drugs_data['novelty_score'].head(15),
        text=drugs_data['novelty_score'].head(15),
        textposition='auto',
    ))
    fig.update_layout(
        title='Top 15 Drugs by Novelty Score',
        xaxis_title='Drug',
        yaxis_title='Novelty Score (0-100)',
        template='plotly_white'
    )
    return fig
