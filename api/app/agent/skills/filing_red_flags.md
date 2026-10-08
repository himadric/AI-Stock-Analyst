# SEC filing red-flag review

Use this before concluding a ticker is clean from a filings perspective, or when specifically asked to check for risk in its filings.

Search (`search_filings`) or read (`get_filing_text`) for each of these - don't skip to a verdict after checking just one:

- **Going concern language** - any explicit doubt about the company's ability to continue operating.
- **Material weakness in internal controls** - a disclosed failure in the company's own financial-reporting controls, not just generic risk-factor boilerplate.
- **Related-party transactions** - deals between the company and its own executives, board, or major shareholders, which can mask self-dealing.
- **Pending or recently settled litigation** - especially anything sized large enough relative to the company's market cap to matter.
- **Auditor changes** - a company switching auditors, especially on short notice or after a qualified opinion, is itself a signal worth naming.

Weigh findings together, not in isolation: generic risk-factor boilerplate (every 10-K has dozens of forward-looking "could harm our business" statements) isn't a red flag on its own - a *specific, disclosed instance* of one of the five items above is. One specific flag is worth noting with context; two or more together is worth weighing seriously into any buy/hold/sell framing.
