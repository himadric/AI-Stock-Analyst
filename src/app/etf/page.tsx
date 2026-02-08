"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, AlertTriangle } from "lucide-react";
import { fetchCompanyInfo, fetchCompanyNews, analyzeNews, fetchStockHistory } from "@/lib/api";
import { EtfHoldings } from "@/components/dashboard/etf-holdings";
import { SectorAllocation } from "@/components/dashboard/sector-allocation";
import { EtfOverview } from "@/components/dashboard/etf-overview";
import { EtfAiAnalysis } from "@/components/dashboard/etf-ai-analysis";
import { StockChart } from "@/components/dashboard/stock-chart";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";


function EtfContent() {
    const searchParams = useSearchParams();
    // Default to VOO if no ticker, but allow search to drive it
    const ticker = searchParams.get("ticker") || "VOO";
    
    const [info, setInfo] = useState<any>(null);
    const [news, setNews] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [period, setPeriod] = useState("1y");
    const [loading, setLoading] = useState(true);
    const [loadingHistory, setLoadingHistory] = useState(false);
    
    // AI Analysis State
    const [analyzing, setAnalyzing] = useState<string | null>(null);
    const [analysisResult, setAnalysisResult] = useState<string | null>(null);

    useEffect(() => {
        setAnalysisResult(null);
        loadData();
    }, [ticker]);

    useEffect(() => {
        loadHistory();
    }, [ticker, period]);

    async function loadData() {
        setLoading(true);
        try {
            const [companyInfo, newsData] = await Promise.all([
                fetchCompanyInfo(ticker),
                fetchCompanyNews(ticker)
            ]);
            setInfo(companyInfo);
            setNews(newsData);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    async function loadHistory() {
        setLoadingHistory(true);
        try {
            // Determine interval based on period
            let interval = "1d";
            if (period === "1d" || period === "5d") interval = "5m"; // higher res for short
            else if (period === "1mo" || period === "3mo") interval = "1h"; // hourly for medium
            else if (['1y', 'ytd', '6mo'].includes(period)) interval = "1d";
            else interval = "1wk"; // weekly for long term

            const data = await fetchStockHistory(ticker, period, interval);
            setHistory(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoadingHistory(false);
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

    return (
        <div className="space-y-6">
             <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">{ticker} ETF Analysis</h2>
                    <p className="text-muted-foreground">Exchange Traded Funds deep dive</p>
                </div>
            </div>



            {loading ? (
                <div className="flex w-full items-center justify-center p-12">
                     <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : !info ? (
                <div className="text-center p-12">
                    <p>Could not load data for {ticker}.</p>
                </div>
            ) : (
                <>
                    {/* Warning if not an ETF */}
                    {!info.is_etf && (
                        <div className="bg-yellow-500/10 border-l-4 border-yellow-500 p-4 rounded-r-md flex items-start gap-3">
                            <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                            <div>
                                <h4 className="font-semibold text-yellow-500">Not an ETF</h4>
                                <p className="text-sm text-yellow-600/90 dark:text-yellow-500/90">
                                    The ticker <strong>{ticker}</strong> appears to be a stock or other asset, not an ETF. 
                                    Some data (Holdings, Sectors) may be missing.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Top Row: Overview Cards */}
                    <EtfOverview info={info} />

                    {/* Price Chart */}
                    <Card className="p-4 mb-12">
                        <div className="flex flex-col space-y-4">
                            <div className="flex justify-end">
                                <Tabs value={period} onValueChange={setPeriod}>
                                    <TabsList>
                                        {['1d', '5d', '1mo', '6mo', 'ytd', '1y', '5y', 'max'].map((p) => (
                                            <TabsTrigger key={p} value={p} className="text-xs h-7 px-3">
                                                {p.toUpperCase()}
                                            </TabsTrigger>
                                        ))}
                                    </TabsList>
                                </Tabs>
                            </div>
                            <div className="h-[400px]">
                                {loadingHistory ? (
                                    <div className="h-full flex items-center justify-center">
                                        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                                    </div>
                                ) : (
                                    <StockChart data={history} period={period} />
                                )}
                            </div>
                        </div>
                    </Card>

                    {/* Main Content Grid */}
                    <div className="grid gap-4 grid-cols-1 lg:grid-cols-7">
                        {/* Left: Sector Allocation (Chart) */}
                        <div className="col-span-4">
                            <SectorAllocation sectors={info.sector_weightings} />
                        </div>
                        {/* Right: Top Holdings (Table) */}
                        <div className="col-span-3">
                            <EtfHoldings holdings={info.holdings} />
                        </div>
                    </div>

                    {/* AI Analysis Section */}
                    <div className="w-full">
                        <EtfAiAnalysis ticker={ticker} />
                    </div>

                    {/* News & Summary */}
                    <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
                        {/* News List */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between">
                                <div>
                                    <CardTitle>Recent News</CardTitle>
                                    <CardDescription>Latest headlines for {ticker}</CardDescription>
                                </div>
                                <Button size="sm" variant="outline" onClick={handleAnalyzeNews} disabled={analyzing !== null || news.length === 0}>
                                    {analyzing === 'news' ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>}
                                    AI Sentiment
                                </Button>
                            </CardHeader>
                            <CardContent>
                                {(analysisResult) && (
                                    <div className="mb-4 p-4 rounded-lg bg-muted text-sm border">
                                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                                            <Sparkles className="h-4 w-4 text-primary" />
                                            AI Analysis Result
                                        </h4>
                                        <p className="whitespace-pre-line">{analysisResult}</p>
                                    </div>
                                )}
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

                        {/* Description / Summary */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Fund Summary</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    {info.summary}
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </>
            )}
        </div>
    );
}

export default function EtfPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
            <DashboardLayout>
                <EtfContent />
            </DashboardLayout>
        </Suspense>
    );
}
