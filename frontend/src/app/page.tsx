"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowUpRight, FileText, Loader2, Sparkles, AlertTriangle } from "lucide-react";
import { fetchCompanyInfo, fetchSECFilings, analyzeFiling, fetchCompanyNews, analyzeNews, fetchFinancials, analyzeValuation, analyzeRisk } from "@/lib/api";
import { FinancialCharts } from "@/components/dashboard/financial-charts";

const METRIC_TOOLTIPS = {
    "Market Cap": "The \"Total Value\" of the company. It helps you categorize the stock as a Mega-cap (huge/stable), Mid-cap, or Small-cap (growth potential but riskier).",
    "Trailing P/E": "Compares the stock price to actual profits from the last year. It tells you how many \"years\" of current earnings it would take to pay back the stock price.",
    "Forward P/E": "Similar to P/E, but uses estimated future earnings. If this is lower than the Trailing P/E, it signals that analysts expect the company's profits to grow.",
    "PEG Ratio": "A powerful \"growth-adjusted\" P/E. It tells you if a high P/E is justified by a high growth rate. Generally, a value under 1.0 is considered \"undervalued\" for its growth.",
    "P/S Ratio": "Compares price to total sales (revenue). This is the \"gold standard\" for evaluating young companies that aren't profitable yet.",
    "Profit Margin": "The percentage of every dollar earned that is kept as profit. It measures the efficiency and \"pricing power\" of the company.",
    "ROE": "Measures how much profit the company generates with the money shareholders have invested. High ROE often indicates a superior management team and a competitive \"moat\".",
    "Free Cash Flow": "The actual cash \"left over\" after all bills and equipment upgrades are paid. This is the cash used to pay dividends or buy back shares.",
    "Debt/Equity": "Shows how much the company relies on borrowed money vs. its own money. High debt can be a major risk during recessions or high-interest-rate periods.",
    "Current Ratio": "Measures if the company has enough short-term assets (cash, inventory) to pay its short-term debts. A ratio above 2.0 is typically considered very safe.",
    "Beta": "Measures volatility relative to the overall market (S&P 500). Beta = 1.0: Moves exactly like the market. Beta > 1.0: Higher risk, higher potential reward. Beta < 1.0: More stable.",
    "Dividend Yield": "The percentage of the stock price returned to you in cash annually. It is a key metric for \"Income Investors\" seeking steady payments."
};

