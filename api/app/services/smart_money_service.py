"""
Cross-references three existing, independent signals - Congress trades,
Vanguard's and Munro Partners' latest 13F moves, and sector performance -
to find tickers where multiple "smart money" sources agree, and shows
whether that's happening in a sector that's currently hot or cold.

Deliberately does no new data fetching of its own beyond a lightweight
per-ticker sector lookup: everything else is existing services' data,
cross-referenced here instead of leaving an LLM to do it turn-by-turn
across several separate tool calls.
"""
import yfinance as yf
from app.services.congress_service import CongressService
from app.services.institution_service import InstitutionService
from app.services.finance import FinanceService

# yfinance's sector names (used elsewhere in this codebase - see
# FinanceService.get_sector_allocations) don't match the SPDR/GICS sector
# names FinanceService.get_sector_performance() uses - cross-walk between
# the two rather than assume they line up.
YFINANCE_TO_SPDR_SECTOR = {
    "Technology": "Technology",
    "Financial Services": "Financials",
    "Healthcare": "Healthcare",
    "Consumer Cyclical": "Consumer Discret.",
    "Communication Services": "Comm. Services",
    "Industrials": "Industrials",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Basic Materials": "Materials",
}


class SmartMoneyService:
    def __init__(self):
        self.congress_service = CongressService()
        self.institution_service = InstitutionService()
        self.finance_service = FinanceService()

    def _get_sector(self, ticker: str) -> str | None:
        # A lightweight direct lookup rather than FinanceService.get_company_info(),
        # which does far more work (ETF holdings, executives, etc.) than this needs.
        try:
            return yf.Ticker(ticker).info.get("sector")
        except Exception:
            return None

    def _build_signals(self) -> dict[str, dict]:
        """
        Shared by find_convergence() (market-wide scan) and get_ticker_signal()
        (one ticker) - both need the same three-source fetch and per-ticker
        tally, just sliced differently afterward.
        """
        congress = self.congress_service.get_recent_trades(limit=150)
        vanguard = self.institution_service.get_vanguard_trades(limit=30)
        munro = self.institution_service.get_munro_trades(limit=30)

        signals: dict[str, dict] = {}

        def sig(ticker: str) -> dict:
            return signals.setdefault(ticker, {"congress_buys": 0, "congress_sells": 0, "vanguard": None, "munro": None})

        if "error" not in congress:
            for t in congress.get("trades", []):
                ticker = t.get("ticker")
                trade_type = (t.get("type") or "").lower()
                if not ticker:
                    continue
                if "purchase" in trade_type:
                    sig(ticker)["congress_buys"] += 1
                elif "sale" in trade_type:
                    sig(ticker)["congress_sells"] += 1
                # "Exchange" and anything else isn't a clear directional signal - skip it.

        if "error" not in vanguard:
            for row in vanguard.get("top_buys", []):
                sig(row["ticker"])["vanguard"] = "buy"
            for row in vanguard.get("top_sells", []):
                sig(row["ticker"])["vanguard"] = "sell"

        if "error" not in munro:
            for row in munro.get("top_buys", []):
                sig(row["ticker"])["munro"] = "buy"
            for row in munro.get("top_sells", []):
                sig(row["ticker"])["munro"] = "sell"

        return signals

    def _classify(self, s: dict) -> tuple[list[str], list[str]]:
        buy_sources, sell_sources = [], []
        if s["congress_buys"] > s["congress_sells"] and s["congress_buys"] > 0:
            buy_sources.append("congress")
        elif s["congress_sells"] > s["congress_buys"] and s["congress_sells"] > 0:
            sell_sources.append("congress")
        if s["vanguard"] == "buy":
            buy_sources.append("vanguard")
        elif s["vanguard"] == "sell":
            sell_sources.append("vanguard")
        if s["munro"] == "buy":
            buy_sources.append("munro")
        elif s["munro"] == "sell":
            sell_sources.append("munro")
        return buy_sources, sell_sources

    def find_convergence(self, limit: int = 10) -> dict:
        signals = self._build_signals()
        sector_performance = self.finance_service.get_sector_performance()
        sector_perf_by_name = {s["name"]: s for s in sector_performance} if isinstance(sector_performance, list) else {}

        results = []
        for ticker, s in signals.items():
            buy_sources, sell_sources = self._classify(s)
            sources = buy_sources if len(buy_sources) >= len(sell_sources) else sell_sources
            if len(sources) < 2:
                continue  # need at least 2 independent sources agreeing to call it convergence
            results.append({
                "ticker": ticker,
                "direction": "buy" if sources is buy_sources else "sell",
                "sources": sources,
                "source_count": len(sources),
            })

        results.sort(key=lambda r: r["source_count"], reverse=True)
        results = results[:limit]

        for r in results:
            try:
                score = self.finance_service.get_future_leader_score(r["ticker"])
                r["future_leader_score"] = score["total_score"] if score else None
            except Exception:
                r["future_leader_score"] = None

            yf_sector = self._get_sector(r["ticker"])
            r["sector"] = yf_sector
            spdr_name = YFINANCE_TO_SPDR_SECTOR.get(yf_sector)
            r["sector_performance"] = sector_perf_by_name.get(spdr_name)

        return {
            "convergence": results,
            "sector_performance": sector_performance,
        }

    def get_ticker_signal(self, ticker: str) -> dict:
        """
        Cheap, single-ticker counterpart to find_convergence() - used by
        get_investment_verdict (agent/tools.py) so a full verdict doesn't
        need to run (and filter down) a whole market-wide scan just to
        check one name. Still does the same three-source fetch under the
        hood (that part isn't ticker-filterable at the source), but skips
        find_convergence's per-result enrichment, since the verdict tool
        already fetches Future Leader score itself.
        """
        signals = self._build_signals()
        s = signals.get(ticker)
        if not s:
            return {"ticker": ticker, "direction": None, "sources": [], "note": "No recent Congress or 13F activity found for this ticker."}

        buy_sources, sell_sources = self._classify(s)
        sources = buy_sources if len(buy_sources) >= len(sell_sources) else sell_sources
        if not sources:
            return {"ticker": ticker, "direction": None, "sources": [], "note": "No clear buy/sell signal from Congress or 13F sources."}

        return {
            "ticker": ticker,
            "direction": "buy" if sources is buy_sources else "sell",
            "sources": sources,
            "source_count": len(sources),
        }
