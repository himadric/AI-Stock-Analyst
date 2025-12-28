const API_BASE_URL = process.env.NODE_ENV === "production" 
    ? "/api" 
    : "http://localhost:8000/api";

export async function fetchCompanyInfo(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/info/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch company info");
    return res.json();
}

export async function fetchStockHistory(ticker: string, period: string = "1y", interval: string = "1d") {
    const res = await fetch(`${API_BASE_URL}/finance/history/${ticker}?period=${period}&interval=${interval}`);
    if (!res.ok) throw new Error("Failed to fetch stock history");
    return res.json();
}

export async function fetchSECFilings(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/sec/filings/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch filings");
    return res.json();
}

export async function analyzeFiling(ticker: string, url: string) {
    const res = await fetch(`${API_BASE_URL}/ai/analyze_filing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, url }),
    });
    if (!res.ok) throw new Error("Failed to analyze filing");
    return res.json();
}

export async function searchTickers(query: string) {
    const res = await fetch(`${API_BASE_URL}/sec/search?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error("Failed to search tickers");
    return res.json();
}

export async function fetchQuotes(symbols: string[]) {
    const symbolsStr = symbols.join(",");
    const res = await fetch(`${API_BASE_URL}/finance/quotes?symbols=${symbolsStr}`);
    if (!res.ok) throw new Error("Failed to fetch quotes");
    return res.json();
}

export async function fetchCompanyNews(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/news/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch news");
    return res.json();
}

export async function fetchFinancials(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/financials/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch financials");
    return res.json();
}

export async function fetchBalanceSheet(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/financials/balance-sheet/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch balance sheet");
    return res.json();
}

export async function fetchCashFlow(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/financials/cash-flow/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch cash flow");
    return res.json();
}

export async function fetchRatios(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/financials/ratios/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch ratios");
    return res.json();
}

export async function analyzeNews(ticker: string, news: any[]) {
    const res = await fetch(`${API_BASE_URL}/ai/analyze_news`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, news }),
    });
    if (!res.ok) throw new Error("Failed to analyze news");
    return res.json();
}

export async function analyzeChart(ticker: string, period: string, interval: string) {
    const res = await fetch(`${API_BASE_URL}/ai/analyze_chart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, period, interval }),
    });
    if (!res.ok) throw new Error("Failed to analyze chart");
    return res.json();
}

export async function fetchForecast(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/forecast/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch forecast");
    return res.json();
}

export async function fetchAnalystActions(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/forecast/actions/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch analyst actions");
    return res.json();
}

export async function fetchOwnership(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/ownership/${ticker}`);
    if (!res.ok) return null; // Return null on 404/500 to handle gracefully
    return res.json();
}

export async function fetchOwnershipDetails(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/finance/ownership/details/${ticker}`);
    if (!res.ok) return { institutions: [], insiders: [] };
    return res.json();
}

export async function analyzeValuation(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/ai/analyze_valuation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Valuation analysis failed");
    return res.json();
}

export async function analyzeRisk(ticker: string) {
    const res = await fetch(`${API_BASE_URL}/ai/analyze_risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Risk analysis failed");
    return res.json();
}
