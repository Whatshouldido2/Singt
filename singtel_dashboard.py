import os
import smtplib
import requests
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model           = genai.GenerativeModel("gemini-2.0-flash")
NEWS_API_KEY    = os.environ.get("NEWS_API_KEY")
EMAIL_SENDER    = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD  = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
TODAY           = datetime.now().strftime("%d %B %Y")

# ── FETCH NEWS ───────────────────────────────────────────────────────────────
def fetch_news(query, max_articles=6):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": max_articles,
        "language": "en",
        "apiKey": NEWS_API_KEY,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        articles = response.json().get("articles", [])
        return articles
    except Exception as e:
        print(f"News fetch error: {e}")
        return []

def articles_to_text(articles):
    """Convert articles to plain text for feeding into Gemini."""
    if not articles:
        return "No recent articles found."
    text = ""
    for i, a in enumerate(articles, 1):
        title       = a.get("title", "")
        source      = a.get("source", {}).get("name", "")
        published   = a.get("publishedAt", "")[:10]
        description = a.get("description") or ""
        text += f"{i}. [{published}] {title} ({source})\n{description}\n\n"
    return text

def render_news_cards(articles):
    """Render news as HTML cards for the email."""
    if not articles:
        return "<p style='color:#888;'>No recent articles found.</p>"
    cards = ""
    for a in articles:
        title       = a.get("title", "No title")
        source      = a.get("source", {}).get("name", "Unknown")
        published   = a.get("publishedAt", "")[:10]
        description = a.get("description") or ""
        url         = a.get("url", "#")
        cards += f"""
        <div style="border-left:4px solid #4285F4; padding:10px 15px;
                    margin-bottom:12px; background:#fafafa; border-radius:4px;">
            <a href="{url}" style="font-weight:bold; color:#1a1a1a;
               text-decoration:none; font-size:14px;">{title}</a>
            <p style="margin:4px 0; font-size:12px; color:#888;">
                {source} &nbsp;|&nbsp; {published}
            </p>
            <p style="margin:4px 0; font-size:13px; color:#444;">{description}</p>
        </div>"""
    return cards

# ── GEMINI SECTION GENERATOR ─────────────────────────────────────────────────
def generate_section(section_name, news_context, prompt):
    """Feed news into Gemini and generate a specific dashboard section."""
    full_prompt = f"""
You are a senior business consultant advising on Singtel (Singapore Telecommunications Limited).
Today's date is {TODAY}.

Here is the latest news context for your analysis:
{news_context}

Based on this context and your knowledge of Singtel, generate the '{section_name}' section
for a consultant dashboard. {prompt}

Format your response as clean HTML (use <p>, <ul>, <li>, <strong>, <table> tags as appropriate).
Do not include ```html or ``` markers — return raw HTML only.
Be analytical, specific, and consultant-grade in your language. Avoid generic statements.
"""
    try:
        response = model.generate_content(full_prompt)
        # Strip any accidental markdown code fences Gemini might add
        content = response.text.strip()
        if content.startswith("```"):
            content = content.split("```")[-2] if "```" in content else content
            content = content.replace("html", "", 1).strip()
        return content
    except Exception as e:
        print(f"Gemini error for {section_name}: {e}")
        return f"<p>Unable to generate {section_name} section today. Error: {e}</p>"

