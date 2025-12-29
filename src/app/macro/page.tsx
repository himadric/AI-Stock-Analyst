"use client";

import { Suspense, useEffect, useState } from "react";
import { fetchMacroData, fetchSectorPerformance, analyzeMacroMarket } from "@/lib/api";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { MacroChartCard } from "@/components/dashboard/macro-chart-card";
import { SectorHeatmap } from "@/components/dashboard/sector-heatmap";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, TrendingUp, TrendingDown, DollarSign, Activity, Globe, Sparkles, BarChart3, PieChart } from "lucide-react";
import { cn } from "@/lib/utils";

export default function MacroPage() {
  const [data, setData] = useState<any[]>([]);
  const [sectorData, setSectorData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // AI Report State
  const [report, setReport] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [macroResult, sectorResult] = await Promise.all([
            fetchMacroData(),
            fetchSectorPerformance()
        ]);
        setData(macroResult);
        setSectorData(sectorResult);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleGenerateReport() {
      setAnalyzing(true);
      setReport(null);
      try {
          // Filter economy data for the report
          const economyData = data.filter(d => d.type === "Economy");
          const res = await analyzeMacroMarket(economyData, sectorData);
          setReport(res.analysis);
      } catch (e) {
          console.error(e);
      } finally {
          setAnalyzing(false);
      }
  }

  // Group by type
  const groups = data.reduce((acc: any, item: any) => {
    const type = item.type || "Other";
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});

  const typeIcons: any = {
      "Index": Globe,
      "Commodity": Activity,
      "Rate": TrendingUp,
      "Currency": DollarSign,
      "Risk": Activity,
      "Crypto": DollarSign
  }

  return (
    <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin h-8 w-8 text-primary" /></div>}>
        <DashboardLayout>
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Macro Dashboard</h2>
                    <p className="text-muted-foreground">Global market indicators, sector performance, and economic health signals.</p>
                </div>
                <Button 
                    onClick={handleGenerateReport} 
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                    disabled={analyzing || loading}
                >
                    {analyzing ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : <Sparkles className="mr-2 h-4 w-4"/>}
                    Generate Market Briefing
                </Button>
            </div>

            {/* AI Report Section */}
            {report && (
                <Card className="border-purple-200 bg-purple-50/10 dark:bg-purple-900/10">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-purple-700 dark:text-purple-300">
                            <Sparkles className="h-5 w-5" />
                            AI Market Briefing
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-line">
                            {report}
                        </div>
                    </CardContent>
                </Card>
            )}

            {loading ? (
                <div className="flex justify-center p-12"><Loader2 className="animate-spin h-8 w-8 text-primary" /></div>
            ) : (
                <div className="space-y-8">
                    {/* 1. Economy Indicators (First) */}
                    {groups["Economy"] && (
                        <div className="space-y-4">
                            <h3 className="text-xl font-semibold flex items-center gap-2">
                                <div className="p-1.5 bg-primary/10 rounded-md">
                                    <Activity className="h-5 w-5 text-primary" />
                                </div>
                                Economy Indicators
                            </h3>
                            <div className="grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                                {groups["Economy"].map((item: any) => (
                                    <MacroChartCard 
                                        key={item.ticker} 
                                        ticker={item.ticker} 
                                        name={item.name} 
                                        type={item.type} 
                                        price={item.price}
                                        change={item.change}
                                        changePercent={item.change_percent}
                                        history={item.history}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 2. Sector Heatmap (Second) */}
                    <div className="space-y-4">
                        <h3 className="text-xl font-semibold flex items-center gap-2">
                            <div className="p-1.5 bg-primary/10 rounded-md">
                                <PieChart className="h-5 w-5 text-primary" />
                            </div>
                            Market Sectors (Real-Time)
                        </h3>
                        <SectorHeatmap data={sectorData} />
                    </div>

                    {/* 3. Other Indicators */}
                    {Object.keys(groups).filter(type => type !== "Economy").map((type) => {
                        const Icon = typeIcons[type] || Activity;
                        return (
                            <div key={type} className="space-y-4">
                                <h3 className="text-xl font-semibold flex items-center gap-2">
                                    <div className="p-1.5 bg-primary/10 rounded-md">
                                        <Icon className="h-5 w-5 text-primary" />
                                    </div>
                                    {type} Indicators
                                </h3>
                                <div className="grid gap-6 grid-cols-1">
                                    {groups[type].map((item: any) => (
                                        <MacroChartCard 
                                            key={item.ticker} 
                                            ticker={item.ticker} 
                                            name={item.name} 
                                            type={item.type} 
                                            price={item.price}
                                            change={item.change}
                                            changePercent={item.change_percent}
                                            history={item.history}
                                        />
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
        </DashboardLayout>
    </Suspense>
  );
}
