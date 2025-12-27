"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";

interface FinancialData {
  date: string;
  revenue: number;
  cost_of_revenue: number;
  gross_profit: number;
  research_development: number;
  selling_general_admin: number;
  operating_expense: number;
  operating_income: number;
  total_expenses: number;
  interest_expense: number;
  pretax_income: number;
  tax_provision: number;
  net_income: number;
  basic_eps: number;
  diluted_eps: number;
  shares_basic: number;
  shares_diluted: number;
}

interface FinancialTableProps {
  data: any[];
  type: "income" | "balance" | "cash" | "ratios";
}

export function FinancialTable({ data, type }: FinancialTableProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6 text-center text-muted-foreground">
          No data available for {type}.
        </CardContent>
      </Card>
    );
  }

  // We want to show the last 4 quarters (reversed for display Newest -> Oldest)
  const displayData = [...data].reverse().slice(0, 4);

  const formatCurrency = (value: number) => {
    if (value === 0 || value === undefined) return "-";
    const inMillions = value / 1e6;
    return inMillions.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  };
  
  const formatNumber = (value: number, decimals = 2) => {
      if (value === 0 || value === undefined) return "-";
      return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };
  
  const formatPercent = (value: number) => {
      if (value === 0 || value === undefined) return "-";
      return `${value.toFixed(2)}%`;
  };

  // Row definitions
  const incomeRows = [
    { label: "Revenue", key: "revenue", bold: true },
    { label: "Cost of Revenue", key: "cost_of_revenue" },
    { label: "Gross Profit", key: "gross_profit", bold: true },
    { label: "Research & Development", key: "research_development" },
    { label: "SG&A", key: "selling_general_admin" },
    { label: "Operating Expenses", key: "operating_expense" },
    { label: "Operating Income", key: "operating_income", bold: true },
    { label: "Interest Expense", key: "interest_expense" },
    { label: "Pretax Income", key: "pretax_income" },
    { label: "Tax Provision", key: "tax_provision" },
    { label: "Net Income", key: "net_income", bold: true },
    { label: "Basic EPS", key: "basic_eps", format: "raw" },
    { label: "Diluted EPS", key: "diluted_eps", format: "raw" },
  ];

  const balanceRows = [
    { label: "Cash & Equivalents", key: "cash_equivalents" },
    { label: "Short-Term Investments", key: "short_term_investments" },
    { label: "Inventory", key: "inventory" },
    { label: "Accounts Receivable", key: "accounts_receivable" },
    { label: "Total Current Assets", key: "total_current_assets", bold: true },
    { label: "Total Assets", key: "total_assets", bold: true },
    { label: "Accounts Payable", key: "accounts_payable" },
    { label: "Current Liabilities", key: "total_current_liabilities" },
    { label: "Total Liabilities", key: "total_liabilities", bold: true },
    { label: "Working Capital", key: "working_capital" },
    { label: "Total Equity", key: "total_equity", bold: true },
  ];

  const cashRows = [
    { label: "Net Income", key: "net_income", bold: true },
    { label: "Depreciation & Amortization", key: "depreciation_amortization" },
    { label: "Stock-Based Compensation", key: "stock_based_compensation" },
    { label: "Change in Working Capital", key: "change_in_working_capital" },
    { label: "Operating Cash Flow", key: "operating_cash_flow", bold: true },
    { label: "Capital Expenditures", key: "capital_expenditure" },
    { label: "Investing Cash Flow", key: "investing_cash_flow", bold: true },
    { label: "Debt Repayment / Issuance", key: "debt_repayment" },
    { label: "Share Issuance / Repurchase", key: "common_stock_issued" },
    { label: "Dividends Paid", key: "dividend_paid" },
    { label: "Financing Cash Flow", key: "financing_cash_flow", bold: true },
    { label: "Net Change in Cash", key: "net_change_in_cash", bold: true },
    { label: "Free Cash Flow", key: "free_cash_flow", bold: true },
  ];
  
  const ratioRows = [
      { label: "Market Cap", key: "market_cap", format: "currency", bold: true },
      { label: "Enterprise Value", key: "enterprise_value", format: "currency" },
      { label: "Close Price", key: "price", format: "raw" },
      
      { label: "PE Ratio (Quarterly)", key: "pe_ratio", format: "raw" },
      { label: "PS Ratio", key: "ps_ratio", format: "raw" },
      { label: "PB Ratio", key: "pb_ratio", format: "raw" },
      { label: "EV / EBITDA", key: "ev_ebitda", format: "raw" },
      { label: "EV / Sales", key: "ev_sales", format: "raw" },
      
      { label: "Gross Margin", key: "gross_margin", format: "percent" },
      { label: "Operating Margin", key: "operating_margin", format: "percent" },
      { label: "Net Margin", key: "net_margin", format: "percent" },
      { label: "ROE", key: "return_on_equity", format: "percent" },
      { label: "ROA", key: "return_on_assets", format: "percent" },
      
      { label: "Debt / Equity", key: "debt_to_equity", format: "raw" },
      { label: "Current Ratio", key: "current_ratio", format: "raw" },
      { label: "FCF Yield", key: "fcf_yield", format: "percent" },
  ];

  let rows = incomeRows;
  let title = "Income Statement";

  if (type === 'balance') {
      rows = balanceRows;
      title = "Balance Sheet";
  } else if (type === 'cash') {
      rows = cashRows;
      title = "Cash Flow Statement";
  } else if (type === 'ratios') {
      rows = ratioRows;
      title = "valuation & Ratios";
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Financials in millions. Last 4 Quarters.</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Breakdown</TableHead>
              {displayData.map((d) => (
                <TableHead key={d.date} className="text-right">
                  {new Date(d.date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.label} className={row.bold ? "font-bold" : ""}>
                <TableCell>{row.label}</TableCell>
                {displayData.map((d) => {
                   const val = d[row.key];
                   
                   let displayVal = "-";
                   if (row.format === 'currency') {
                       displayVal = formatCurrency(val as number);
                   } else if (row.format === 'percent') {
                       displayVal = formatPercent(val as number);
                   } else if (row.format === 'raw' || !row.format) {
                        // Default logic for other tables was raw for EPS, currency for others
                        // But here we are explicit.
                        // For legacy support of other tables if they don't have format:
                        if (type !== 'ratios') {
                             // Legacy logic
                             if (row.key.includes('eps')) displayVal = (typeof val === 'number' ? val.toFixed(2) : "-");
                             else displayVal = formatCurrency(val as number);
                        } else {
                            displayVal = typeof val === 'number' ? val.toFixed(2) : "-";
                        }
                   }
                   
                   return (
                       <TableCell key={`${d.date}-${row.key}`} className="text-right">
                           {displayVal}
                       </TableCell>
                   );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
