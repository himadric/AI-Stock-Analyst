# Earnings review playbook

Use this when asked to assess how a ticker's latest quarter actually went - not just "did revenue grow," but whether it beat the market's own expectations.

1. Call `get_quarterly_financials` for the trend (at least the last 2-3 quarters, not just the latest one in isolation) - frame the latest quarter against both QoQ and YoY, since a single-quarter dip can be seasonal.
2. Call `get_analyst_actions` and look specifically for rating/price-target changes dated at or right after the most recent earnings date - that's the market's real-time verdict on the print, which matters more than the raw growth numbers alone.
3. Call `get_forecast` to see where consensus estimates and the price target sit now, versus what you'd expect from the raw numbers alone - a "good" quarter that still missed elevated expectations often shows up here as a flat or lowered target.
4. Call `get_company_news` for the earnings-call period specifically - look for management's own framing (guidance raised/cut, specific headwinds named) rather than just the headline revenue/EPS number.

Write the verdict in beat/miss terms relative to expectations (estimates, guidance, prior trend), not just whether the absolute numbers went up. A 15% revenue grower that guided for 25% and just did 12% is a miss, not a beat, even though growth is still double digits.
