import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not found in environment.")
        
        # Use a standard, fast model
        self.model_name = "gemini-3-flash-preview"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    def generate_insight(self, prompt: str):
        if not self.api_key:
            return "AI service is not configured. Please check your .env file and API key."
        
        try:
            # Construct the payload for the REST API
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95
                }
            }

            # Use httpx for a synchronous call (or async if we were async, but this class is sync-ish for now)
            # Since the frontend calls this via FastAPI sync endpoints (def), using sync httpx.post is fine.
            # If the methods were `async def`, we'd use `httpx.AsyncClient`. 
            # The methods in `main.py` calling this might be async. Let's start with sync for compatibility.
            
            with httpx.Client() as client:
                response = client.post(self.api_url, json=payload, timeout=30.0)
                
                if response.status_code != 200:
                    return f"Error from AI Provider: {response.text}"
                
                data = response.json()
                # Parse the nested response structure
                # { "candidates": [ { "content": { "parts": [ { "text": "..." } ] } } ] }
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return text
                except (KeyError, IndexError):
                    return "Error: Unexpected response format from AI provider."
                    
        except Exception as e:
            return f"Error generating insight: {str(e)}"

    def summarize_filing(self, text: str, ticker: str):
        # Truncating is good, but 10k chars is roughly 2.5k tokens. 
        # Gemini 1.5 Flash can handle 1 million tokens, so you can actually 
        # send much more of the filing if you want!
        prompt = f"""
<role>
You are a Lead Equity Research Analyst specializing in {ticker}. Your goal is to provide high-signal, low-noise executive summaries of SEC filings for institutional investors.
</role>

<task>
Analyze the provided SEC filing excerpt for {ticker} and generate a structured summary. 
Focus on identifying "inflection points"—changes in language or numbers that indicate a shift in business health.
</task>

<requirements>
1. **Key Financial Shifts**: Identify specific YoY or QoQ changes in Revenue, Margins, or Cash Flow.
2. **Material Risks**: Focus on company-specific risks (e.g., "loss of a specific patent") rather than generic market risks (e.g., "the economy might slow down").
3. **Future Outlook**: Extract specific management guidance or "known trends and uncertainties" mentioned in the MD&A.
4. **Tone**: Professional, objective, and dense with information.
5. **Length**: Maximum 200 words.
</requirements>

<context_text>
{text}
</context_text>

<output_format>
**EXECUTIVE SUMMARY: {ticker}**
* **Financial Health:** [1-2 sentences on recent performance]
* **Top 3 Risks:** [Bullet points]
* **Strategic Outlook:** [1-2 sentences on management's stated direction]
</output_format>
"""
        return self.generate_insight(prompt)

    def analyze_news_sentiment(self, news_list: list, ticker: str):
        news_text = "\n".join([f"- {item.get('title')} ({item.get('publisher')})" for item in news_list])
        
        prompt = f"""
<role>
You are a Market Sentiment Analyst. 
</role>

<task>
Analyze the following recent news headlines for {ticker} and determine the overall market sentiment.
</task>

<requirements>
1. **Sentiment Score**: Determine if the sentiment is Bullish, Bearish, or Neutral.
2. **Key Drivers**: Briefly explain *why* based on the headlines (e.g., "Positive earnings report", "Regulatory lawsuit").
3. **Format**: Concise executive summary (max 150 words).
</requirements>

<news_headlines>
{news_text}
</news_headlines>
"""
        return self.generate_insight(prompt)

    def analyze_chart_data(self, ticker: str, period: str, interval: str, data: list):
        """
        Analyzes historical stock data to identify trends and key levels.
        """
        # Format data for the prompt (condense if too large, but 1.5 Flash can handle it)
        # We'll take the last 50-100 data points to keep it focused on recent action
        # or all of it if it's small.
        
        # summary of data
        data_str = "Date, Open, High, Low, Close, Volume\n"
        
        # Limit to last 60 bars to ensure high signal-to-noise for the prompt
        sliced_data = data[-60:] if len(data) > 60 else data
        
        for row in sliced_data:
            data_str += f"{row['date']}, {row['open']}, {row['high']}, {row['low']}, {row['close']}, {row['volume']}\n"
            
        prompt = f"""
<role>
You are an expert Technical Analyst and Quantitative Trader. Your goal is to analyze the provided price and volume data to identify trends, momentum shifts, and potential entry/exit zones.
</role>

<task>
Analyze the following time-series data for {ticker}. Provide a technical diagnostic focusing on price action, volume confirmation, and trend strength.
</task>

<data_points>
{data_str} 
</data_points>

<requirements>
1. **Trend Identification**: Is the asset in an accumulation, markup, distribution, or markdown phase? Use Moving Average logic (e.g., price vs. 50-day/200-day levels if provided).
2. **Volume Profiling**: Does volume confirm the price move? Look for "Buying/Selling Climaxes" or "Volume Divergence."
3. **Support & Resistance**: Based on the data, identify the most significant "congestion zones" or price floors/ceilings.
4. **Momentum Check**: Evaluate the speed of the recent move. Is it overextended or just starting?
5. **Actionable Summary**: Provide a "Bull Case," a "Bear Case," and a specific "Key Level to Watch."
</requirements>

<output_format>
### 📈 Technical Diagnostic: {ticker}
* **Primary Trend**: [Bullish/Bearish/Neutral]
* **Volume Sentiment**: [Confirming/Diverging]
* **Key Support**: [Price Level]
* **Key Resistance**: [Price Level]

**Analyst Commentary:**
[2-3 concise paragraphs of technical reasoning]

**Risk Management:**
* **Stop-Loss Area**: [Level]
* **Profit Target Area**: [Level]
</output_format>
"""        
        return self.generate_insight(prompt)

    def analyze_valuation(self, ticker: str, metrics: dict, income_statements: list):
        # Format income statements for context
        income_context = ""
        if income_statements:
            # Take last 4
            recent_is = income_statements[:4]
            income_context = "Recent Income Statements (last 4 quarters):\n"
            for stmt in recent_is:
                 # Assuming stmt is a dict-like or Series converted to dict
                 # If it's a DataFrame row, we might need to handle it.
                 # Let's assume passed as list of dicts.
                 income_context += f"{stmt}\n"
        
        # Prepare variables with defaults
        trailing_pe = metrics.get('pe_ratio', 'N/A')
        forward_pe = metrics.get('forward_pe', 'N/A')
        peg = metrics.get('peg_ratio', 'N/A')
        ps_ratio = metrics.get('price_to_sales', 'N/A')
        profit_margin = f"{metrics.get('profit_margin', 0)*100:.2f}%" if metrics.get('profit_margin') else 'N/A'
        roe = f"{metrics.get('roe', 0)*100:.2f}%" if metrics.get('roe') else 'N/A'
        fcf = metrics.get('free_cash_flow', 'N/A')
        debt_equity = metrics.get('debt_to_equity', 'N/A')
        current_ratio = metrics.get('current_ratio', 'N/A')
        beta = metrics.get('beta', 'N/A')
        
        # Approximate 52-week range if not passed directly, or expect it in metrics
        # For now, if metrics lacks range, we might skip or say N/A
        year_range = metrics.get('year_range', 'N/A') 
        industry_pe = "N/E" # As requested default or fetched if available

        prompt = f"""
<role>
You are a Senior Equity Research Analyst and Portfolio Manager. Your goal is to provide a high-conviction "Buy/Hold/Sell" framework for {ticker} by synthesizing valuation, balance sheet health, and market risk.
</role>

<task>
Perform a multi-dimensional financial audit of {ticker} using the provided data points.
</task>

<financial_data>
- Ticker: {ticker}
- Valuation: P/E (TTM): {trailing_pe}, Forward P/E: {forward_pe}, PEG Ratio: {peg}, P/S: {ps_ratio}
- Profitability: Net Margin: {profit_margin}, ROE: {roe}, Free Cash Flow: {fcf}
- Health: Debt-to-Equity: {debt_equity}, Current Ratio: {current_ratio}
- Risk: Beta: {beta}, 52-Week Range: {year_range}
- Context: Industry Average P/E: {industry_pe}
</financial_data>

<income_statement_context>
{income_context}
</income_statement_context>

<analysis_framework>
1. **Valuation Integrity**: Compare the PEG Ratio and Forward P/E. Is the market overpaying for growth, or is there a "margin of safety"?
2. **Operational Strength**: Does the ROE and Profit Margin suggest a strong competitive "moat"? 
3. **Solvency & Liquidity**: Analyze the Debt-to-Equity and Current Ratio. Can the company survive a high-interest-rate environment or a sudden revenue drop?
4. **Volatility Mapping**: Use the Beta and 52-week range to describe the "investor experience." Is this a "widows and orphans" stock (stable) or a high-volatility trade?
</analysis_framework>

<output_format>
## 📊 Investment Grade Report: {ticker}

### 1. Valuation Summary
* **Score**: [e.g., Fairly Valued / Overvalued / Undervalued]
* **Reasoning**: [1-2 sentences on P/E vs. Growth]

### 2. Financial Health Check
* **Liquidity**: [Strong/Adequate/Warning]
* **Leverage**: [Low/Moderate/High Debt]
* **Commentary**: [Note on FCF and Debt-to-Equity]

### 3. Risk & Volatility
* **Beta Profile**: [Interpretation of Beta value]
* **Key Risk Factor**: [The #1 thing that could crash this stock]

### 4. Final Analyst Verdict
**[Bull Case]** / **[Bear Case]**
[A 3-sentence summary of whether this stock belongs in a long-term portfolio.]
</output_format>
"""
        return self.generate_insight(prompt)

    def analyze_risk(self, ticker: str, metrics: dict, financials: list, ownership: dict):
        """
        Generates a forensic 'Red Flag' report focusing on earnings quality and governance.
        """
        # Format contexts
        fin_context = "Recent Financials (Revenue, Net Income, Cash Flow):\n"
        if financials:
             for f in financials[:4]: # Last 4 quarters
                 # Extract key metrics for forensic analysis
                 date = f.get('date', 'N/A')
                 rev = f.get('revenue', 0)
                 ni = f.get('net_income', 0)
                 # Note: financials from get_quarterly_financials is Income Statement. 
                 # We need to rely on what is passed. 
                 fin_context += f"Q ({date}): Rev={rev}, NetIncome={ni}\n"

        insider_context = "Insider Activity:\n"
        insiders = ownership.get('insiders', [])
        if insiders:
            for ins in insiders[:5]:
                insider_context += f"{ins.get('holder')} ({ins.get('position')}): {ins.get('shares')} shares\n"
        
        prompt = f"""
<role>
You are a Forensic Accountant and Short-Seller Research Analyst. Your job is to look past the "headline numbers" and identify hidden risks, accounting gimmicks, or governance red flags for {ticker}.
</role>

<task>
Conduct a "Red Flag" stress test on {ticker} using the available data. Be skeptical, critical, and direct.
</task>

<data_inputs>
Ticker: {ticker}
P/E Ratio: {metrics.get('pe_ratio')}
Profit Margin: {metrics.get('profit_margin')}
Debt/Equity: {metrics.get('debt_to_equity')}
Current Ratio: {metrics.get('current_ratio')}
Free Cash Flow: {metrics.get('free_cash_flow')}

{fin_context}

{insider_context}
</data_inputs>

<analysis_focus>
1. **Earnings Quality**: 
   - Ask: Is the company reporting profits (Net Income) but bleeding cash? (Compare Income vs Cash Flow if data permits).
   - Flag: High discrepancies between GAAP earnings and Free Cash Flow.
2. **Growth vs. Efficiency**:
   - Ask: Is revenue growing but margins shrinking? (Indicates "buying growth" or pricing pressure).
   - Ask: Is debt growing faster than assets?
3. **Governance & Insider Sentiment**:
   - Ask: Are insiders dumping stock? (Heavy selling is a massive red flag).
   - Flag: Any odd patterns in ownership.
4. **Solvency Stress**:
   - Ask: Can they pay their short-term bills? (Current Ratio < 1.0 is a warning).
   - Ask: Is leverage (Debt/Equity) dangerous for this sector?
</analysis_focus>

<output_format>
## 🚩 Forensic Risk Report: {ticker}

### 1. ⚠️ Key Red Flags (High Priority)
* **[Flag Name]**: [Description of the specific risk. Be blunt.]
* **[Flag Name]**: [Description]
* *(If no major flags found, state "No critical red flags detected in provided data.")*

### 2. Earnings Quality Audit
* **Verdict**: [High/Medium/Low Quality]
* **Observation**: [Analysis of Margins and Cash Flow alignment]

### 3. Governance Check
* **Insider Signal**: [Bullish/Bearish/Neutral]
* **Notes**: [Comment on recent insider activity]

### 4. Short-Seller Verdict
**[Risk Score: 1-10]** (1 = Safe, 10 = Toxic)
[Final summary: Is this a "Value Trap" or a clean company?]
</output_format>
"""
        return self.generate_insight(prompt)

    def analyze_macro_market(self, macro_data: list, sector_data: list):
        # Format Macro Data
        macro_text = ""
        for item in macro_data:
            val = f"{item['price']:.2f}%" if str(item.get('price')).replace('.','').isdigit() else str(item.get('price'))
            macro_text += f"- {item['name']} ({item['ticker']}): {val}\n"
            
        # Format Sector Data
        sector_text = ""
        # Sort by best performing for context
        sorted_sectors = sorted(sector_data, key=lambda x: x['change_percent'], reverse=True)
        for s in sorted_sectors:
            sector_text += f"- {s['name']}: {s['change_percent']:.2f}%\n"

        prompt = f"""
<role>
You are a Chief Market Strategist at a top-tier investment bank. Your job is to provide a "State of the Market" briefing to high-net-worth clients.
</role>

<task>
Synthesize the provided Economic Indicators and Sector Performance data into a cohesive market narrative. Connect the dots between macro conditions (e.g., inflation, rates) and where money is flowing in the market (e.g., sector rotation).
</task>

<data_context>
**Economic Indicators:**
{macro_text}

**Sector Performance (Today):**
{sector_text}
</data_context>

<requirements>
1. **The Big Picture**: Start with a single sentence characterizing the current market environment (e.g., "Risk-on rally driven by falling yields" or "Defensive rotation amidst growth fears").
2. **Sector Flow**: Identify which sectors are leading vs. lagging and *why* this makes sense given the macro backdrop. (e.g., "Tech leading suggests risk appetite," or "Utilities outperforming indicates defensive positioning").
3. **Macro Correlation**: Explicitly reference at least one macro data point (CPI, GDP, Fed Rate) to explain the sector movement.
4. **Outlook**: Conclude with a brief 1-sentence forward-looking statement.
5. **Tone**: Sophisticated, institutional, and high-signal.
</requirements>

<output_format>
**MARKET BRIEFING:**
* **Theme:** [1 sentence summary]
* **Sector Analysis:** [2-3 sentences connecting leaders/laggards to the theme]
* **Macro Driver:** [Insight on how GDP/CPI/Rates are influencing this price action]
* **Outlook:** [Forward-looking takeaway]
</output_format>
"""
    def analyze_etf_quality(self, ticker: str, data: dict):
        """
        Generates a 'Quality Core' ETF analysis based on specific user requirements.
        """
        # Unwrap data for prompt
        expense_ratio = data.get('expense_ratio', 'N/A')
        spread = data.get('bid_ask_spread', 'N/A')
        
        top_holdings = ""
        if data.get('holdings'):
            for h in data.get('holdings')[:10]:
                top_holdings += f"- {h['name']} ({h['symbol']}): {h['percent']}%\n"
        
        sector_breakdown = ""
        if data.get('sectors'):
            for s in data.get('sectors'):
                sector_breakdown += f"- {s['sector']}: {s['weight']*100:.2f}%\n"

        beta = data.get('beta', 'N/A')
        std_dev = data.get('std_dev', 'N/A')
        sharpe = data.get('sharpe', 'N/A')
        
        return_5y = data.get('return_5y', 'N/A')
        return_10y = data.get('return_10y', 'N/A')
        benchmark_return_5y = data.get('benchmark_return_5y', 'N/A')
        tracking_error = data.get('tracking_error', 'N/A')
        
        pe_ratio = data.get('pe_ratio', 'N/A')

        prompt = f"""
<role>
Senior Investment Strategist.
</role>

<objective>
Conduct a "Quality Core" analysis of {ticker} for a 10-year investment horizon.
</objective>

<data_context>
**Structural Efficiency:**
- Expense Ratio: {expense_ratio}
- 30-day Median Bid-Ask Spread (Proxy): {spread}

**Portfolio Composition:**
Top 10 Holdings:
{top_holdings}

Sub-Sector/Sector Breakdown:
{sector_breakdown}

**Risk Metrics:**
- Beta (vs S&P 500): {beta}
- Standard Deviation: {std_dev}
- Sharpe Ratio: {sharpe}

**Long-Term Performance:**
- 5-Year Annualized Return: {return_5y}
- 10-Year Annualized Return: {return_10y}
- Benchmark 5Y Return (Ref): {benchmark_return_5y}
- Tracking Error (Est): {tracking_error}

**Valuation:**
- P/E Ratio: {pe_ratio}
</data_context>

<required_analysis_sections>

**1. Structural Efficiency**
- Compare Expense Ratio to category norms.
- Evaluate Bid-Ask Spread for liquidity.

**2. Portfolio Composition (The Engine)**
- Analyze Top 10 Holdings concentration.
- Analyze sub-sector breakdown. Does this align with high-growth themes (e.g., AI, aging population)?

**3. Risk Metrics**
- Interpret Beta and Standard Deviation. 
- Does the Sharpe Ratio justify the risk?

**4. Long-Term Performance**
- Compare returns against valid benchmarks.
- Discuss Tracking Error if relevant.

</required_analysis_sections>

<deliverable>
**1. Summary Table**
Create a markdown table summarizing key metrics (Expense Ratio, Beta, Sharpe, 5Y Return, Verdict).

**2. Buy/Wait Verdict**
Provide a clear "BUY" or "WAIT" verdict based on current Sector Valuation (P/E Ratio) relative to historical norms and the quality analysis.
</deliverable>
"""
        return self.generate_insight(prompt)