# ── GENERATE ALL SECTIONS ────────────────────────────────────────────────────
def generate_all_sections():

    # Fetch news for different topics
    print("Fetching news...")
    singtel_news      = fetch_news("Singtel", 8)
    optus_news        = fetch_news("Optus Australia", 5)
    ncs_news          = fetch_news("NCS Singtel IT services", 4)
    nxera_news        = fetch_news("Nxera data centre Singapore", 4)
    airtel_news       = fetch_news("Bharti Airtel", 5)
    telco_sector_news = fetch_news("telco Asia 5G AI enterprise", 6)
    competitor_news   = fetch_news("Deutsche Telekom SoftBank Telstra telco strategy", 5)

    # Combine relevant news into context strings
    singtel_context  = articles_to_text(singtel_news + optus_news + ncs_news + nxera_news)
    regional_context = articles_to_text(airtel_news + singtel_news)
    sector_context   = articles_to_text(telco_sector_news + competitor_news)
    all_context      = articles_to_text(
        singtel_news + optus_news + ncs_news +
        nxera_news + airtel_news + telco_sector_news
    )

    print("Generating sections with Gemini 1.5 Pro...")

    # Section 1: Company Overview
    overview = generate_section(
        "Company Overview",
        singtel_context,
        """Provide a current snapshot of Singtel as a business. Cover its core segments
        (consumer, enterprise, digital infrastructure), key subsidiaries (Optus, NCS, Nxera),
        regional footprint, and any recent structural or leadership changes.
        Keep it factual and concise — 1 paragraph plus bullet points."""
    )

    # Section 2: Strategic Growth Plans
    growth = generate_section(
        "Strategic Growth Plans",
        singtel_context,
        """Analyse Singtel's current strategic priorities and growth plans based on the latest
        news. Cover their Singtel28 roadmap, data centre expansion, enterprise IT ambitions,
        5G monetisation strategy, and regional associate strategy.
        Highlight any updates or shifts in direction from recent news."""
    )

    # Section 3: Current Initiatives & Partnerships
    initiatives = generate_section(
        "Current Initiatives and Partnerships",
        singtel_context,
        """List and analyse Singtel's most active current initiatives and partnerships.
        Include technology partnerships (AI, cloud, network), government contracts,
        sustainability commitments, and any new deals announced recently.
        Be specific about what each initiative aims to achieve."""
    )

    # Section 4: Risk & Exposure Analysis
    risks = generate_section(
        "Risk and Exposure Analysis",
        all_context,
        """Identify and assess the key risks and exposures facing Singtel today.
        Consider operational risks (Optus), competitive risks, geopolitical risks
        (India, Indonesia), regulatory risks, technology risks, and financial risks.
        Present as an HTML table with columns: Risk, Severity (High/Medium/Low),
        and Consultant's Assessment. Be candid and specific."""
    )

    # Section 5: Competitive Benchmarking
    competitive = generate_section(
        "Competitive Benchmarking",
        sector_context,
        """Compare Singtel against its key global and regional competitors including
        Deutsche Telekom, SoftBank, Telstra, Bharti Airtel, and StarHub/M1.
        For each competitor, assess their current strategy and how Singtel compares.
        Present as an HTML table. Be honest about where Singtel leads and where it lags."""
    )

    # Section 6: Sector Trends
    trends = generate_section(
        "Sector Trends Relevant to Singtel",
        sector_context,
        """Summarise the 4-5 most important trends happening in the global telco and
        digital infrastructure sector right now that are directly relevant to Singtel.
        For each trend, explain what it means for Singtel specifically —
        is it an opportunity, a threat, or both?"""
    )

    # Section 7: Consultant's Evaluation
    evaluation = generate_section(
        "Consultant's Evaluation and Recommendations",
        all_context,
        """As a senior consultant, provide your evaluation of Singtel covering:
        1. What is Singtel's genuine USP today?
        2. Is Singtel sector-leading, a fast-follower, or falling behind globally?
        3. Feasibility assessment of their current strategy
        4. At least 5 specific, actionable recommendations for growth,
           partnerships, or risk mitigation
        5. Who should Singtel consider partnering with and why?
        Be direct, analytical, and specific. Avoid generic consulting language."""
    )

    return {
        "overview":     overview,
        "growth":       growth,
        "initiatives":  initiatives,
        "risks":        risks,
        "competitive":  competitive,
        "trends":       trends,
        "evaluation":   evaluation,
        "singtel_news": singtel_news + optus_news + ncs_news + nxera_news,
        "sector_news":  telco_sector_news + competitor_news,
    }

