def generate_report(claims, issues, external_checks, input_filename=""):
    """Generates a modern HTML report from the analysis results."""
    
    claim_items = "".join(
        [f"<li><p>{c['claim']} <span class='section'>({c.get('section', 'Unknown')})</span></p></li>" for c in claims]
    )

    # Internal issues
    issue_items = "".join(
        [f"<li class='issue'>{i}</li>" for i in issues]
    ) if issues else "<li class='ok'>✅ No major internal inconsistencies found.</li>"

    # Parse external checks
    external_items = ""
    valid, outdated, unknown = 0, 0, 0
    if not external_checks:
        external_items = "<p class='no-checks'>No external checks were performed.</p>"
    
    for e in external_checks:
        if isinstance(e, dict):
            status_class = "unknown"
            status_text = "❔ Unknown"
            latest_info = e.get('latest_info', 'N/A')
            
            if e.get("is_outdated") is True:
                status_class = "outdated"
                status_text = "❌ Outdated"
                latest_info = e.get('latest_info', 'No new info provided.')
                outdated += 1
            elif e.get("is_outdated") is False:
                status_class = "valid"
                status_text = "✅ Valid"
                latest_info = e.get('latest_info', 'Info appears current.')
                valid += 1
            else:
                unknown += 1 # Handle 'null' or missing key
                
            external_items += f"""
            <div class="ext-card">
                <p class="claim-text"><b>Claim:</b> {e.get('claim', 'Claim text missing')}</p>
                <div class="status-box {status_class}">
                    <strong>{status_text}</strong>
                </div>
                <p class="latest-info"><b>Latest Info:</b> {latest_info}</p>
            </div>
            """
        else:
            external_items += f"<div class='ext-card'><p>{e}</p></div>"

    # Calculate summary
    total_checked = valid + outdated
    accuracy = 0.0
    if total_checked > 0:
        accuracy = round((valid / total_checked) * 100, 1)

    progress_color = "#e11d48" # Red
    if accuracy > 80:
        progress_color = "#16a34a" # Green
    elif accuracy > 50:
        progress_color = "#f59e0b" # Amber
        
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DocuCheck Report</title>
        <style>
            :root {{
                --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                --bg-color: #f8f9fa; --card-bg: #ffffff; --text-color: #212529;
                --text-muted: #6c757d; --border-color: #dee2e6; --shadow: 0 4px 12px rgba(0,0,0,0.05);
                --radius: 12px; --color-green: #16a34a; --color-red: #e11d48; --color-amber: #f59e0b;
                --color-blue: #0d6efd;
            }}
            body {{ font-family: var(--font-sans); background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 24px; }}
            .container {{ max-width: 900px; margin: 20px auto; }}
            h1, h2 {{ color: #111827; font-weight: 600; }}
            h1 {{ text-align: center; font-size: 2.25rem; margin-bottom: 8px; }}
            .subtitle {{ text-align: center; font-size: 1.1rem; color: var(--text-muted); margin-top: 0; margin-bottom: 32px; }}
            .card {{ background-color: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--border-color); margin-bottom: 24px; padding: 24px; overflow: hidden; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; text-align: center; margin-bottom: 24px; }}
            .summary-box {{ background: #fdfdff; border: 1px solid var(--border-color); padding: 20px; border-radius: 8px; }}
            .summary-box h3 {{ margin: 0 0 8px 0; font-size: 1rem; color: var(--text-muted); font-weight: 500; }}
            .summary-box .value {{ font-size: 2rem; font-weight: 700; color: #111827; }}
            .progress {{ background: #e9ecef; border-radius: 20px; height: 24px; overflow: hidden; }}
            .progress-bar {{ height: 100%; border-radius: 20px; background-color: {progress_color}; width: {accuracy}%; text-align: center; color: white; font-size: 0.85rem; font-weight: 600; line-height: 24px; transition: width 0.5s ease-in-out; }}
            ul {{ padding-left: 20px; }} li {{ margin-bottom: 12px; line-height: 1.5; }}
            .section {{ color: var(--text-muted); font-size: 0.9em; font-style: italic; }}
            .issue {{ color: var(--color-red); font-weight: 500; }} .ok {{ color: var(--color-green); font-weight: 500; }}
            .no-checks {{ color: var(--text-muted); font-style: italic; }}
            .ext-card {{ background: var(--bg-color); border-radius: 8px; padding: 16px; margin-bottom: 16px; border-left: 5px solid var(--color-blue); }}
            .ext-card .claim-text {{ margin-top: 0; color: #333; line-height: 1.5; word-wrap: break-word; }}
            .status-box {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; margin-bottom: 12px; }}
            .status-box.valid {{ background-color: #dcfce7; color: #15803d; }}
            .status-box.outdated {{ background-color: #fee2e2; color: #b91c1c; }}
            .status-box.unknown {{ background-color: #eef2ff; color: #4338ca; }}
            .ext-card .latest-info {{ background: #fff; border: 1px dashed var(--border-color); padding: 12px; border-radius: 4px; margin-bottom: 0; font-size: 0.95rem; color: #333; word-wrap: break-word; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📑 DocuCheck Report</h1>
            <p class="subtitle">Analysis for: <b>{input_filename}</b></p>
            <div class="card">
                <h2>📊 Overall Summary</h2>
                <div class="summary-grid">
                    <div class="summary-box"><h3>Externally Checked</h3><span class="value">{total_checked + unknown}</span></div>
                    <div class="summary-box"><h3>Valid</h3><span class="value" style="color: var(--color-green);">{valid}</span></div>
                    <div class="summary-box"><h3>Outdated</h3><span class="value" style="color: var(--color-red);">{outdated}</span></div>
                    <div class="summary-box"><h3>Unknown</h3><span class="value" style="color: var(--text-muted);">{unknown}</span></div>
                </div>
                <div class="progress"><div class="progress-bar">{accuracy}% Valid</div></div>
            </div>
            <div class="card"><h2>⚖️ Internal Consistency</h2><ul>{issue_items}</ul></div>
            <div class="card"><h2>🌍 External Fact-Checks</h2>{external_items}</div>
            <div class="card"><h2>🔍 All Extracted Claims ({len(claims)})</h2><ul>{claim_items}</ul></div>
        </div>
    </body>
    </html>
    """
    return html