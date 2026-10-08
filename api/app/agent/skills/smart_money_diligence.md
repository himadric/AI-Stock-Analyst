# Interpreting smart-money signals

Use this when using Congress trades, Vanguard's or Munro's 13F activity, or `find_smart_money_convergence` to inform a view on a ticker - these sources are genuinely useful but easy to overread individually.

Keep these limits in mind:

- **A single Congressional trade disclosure is weak evidence on its own.** Disclosed position sizes are often small relative to the member's total portfolio, and disclosure lag means the trade may already be weeks old by the time it's visible.
- **13F filings (Vanguard, Munro) are up to 45 days stale** by the time they're public, and reflect a snapshot, not a live position - a holding shown as "bought" may already have been trimmed or exited since.
- **One source agreeing with your thesis isn't convergence.** Treat it as a mild supporting data point, not a signal to act on by itself.

What actually counts as a meaningful signal: **two or more independent sources (Congress, Vanguard, Munro) agreeing on the same direction, ideally alongside the ticker's sector also showing strength** (`find_smart_money_convergence` already checks all of this together). When you see that kind of agreement, say so plainly and name which sources agree. When you only have one weak source, say that plainly too, rather than framing it as more conclusive than it is.