# ── BUILD HTML EMAIL ─────────────────────────────────────────────────────────
def build_html(sections):
    singtel_cards = render_news_cards(sections["singtel_news"])
    sector_cards  = render_news_cards(sections["sector_news"])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 820px;
                margin: 20px auto;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                background: #4285F4;
                color: white;
                padding: 24px 30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 22px;
            }}
            .header p {{
                margin: 4px 0 0;
                font-size: 13px;
                opacity: 0.85;
            }}
            .section {{
                padding: 22px 30px;
                border-bottom: 1px solid #eee;
            }}
            .section h2 {{
                font-size: 16px;
                color: #1a1a1a;
                border-left: 4px solid #4285F4;
                padding-left: 10px;
                margin-bottom: 14px;
            }}
            .section p, .section li {{
                font-size: 13px;
                color: #333;
                line-height: 1.7;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }}
            th {{
                background: #1a1a1a;
                color: white;
                padding: 8px 10px;
                text-align: left;
            }}
            td {{
                padding: 8px 10px;
                border-bottom: 1px solid #eee;
            }}
            tr:nth-child(even) td {{
                background: #f9f9f9;
            }}
            .badge-high {{
                background: #fde8e8;
                color: #c0392b;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            .badge-medium {{
                background: #fef9e7;
                color: #d68910;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            .badge-low {{
                background: #e9f7ef;
                color: #1e8449;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            .footer {{
                background: #1a1a1a;
                color: #aaa;
                padding: 16px 30px;
                font-size: 11px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
    <div class="container">

        <div class="header">
            <h1>&#128202; Singtel Consultant Dashboard</h1>
            <p>Daily Briefing &nbsp;|&nbsp; {TODAY} &nbsp;|&nbsp;
               Powered by Gemini 1.5 Pro &nbsp;|&nbsp; Consultant's Perspective</p>
        </div>

        <div class="section">
            <h2>1. Company Overview</h2>
            {sections['overview']}
        </div>

        <div class="section">
            <h2>2. Strategic Growth Plans</h2>
            {sections['growth']}
        </div>

        <div class="section">
            <h2>3. Current Initiatives &amp; Partnerships</h2>
            {sections['initiatives']}
        </div>

        <div class="section">
            <h2>4. Risk &amp; Exposure Analysis</h2>
            {sections['risks']}
        </div>

        <div class="section">
            <h2>5. Competitive Benchmarking</h2>
            {sections['competitive']}
        </div>

        <div class="section">
            <h2>6. Sector Trends Relevant to Singtel</h2>
            {sections['trends']}
        </div>

        <div class="section">
            <h2>7. Consultant's Evaluation &amp; Recommendations</h2>
            {sections['evaluation']}
        </div>

        <div class="section">
            <h2>8. Latest Singtel News</h2>
            {singtel_cards}
        </div>

        <div class="section">
            <h2>9. Sector &amp; Competitor News</h2>
            {sector_cards}
        </div>

        <div class="footer">
            Generated automatically on {TODAY} via GitHub Actions &nbsp;|&nbsp;
            Powered by Google Gemini 1.5 Pro + NewsAPI &nbsp;|&nbsp;
            For consultant use only — verify all facts before client use
        </div>

    </div>
    </body>
    </html>
    """
    return html

# ── SEND EMAIL ───────────────────────────────────────────────────────────────
def send_email(html_content):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Singtel Consultant Dashboard — {TODAY}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        print(f"Email sent successfully to {EMAIL_RECIPIENT}")
    except Exception as e:
        print(f"Email error: {e}")
        raise

# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Starting Singtel Dashboard generation for {TODAY}...")
    sections = generate_all_sections()
    print("Building HTML email...")
    html = build_html(sections)
    print("Sending email...")
    send_email(html)
    print("Done.")
