import numpy as np
import pandas as pd
import yfinance as yf
from functools import lru_cache
from datetime import datetime, timedelta

class SimulationService:
    @lru_cache(maxsize=32)
    def run_dcf_simulation(self, ticker: str, wacc: float = 0.09, growth_rate_mean: float = None, num_simulations: int = 10000, bear_case: bool = False):
        """
        Runs a Probabilistic DCF Simulation (Monte Carlo) to estimate Intrinsic Value.
        
        Args:
            ticker: Stock symbol
            wacc: Weighted Average Cost of Capital (Discount Rate)
            growth_rate_mean: Optional override for expected revenue growth rate
            num_simulations: Number of simulation paths
            
        Returns:
            dict: Simulation results including value distribution and metrics
        """
        try:
            stock = yf.Ticker(ticker)
            
            # 1. Fetch Key Financials
            income_stmt = stock.income_stmt
            cashflow = stock.cashflow
            balance_sheet = stock.balance_sheet
            
            # Check availability
            if income_stmt.empty or cashflow.empty:
                return {"error": "Insufficient financial data available"}
                
            # Extract data
            current_price = stock.fast_info.last_price
            shares_outstanding = stock.fast_info.shares
            
            # Net Debt = Total Debt - Cash & Equivalents
            total_debt = stock.info.get("totalDebt", 0)
            cash_equivalents = stock.info.get("totalCash", 0)
            net_debt = total_debt - cash_equivalents
            
            # Historical Revenue & FCF (Last 5 years max)
            # Transpose to get rows as years, sorted ascending
            rev_series = income_stmt.loc["Total Revenue"].iloc[:5].sort_index()
            # FCF might need calculation if not explicit key, but usually present in yF
            if "Free Cash Flow" in cashflow.index:
                fcf_series = cashflow.loc["Free Cash Flow"].iloc[:5].sort_index()
            else:
                # Fallback: OCF - CapEx
                ocf = cashflow.loc["Operating Cash Flow"] if "Operating Cash Flow" in cashflow.index else None
                capex = cashflow.loc["Capital Expenditure"] if "Capital Expenditure" in cashflow.index else None
                if ocf is not None and capex is not None:
                     fcf_series = (ocf + capex).iloc[:5].sort_index() # CapEx is usually negative
                else:
                    return {"error": "Could not calculate Free Cash Flow"}

            # Align dates
            common_dates = rev_series.index.intersection(fcf_series.index)
            rev_series = rev_series.loc[common_dates]
            fcf_series = fcf_series.loc[common_dates]
            
            if len(rev_series) < 2:
                 return {"error": "Not enough historical data points"}

            # 2. Historical Statistics
            # 2. Historical Statistics
            # Revenue Growth Rates
            # invalid_value_warning=False suppresses warnings for 0 division
            with np.errstate(invalid='ignore', divide='ignore'):
                rev_growth = rev_series.pct_change()
            
            # Clean infinite or NaN growth
            rev_growth = rev_growth.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(rev_growth) > 0:
                hist_growth_mean = float(rev_growth.mean())
                hist_growth_std = float(rev_growth.std()) if len(rev_growth) > 1 else 0.05
            else:
                # Default for pre-revenue or new companies
                hist_growth_mean = 0.10 
                hist_growth_std = 0.10

            # Data cleaning for extreme volatility (e.g. startup phase or covid)
            # Clip std dev to reasonable bounds for stability
            hist_growth_std = min(max(hist_growth_std, 0.02), 0.30) 
            hist_growth_mean = min(max(hist_growth_mean, -0.20), 0.50) # Cap historical mean between -20% and 50%
            
            # FCF Margins (FCF / Revenue)
            # Handle division by zero
            with np.errstate(invalid='ignore', divide='ignore'):
                 fcf_margins = fcf_series / rev_series
            
            fcf_margins = fcf_margins.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(fcf_margins) > 0:
                margin_mean = float(fcf_margins.mean())
                margin_std = float(fcf_margins.std()) if len(fcf_margins) > 1 else 0.02
            else:
                margin_mean = -0.10 # Assume burn
                margin_std = 0.05
                
            margin_std = min(max(margin_std, 0.01), 0.15) # Clip
            margin_mean = min(max(margin_mean, -0.99), 0.40) # Cap margins (-99% to 40%)
            
            # Use user input for growth if provided, else historical
            sim_growth_mean = growth_rate_mean if growth_rate_mean is not None else hist_growth_mean
            
            # --- BEAR CASE ADJUSTMENTS ---
            terminal_growth = 0.025 # 2.5% perpetuity growth (Base - Lowered to offset margin optimism)
            
            # Target Margin for Expansion (Industry Standard for Mature Tech/Services)
            TARGET_MARGIN = 0.18 
            
            if bear_case:
                # 1. Revenue Growth: Shift down by 1.5x StdDev (Recessionary)
                sim_growth_mean = sim_growth_mean - (1.5 * hist_growth_std)
                
                # 2. WACC: Increase by 200bps (Risk premium)
                wacc = wacc + 0.02
                
                # 3. Margins: Compress/Lower Target
                margin_mean = margin_mean - 0.05
                TARGET_MARGIN = 0.12 # Lower target in bear case
                
                # 4. Terminal Growth: Stagnation
                terminal_growth = 0.015
            
            # Cap/Floor safety checks after adjustment
            margin_mean = max(margin_mean, -0.99) 
            
            # 3. Monte Carlo Simulation (Vectorized)
            forecast_years = 10
            
            # Initialize arrays
            # Revenue Paths: [years, sims]
            # Start with latest revenue
            last_revenue = float(rev_series.iloc[-1])
            if last_revenue == 0:
                last_revenue = 1000000 # Assume $1M base for pre-revenue to allow math to work
            
            # Cap initial growth assumption to 25% max (Titan Cap) to prevent unrealistic projections
            sim_growth_mean = min(sim_growth_mean, 0.25)

            # Generate random Growth Rates: Normal Distribution with Linear Decay
            # Instead of constant mean, decay from sim_growth_mean to terminal_growth over forecast_years
            
            # Linear decay path for the mean growth rate
            growth_decay_means = np.linspace(sim_growth_mean, terminal_growth, forecast_years)
            
            # Margin Expansion Logic
            # If current margin < TARGET, expand linearly to TARGET over 10 years
            # If current margin >= TARGET, maintain current (capped logic already applied)
            if margin_mean < TARGET_MARGIN:
                margin_decay_means = np.linspace(margin_mean, TARGET_MARGIN, forecast_years)
            else:
                margin_decay_means = np.full(forecast_years, margin_mean)

            growth_rates = np.zeros((forecast_years, num_simulations))
            margins = np.zeros((forecast_years, num_simulations))
            
            for y in range(forecast_years):
                # Generate simulation step for year y using the decay/expansion means
                growth_rates[y] = np.random.normal(growth_decay_means[y], hist_growth_std, num_simulations)
                margins[y] = np.random.normal(margin_decay_means[y], margin_std, num_simulations)
            
            # Calculate Revenue projections
            msg_rev = np.zeros((forecast_years, num_simulations))
            current_rev = np.full(num_simulations, last_revenue)
            
            for y in range(forecast_years):
                current_rev = current_rev * (1 + growth_rates[y])
                msg_rev[y] = current_rev
                
            # Calculate FCF projections: Revenue * Margin
            projected_fcf = msg_rev * margins
            
            # 4. Discounting (WACC) to Present Value
            discount_factors = np.array([(1 + wacc) ** (i + 1) for i in range(forecast_years)]).reshape(-1, 1)
            pv_fcf = projected_fcf / discount_factors
            
            # Sum of PV of predicted FCFs
            sum_pv_fcf = pv_fcf.sum(axis=0)
            
            # 5. Terminal Value (Gordon Growth Model)
            # TV = (Final FCF * (1 + g_term)) / (WACC - g_term)
            # terminal_growth set above
            # Ensure WACC > terminal growth to assume convergence
            safe_wacc = max(wacc, terminal_growth + 0.01)
            
            final_fcf = projected_fcf[-1]
            tv = (final_fcf * (1 + terminal_growth)) / (safe_wacc - terminal_growth)
            
            # Discount TV
            pv_tv = tv / ((1 + wacc) ** forecast_years)
            
            # 6. Equity Value Calculation
            enterprise_value = sum_pv_fcf + pv_tv
            equity_value = enterprise_value - net_debt
            
            # Intrinsic Value per share
            intrinsic_values = equity_value / shares_outstanding
            
            # Handle negative values (bankrupt scenarios) or NaNs
            intrinsic_values = np.nan_to_num(intrinsic_values, nan=0.0)
            intrinsic_values = np.maximum(intrinsic_values, 0) # Assumes limited liability bottom at 0
            
            # 7. Metrics & Distribution
            expected_value = np.median(intrinsic_values)
            buy_zone_price = np.percentile(intrinsic_values, 25)
            prob_profit = np.mean(intrinsic_values > current_price) * 100
            
            # Max Drawdown Probability: % chance value is < 30% below current price
            drawdown_threshold = current_price * 0.70
            max_drawdown_prob = np.mean(intrinsic_values < drawdown_threshold) * 100
            
            # Create Histogram Buckets
            # Use numpy histogram
            counts, bin_edges = np.histogram(intrinsic_values, bins=50, density=True)
            
            histogram_data = []
            for i in range(len(counts)):
                val = (bin_edges[i] + bin_edges[i+1]) / 2
                freq = float(counts[i])
                if np.isnan(val) or np.isinf(val): val = 0.0
                if np.isnan(freq) or np.isinf(freq): freq = 0.0
                
                histogram_data.append({
                    "value": float(val), 
                    "frequency": freq 
                })
                
            return {
                "dcf_metrics": {
                    "current_price": float(current_price),
                    "expected_value": float(expected_value),
                    "buy_zone_price": float(buy_zone_price),
                    "win_probability": float(prob_profit),
                    "assumptions": {
                        "wacc": wacc,
                        "growth_mean": float(sim_growth_mean),
                        "growth_std": float(hist_growth_std),
                        "margin_mean": float(margin_mean),
                        "margin_std": float(margin_std),
                        "terminal_growth": terminal_growth
                    }
                },
                "max_drawdown_prob": float(max_drawdown_prob),
                "histogram": histogram_data,
                "ticker": ticker,
                "is_bear_case": bear_case
            }

        except Exception as e:
            print(f"DCF Simulation Error for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