function DashboardContent() {
    const searchParams = useSearchParams();
    // Default to AAPL if no ticker logic provided
    const ticker = searchParams.get("ticker") || "AAPL";
    
    const [companyInfo, setCompanyInfo] = useState<any>(null);
    const [filings, setFilings] = useState<any[]>([]);
    const [news, setNews] = useState<any[]>([]);
    const [financials, setFinancials] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    
    // AI Analysis State
    const [analyzing, setAnalyzing] = useState<string | null>(null); // 'filing' or 'news'
    const [analysisResult, setAnalysisResult] = useState<string | null>(null);

    useEffect(() => {
        setAnalysisResult(null); // Clear previous analysis on ticker change
        loadData();
    }, [ticker]);

    async function loadData() {
        setLoading(true);
        setCompanyInfo(null); // Clear previous info while loading
        try {
            const [info, secData, newsData, finData] = await Promise.all([
                fetchCompanyInfo(ticker),
                fetchSECFilings(ticker),
                fetchCompanyNews(ticker),
                fetchFinancials(ticker)
            ]);
            setCompanyInfo(info);
            setFilings(secData);
            setNews(newsData);
            setFinancials(finData);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    async function handleAnalyzeFiling(url: string) {
        setAnalyzing(url);
        setAnalysisResult(null);
        try {
            const res = await analyzeFiling(ticker, url);
            setAnalysisResult(res.summary);
        } catch (e) {
            console.error(e);
            setAnalysisResult("Failed to generate analysis.");
        } finally {
            setAnalyzing(null);
        }
    }

    async function handleAnalyzeNews() {
        setAnalyzing('news');
        setAnalysisResult(null);
        try {
            const res = await analyzeNews(ticker, news);
            setAnalysisResult(res.analysis);
        } catch (e) {
            console.error(e);
            setAnalysisResult("Failed to generate news sentiment analysis.");
        } finally {
            setAnalyzing(null);
        }
    }

    async function handleAnalyzeValuation() {
        setAnalyzing('valuation');
        setAnalysisResult(null);
        try {
            const res = await analyzeValuation(ticker);
            setAnalysisResult(res.analysis);
        } catch (e) {
            console.error(e);
            setAnalysisResult("Failed to generate valuation report.");
        } finally {
            setAnalyzing(null);
        }
    }

    async function handleAnalyzeRisk() {
        setAnalyzing('risk');
        setAnalysisResult(null);
        try {
            const res = await analyzeRisk(ticker);
            setAnalysisResult(res.analysis);
        } catch (e) {
            console.error(e);
            setAnalysisResult("Failed to generate risk report.");
        } finally {
            setAnalyzing(null);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{ticker} Analysis</h2>
                    <p className="text-muted-foreground">Real-time market insights and AI predictions</p>
                </div>
            </div>

            {loading || !companyInfo ? (
                <div className="flex w-full items-center justify-center p-12">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <>
                {/* Key Metrics */}
                <TooltipProvider>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Current Price</CardTitle>
                            <ArrowUpRight className="h-4 w-4 text-green-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">${companyInfo.current_price?.toFixed(2)}</div>
                        </CardContent>
                    </Card>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Market Cap</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">
                                        {companyInfo.market_cap ? (companyInfo.market_cap / 1e12).toFixed(2) + "T" : "N/A"}
                                    </div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Market Cap"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Trailing P/E</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.pe_ratio?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Trailing P/E"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Forward P/E</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.forward_pe?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Forward P/E"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Industry P/E</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold text-muted-foreground">N/E</div>
                        </CardContent>
                    </Card>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">PEG Ratio</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.peg_ratio?.toFixed(2) || "N/E"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["PEG Ratio"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">P/S Ratio</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.price_to_sales?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["P/S Ratio"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Profit Margin</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">
                                        {companyInfo.profit_margin ? (companyInfo.profit_margin * 100).toFixed(2) + "%" : "N/A"}
                                    </div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Profit Margin"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">ROE</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">
                                        {companyInfo.roe ? (companyInfo.roe * 100).toFixed(2) + "%" : "N/A"}
                                    </div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["ROE"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Free Cash Flow</CardTitle>
                                </CardHeader>
                                <CardContent>
                                     <div className="text-xl font-bold truncate" title={companyInfo.free_cash_flow?.toLocaleString()}>
                                        {companyInfo.free_cash_flow 
                                            ? (companyInfo.free_cash_flow > 1e9 
                                                ? (companyInfo.free_cash_flow / 1e9).toFixed(2) + "B" 
                                                : (companyInfo.free_cash_flow / 1e6).toFixed(2) + "M") 
                                            : "N/A"}
                                     </div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Free Cash Flow"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Debt/Equity</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.debt_to_equity?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Debt/Equity"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Current Ratio</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.current_ratio?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Current Ratio"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Dividend Yield</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">
                                        {companyInfo.dividend_yield ? (companyInfo.dividend_yield * 100).toFixed(2) + "%" : "N/A"}
                                    </div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Dividend Yield"]}</p>
                        </TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Beta</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{companyInfo.beta?.toFixed(2) || "N/A"}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-[300px]">
                            <p>{METRIC_TOOLTIPS["Beta"]}</p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                </TooltipProvider>

                <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7">
                    {/* Main Analysis Area / Charts */}
                    <div className="col-span-4 space-y-4">
                        {/* Financial Charts */}
                        <FinancialCharts data={financials} />

                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between">
                                <div>
                                    <CardTitle>AI Analysis Engine</CardTitle>
                                    <CardDescription>Select a filing or click analysis buttons.</CardDescription>
                                </div>
                                <div className="flex gap-2">
                                    <Button 
                                        size="sm" 
                                        variant="destructive"
                                        onClick={handleAnalyzeRisk}
                                        disabled={analyzing !== null}
                                    >
                                        {analyzing === 'risk' ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <AlertTriangle className="h-4 w-4 mr-2"/>}
                                        Red Flag Scanner
                                    </Button>
                                    <Button 
                                        size="sm" 
                                        variant="outline"
                                        onClick={handleAnalyzeValuation}
                                        disabled={analyzing !== null}
                                    >
                                        {analyzing === 'valuation' ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
                                        Valuation
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {analysisResult ? (
                                        <div className="prose dark:prose-invert text-sm">
                                        <p className="whitespace-pre-line">{analysisResult}</p>
                                        </div>
                                ) : analyzing ? (
                                    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2">
                                        <Loader2 className="h-6 w-6 animate-spin" />
                                        <p>{analyzing === 'news' ? "Analyzing market sentiment..." : analyzing === 'valuation' ? "Generating valuation report..." : "Reading filing..."}</p>
                                    </div>
                                ) : (
                                    <div className="flex h-[200px] items-center justify-center text-muted-foreground bg-muted/20 rounded-md border-dashed border-2">
                                        Waiting for input...
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                        
                        <Card>
                            <CardHeader>
                                <CardTitle>Company Summary</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground leading-relaxed">{companyInfo.summary}</p>
                            </CardContent>
                        </Card>

                    </div>

                    {/* Right Column: Filings & News */}
                    <div className="col-span-3 space-y-4">
                        {/* SEC Filings List */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Recent SEC Filings</CardTitle>
                                <CardDescription>Latest 10-K, 10-Q, 20-F, 6-K</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
                                    {filings.length === 0 && <p className="text-muted-foreground text-sm">No recent filings found.</p>}
                                    {filings.map((filing, i) => (
                                        <div key={i} className="flex items-center gap-4 p-3 rounded-lg border bg-card hover:bg-accent transition-colors">
                                            <div className="h-10 w-10 shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                                <FileText className="h-5 w-5" />
                                            </div>
                                            <div className="flex-1 space-y-1 min-w-0">
                                                <p className="text-sm font-medium leading-none truncate">{filing.form} Report</p>
                                                <p className="text-xs text-muted-foreground">{filing.filingDate}</p>
                                            </div>
                                            <div className="flex gap-2">
                                                <Button 
                                                    size="sm" 
                                                    variant="secondary" 
                                                    onClick={() => window.open(filing.link, "_blank")}
                                                >
                                                    Open
                                                </Button>
                                                <Button 
                                                    size="sm" 
                                                    onClick={() => handleAnalyzeFiling(filing.link)}
                                                    disabled={analyzing !== null}
                                                >
                                                    {analyzing === filing.link ? <Loader2 className="h-4 w-4 animate-spin"/> : <Sparkles className="h-4 w-4"/>}
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Recent News List */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between">
                                <div>
                                    <CardTitle>Recent News</CardTitle>
                                    <CardDescription>Latest headlines</CardDescription>
                                </div>
                                <Button size="sm" variant="outline" onClick={handleAnalyzeNews} disabled={analyzing !== null || news.length === 0}>
                                    {analyzing === 'news' ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
                                    Summarize
                                </Button>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
                                    {news.length === 0 && <p className="text-muted-foreground text-sm">No recent news found.</p>}
                                    {news.map((item, i) => (
                                        <div key={i} className="flex flex-col gap-1 p-3 rounded-lg border bg-card hover:bg-accent transition-colors cursor-pointer" onClick={() => window.open(item.link, "_blank")}>
                                            <p className="text-sm font-medium leading-snug line-clamp-2">{item.title}</p>
                                            <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
                                                <span>{item.publisher}</span>
                                                <span>{new Date(item.providerPublishTime * 1000).toLocaleDateString()}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
                </>
            )}
        </div>
    );
}

export default function DashboardPage() {
    return (
        <DashboardLayout>
            <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
                <DashboardContent />
            </Suspense>
        </DashboardLayout>
    );
}
