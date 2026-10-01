const API_BASE_URL = process.env.NODE_ENV === "production" 
    ? "/api" 
    : "http://127.0.0.1:8000/api";

// Short-lived token from /session-token that the FastAPI backend requires on every request.
// The promise is cached so parallel requests share one token fetch.
let tokenPromise: Promise<{ token: string; expiresAt: number }> | null = null;

async function getApiToken(forceRefresh = false): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    if (forceRefresh || !tokenPromise) {
        tokenPromise = null;
    } else {
        const cached = await tokenPromise.catch(() => null);
        if (!cached || cached.expiresAt - 60 <= now) tokenPromise = null;
    }

    if (!tokenPromise) {
        tokenPromise = fetch("/session-token", { cache: "no-store" }).then(async (res) => {
            if (res.status === 401 && typeof window !== "undefined") {
                window.location.href = "/login";
            }
            if (!res.ok) throw new Error("Not authenticated");
            return res.json();
        });
        tokenPromise.catch(() => { tokenPromise = null; });
    }

    return (await tokenPromise).token;
}

// fetch() against the FastAPI backend with the session token attached; retries once on 401.
async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
    const send = async (forceRefresh: boolean) => {
        const headers = new Headers(init.headers);
        headers.set("Authorization", `Bearer ${await getApiToken(forceRefresh)}`);
        return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
    };

    const res = await send(false);
    return res.status === 401 ? send(true) : res;
}

export async function fetchCompanyInfo(ticker: string) {
    const res = await apiFetch(`/finance/info/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch company info");
    return res.json();
}

export async function fetchPeerComparison(ticker: string) {
    const res = await apiFetch(`/finance/peers/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch peer data");
     // Returns list of metrics for peers
    return res.json();
}

export async function fetchMarketMap(type: "sector" | "factor" = "sector") {
    const res = await apiFetch(`/finance/market-map?map_type=${type}`);
    if (!res.ok) throw new Error("Failed to fetch market map");
    return res.json();
}

export async function fetchHistoricalMetrics(ticker: string) {
    const res = await apiFetch(`/finance/historical-metrics/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch historical metrics");
    return res.json();
}

export async function fetchStockHistory(ticker: string, period: string = "1y", interval: string = "1d") {
    const res = await apiFetch(`/finance/history/${ticker}?period=${period}&interval=${interval}`);
    if (!res.ok) throw new Error("Failed to fetch stock history");
    return res.json();
}

export async function fetchSECFilings(ticker: string) {
    const res = await apiFetch(`/sec/filings/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch filings");
    return res.json();
}

export async function analyzeFiling(ticker: string, url: string) {
    const res = await apiFetch(`/ai/analyze_filing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, url }),
    });
    if (!res.ok) throw new Error("Failed to analyze filing");
    return res.json();
}

// Indexes one filing into Pinecone for the chat agent's search_filings tool
// (semantic search across filings). See docs/ARCHITECTURE.md "RAG over SEC filings".
export async function ingestFiling(
    ticker: string,
    filing: { accessionNumber: string; form: string; filingDate: string; link: string }
) {
    const res = await apiFetch(`/agent/ingest_filing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, ...filing }),
    });
    if (!res.ok) throw new Error("Failed to ingest filing");
    return res.json();
}

export async function searchTickers(query: string) {
    const res = await apiFetch(`/sec/search?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error("Failed to search tickers");
    return res.json();
}

export async function fetchQuotes(symbols: string[]) {
    const symbolsStr = symbols.join(",");
    const res = await apiFetch(`/finance/quotes?symbols=${symbolsStr}`);
    if (!res.ok) throw new Error("Failed to fetch quotes");
    return res.json();
}

export async function fetchCompanyNews(ticker: string) {
    const res = await apiFetch(`/finance/news/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch news");
    return res.json();
}

export async function fetchFinancials(ticker: string) {
    const res = await apiFetch(`/finance/financials/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch financials");
    return res.json();
}

export async function fetchBalanceSheet(ticker: string) {
    const res = await apiFetch(`/finance/financials/balance-sheet/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch balance sheet");
    return res.json();
}

export async function fetchCashFlow(ticker: string) {
    const res = await apiFetch(`/finance/financials/cash-flow/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch cash flow");
    return res.json();
}

export async function fetchRatios(ticker: string) {
    const res = await apiFetch(`/finance/financials/ratios/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch ratios");
    return res.json();
}

export async function analyzeNews(ticker: string, news: any[]) {
    const res = await apiFetch(`/ai/analyze_news`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, news }),
    });
    if (!res.ok) throw new Error("Failed to analyze news");
    return res.json();
}

