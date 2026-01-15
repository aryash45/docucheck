"""HTML report generation module."""

def generate_report(claims, issues, external_checks, input_filename=""):
    """Generates a modern HTML report from analysis results."""
    
    claim_items = "".join(
        [f"<li><p>{c[''claim'']} <span class=''section''>({c.get(''section'', ''Unknown'')})</span></p></li>" for c in claims]
    )

    issue_items = "".join(
        [f"<li class=''issue''>{i}</li>" for i in issues]
    ) if issues else "<li class=''ok''> No inconsistencies found.</li>"

    external_items = ""
    valid, outdated, unknown = 0, 0, 0
    if not external_checks:
        external_items = "<p class=''no-checks''>No external checks performed.</p>"
    
    for e in external_checks:
        if isinstance(e, dict):
            status_class = "unknown"
            status_text = " Unknown"
            latest_info = e.get(''latest_info'', ''N/A'')
            
            if e.get("is_outdated") is True:
                status_class = "outdated"
                status_text = " Outdated"
                outdated += 1
            elif e.get("is_outdated") is False:
                status_class = "valid"
                status_text = " Valid"
                valid += 1
            else:
                unknown += 1
                
            external_items += f"""<div class="ext-card">
                <p><b>Claim:</b> {e.get(''claim'', ''N/A'')}</p>
                <div class="status-box {status_class}"><strong>{status_text}</strong></div>
                <p><b>Latest Info:</b> {latest_info}</p></div>"""

    total_checked = valid + outdated
    accuracy = 0.0 if total_checked == 0 else round((valid / total_checked) * 100, 1)
    progress_color = "#16a34a" if accuracy > 80 else "#f59e0b" if accuracy > 50 else "#e11d48"
        
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
    <title>DocuCheck Report</title><style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    background: #f8f9fa; color: #212529; margin: 0; padding: 24px; }}
    .container {{ max-width: 900px; margin: auto; }}
    h1 {{ text-align: center; font-size: 2.25rem; margin-bottom: 8px; }}
    .subtitle {{ text-align: center; color: #6c757d; margin-bottom: 32px; }}
    .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }}
    .summary-box {{ background: #fdfdff; border: 1px solid #dee2e6; padding: 20px; border-radius: 8px; text-align: center; }}
    .summary-box h3 {{ margin: 0 0 8px; color: #6c757d; font-weight: 500; }}
    .value {{ font-size: 2rem; font-weight: 700; }}
    .progress {{ background: #e9ecef; border-radius: 20px; height: 24px; overflow: hidden; }}
    .progress-bar {{ height: 100%; border-radius: 20px; background: {progress_color}; width: {accuracy}%; 
    text-align: center; color: white; font-weight: 600; line-height: 24px; }}
    ul {{ padding-left: 20px; }} li {{ margin-bottom: 12px; }}
    .section {{ color: #6c757d; font-size: 0.9em; font-style: italic; }}
    .issue {{ color: #e11d48; font-weight: 500; }} .ok {{ color: #16a34a; }}
    .ext-card {{ background: #f8f9fa; border-left: 5px solid #0d6efd; padding: 16px; margin-bottom: 16px; border-radius: 8px; }}
    .status-box {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; margin-bottom: 12px; }}
    .status-box.valid {{ background: #dcfce7; color: #15803d; }}
    .status-box.outdated {{ background: #fee2e2; color: #b91c1c; }}
    .status-box.unknown {{ background: #eef2ff; color: #4338ca; }}
    </style></head><body><div class="container">
    <h1> DocuCheck Report</h1>
    <p class="subtitle">Analysis for: <b>{input_filename}</b></p>
    <div class="card"><h2> Overall Summary</h2><div class="summary-grid">
    <div class="summary-box"><h3>Checked</h3><span class="value">{total_checked + unknown}</span></div>
    <div class="summary-box"><h3>Valid</h3><span class="value" style="color: #16a34a;">{valid}</span></div>
    <div class="summary-box"><h3>Outdated</h3><span class="value" style="color: #e11d48;">{outdated}</span></div>
    <div class="summary-box"><h3>Unknown</h3><span class="value">{unknown}</span></div>
    </div><div class="progress"><div class="progress-bar">{accuracy}% Valid</div></div></div>
    <div class="card"><h2> Internal Consistency</h2><ul>{issue_items}</ul></div>
    <div class="card"><h2> External Fact-Checks</h2>{external_items}</div>
    <div class="card"><h2> Claims ({len(claims)})</h2><ul>{claim_items}</ul></div>
    </div></body></html>"""
    return html
