# AI Analyst

AI-powered stock and ETF research dashboard.

## Demo

[![Watch the AI Analyst demo](docs/media/demo-thumbnail.png)](docs/media/stock-analyst-demo.mp4)

*Click the image to watch the 7-minute walkthrough.*

## About

AI Analyst puts fundamental data, market data and AI-written analysis for a stock or ETF on one dashboard. Search for a ticker to see its key metrics, quarterly financial statements, price charts with technical indicators, analyst forecasts and ownership. You can also run a Monte Carlo DCF valuation, or have Google Gemini summarize SEC filings, flag valuation and risk red flags, and read price charts and macro conditions.

Beyond single stocks, the app tracks the wider market:

- **Market views:** an S&P 500 relative-strength heatmap, sector performance, and a macro dashboard of indices, rates, currencies and commodities.
- **Future Leader rankings:** small-, mid- and large-cap companies scored on growth efficiency, R&D intensity, scalability, valuation and ROIC.
- **Smart-money trackers:** US House and Senate stock trades, Vanguard and Munro Partners 13F moves, and book-to-bill ratios for government contractors.
- **Brand sentiment:** sentiment scored from news and YouTube reviews.
- **ETF analysis:** holdings, sector allocation, and an AI "Quality Core" assessment.

**Built with:** Next.js, React, TypeScript, Tailwind CSS and shadcn/ui on the frontend; Python FastAPI on the backend. Data comes from Yahoo Finance, SEC EDGAR, USAspending.gov and Financial Modeling Prep. Google Gemini writes the AI analysis, MongoDB stores precomputed data, and the app is deployed on Vercel.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it's built and [CLAUDE.md](CLAUDE.md) for local setup and development conventions.