export async function analyzeChart(ticker: string, period: string, interval: string) {
    const res = await apiFetch(`/ai/analyze_chart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, period, interval }),
    });
    if (!res.ok) throw new Error("Failed to analyze chart");
    return res.json();
}

export async function fetchForecast(ticker: string) {
    const res = await apiFetch(`/finance/forecast/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch forecast");
    return res.json();
}

export async function fetchAnalystActions(ticker: string) {
    const res = await apiFetch(`/finance/forecast/actions/${ticker}`);
    if (!res.ok) throw new Error("Failed to fetch analyst actions");
    return res.json();
}

export async function fetchOwnership(ticker: string) {
    const res = await apiFetch(`/finance/ownership/${ticker}`);
    if (!res.ok) return null; // Return null on 404/500 to handle gracefully
    return res.json();
}

export async function fetchOwnershipDetails(ticker: string) {
    const res = await apiFetch(`/finance/ownership/details/${ticker}`);
    if (!res.ok) return { institutions: [], insiders: [] };
    return res.json();
}

export async function analyzeValuation(ticker: string) {
    const res = await apiFetch(`/ai/analyze_valuation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Valuation analysis failed");
    return res.json();
}

export async function analyzeRisk(ticker: string) {
    const res = await apiFetch(`/ai/analyze_risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Risk analysis failed");
    return res.json();
}

export async function analyzeEtf(ticker: string) {
    const res = await apiFetch(`/ai/analyze_etf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Failed to generate analysis");
    return res.json();
}

export async function fetchMacroData() {
    const res = await apiFetch(`/finance/macro`);
    if (!res.ok) throw new Error("Failed to fetch macro data");
    return res.json();
}

export async function fetchSectorPerformance() {
    const res = await apiFetch(`/finance/sectors`);
    if (!res.ok) throw new Error("Failed to fetch sector data");
    return res.json();
}

export async function analyzeMacroMarket(macro_data: any[], sector_data: any[]) {
    const res = await apiFetch(`/ai/analyze_macro_market`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ macro_data, sector_data }),
    });
    if (!res.ok) throw new Error("Macro analysis failed");
    return res.json();
}

export async function fetchFutureLeaderScore(ticker: string) {
    const res = await apiFetch(`/finance/score/${ticker}`);
    if (!res.ok) return null;
    return res.json();
}

export async function fetchRankings(category: string = "Small Cap", page: number = 1, limit: number = 10) {
    const res = await apiFetch(`/finance/rankings?category=${encodeURIComponent(category)}&page=${page}&limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch rankings");
    return res.json();
}

export async function fetchGovtRankings() {
    const res = await apiFetch(`/finance/govt/rankings`);
    if (!res.ok) throw new Error("Failed to fetch govt rankings");
    return res.json();
}

// Sentiment
export async function fetchSentiment(ticker: string) {
  const res = await apiFetch(`/sentiment/${ticker}`);
  if (!res.ok) {
     if (res.status === 404) return null;
     throw new Error("Failed to fetch sentiment");
  }
  return res.json();
}

// Vanguard Tracker
export async function fetchVanguardTrades(limit: number = 100) {
    const res = await apiFetch(`/vanguard/trades?limit=${limit}`);
    if (!res.ok) {
        throw new Error("Failed to fetch vanguard trades");
    }
    return res.json();
}

// Munro Partners Tracker
export async function fetchMunroTrades(limit: number = 100) {
    const res = await apiFetch(`/munro/trades?limit=${limit}`);
    if (!res.ok) {
        throw new Error("Failed to fetch munro trades");
    }
    return res.json();
}

// Congress Tracker
export async function fetchCongressTrades(limit: number = 100) {
    const res = await apiFetch(`/congress/trades?limit=${limit}`);
    if (!res.ok) {
        throw new Error("Failed to fetch congress trades");
    }
    return res.json();
}

// US House Tracker
export async function fetchHouseTrades() {
    const res = await apiFetch(`/house/trades`);
    if (!res.ok) {
        throw new Error("Failed to fetch house trades");
    }
    return res.json();
}

// US Senate Tracker
export async function fetchSenateTrades() {
    const res = await apiFetch(`/senate/trades`);
    if (!res.ok) {
        throw new Error("Failed to fetch senate trades");
    }
    return res.json();
}

// Simulation
// Simulation
export async function runSimulation(ticker: string, wacc: number, growth_rate_mean: number | null, simulations: number = 10000, bear_case: boolean = false) {
    const res = await apiFetch(`/simulation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            ticker, 
            wacc, 
            growth_rate_mean, 
            simulations,
            bear_case
        }),
    });
    if (!res.ok) throw new Error("Simulation failed");
    return res.json();
}

// Watchlist
export async function getWatchlist() {
    const res = await apiFetch(`/watchlist`);
    if (!res.ok) throw new Error("Failed to fetch watchlist");
    return res.json();
}

export async function addToWatchlist(ticker: string) {
    const res = await apiFetch(`/watchlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
    });
    if (!res.ok) throw new Error("Failed to add to watchlist");
    return res.json();
}

export async function removeFromWatchlist(ticker: string) {
    const res = await apiFetch(`/watchlist/${ticker}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to remove from watchlist");
    return res.json();
}

// Analyst agent (Path A — interactive chat only; see docs/ARCHITECTURE.md)
export interface AgentChatMessage {
    role: "user" | "assistant";
    content: string;
}

export type AgentEvent =
    | { type: "text"; text: string }
    | { type: "tool_start"; tool: string; args: Record<string, unknown> }
    | { type: "tool_end"; tool: string }
    | { type: "watchlist_proposal"; ticker: string; reason: string }
    | { type: "error"; message: string }
    | { type: "done" };

// Streams the agent's response as it's generated. Not a plain fetch: this
// endpoint returns text/event-stream, and EventSource can't send the
// Authorization header apiFetch attaches, so we parse the SSE stream by
// hand over a normal fetch instead.
export async function* streamAgentChat(messages: AgentChatMessage[]): AsyncGenerator<AgentEvent> {
    const res = await apiFetch(`/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
    });
    if (!res.ok || !res.body) throw new Error("Failed to reach the analyst agent");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIndex;
        while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
            const chunk = buffer.slice(0, sepIndex);
            buffer = buffer.slice(sepIndex + 2);
            const line = chunk.split("\n").find((l) => l.startsWith("data: "));
            if (line) {
                yield JSON.parse(line.slice(6)) as AgentEvent;
            }
        }
    }
}

