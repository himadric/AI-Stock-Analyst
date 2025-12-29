"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchStockHistory } from "@/lib/api";
import { StockChart } from "@/components/dashboard/stock-chart";
import { ChartAnalysis } from "@/components/dashboard/chart-analysis";
import { SectorList } from "@/components/dashboard/sector-list";
import { IndicatorList } from "@/components/dashboard/indicator-list";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

type Timeframe = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";

const COLORS = [
  "#f97316", "#f59e0b", "#84cc16", "#10b981", "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", "#f43f5e"
];

import { Suspense } from "react";

function ChartContent() {
  const searchParams = useSearchParams();
  const ticker = searchParams.get("ticker") || "AAPL";
  
  const [data, setData] = useState<any[]>([]);
  const [comparisonData, setComparisonData] = useState<any[]>([]);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState<Timeframe>("1Y");

  const timeframeConfig: Record<Timeframe, { period: string; interval: string }> = {
    "1D": { period: "1d", interval: "5m" },
    "1W": { period: "5d", interval: "15m" },
    "1M": { period: "1mo", interval: "1d" },
    "3M": { period: "3mo", interval: "1d" },
    "1Y": { period: "1y", interval: "1d" },
    "ALL": { period: "max", interval: "1wk" },
  };

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const config = timeframeConfig[timeframe];
        const history = await fetchStockHistory(ticker, config.period, config.interval);
        setData(history);
        
        // Reload comparisons if period changes
        if (selectedSectors.length > 0) {
            await updateComparisons(selectedSectors, config);
        }
      } catch (err) {
        console.error("Failed to load chart data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [ticker, timeframe]);

  // Handle sector fetching separate from main load to avoid full reload
  const updateComparisons = async (sectors: string[], config: any) => {
      const results = await Promise.all(sectors.map(async (sec, idx) => {
          try {
              const hist = await fetchStockHistory(sec, config.period, config.interval);
              return { ticker: sec, data: hist, color: COLORS[idx % COLORS.length] };
          } catch (e) {
              console.error(`Failed to fetch ${sec}`, e);
              return null;
          }
      }));
      setComparisonData(results.filter(Boolean));
  };

  const handleToggleSector = async (sec: string) => {
      const newSelection = selectedSectors.includes(sec)
        ? selectedSectors.filter(s => s !== sec)
        : [...selectedSectors, sec];
      
      setSelectedSectors(newSelection);
      // Fetch data for new selection
      await updateComparisons(newSelection, timeframeConfig[timeframe]);
  };

  const handleToggleIndicator = (id: string) => {
      if (selectedIndicators.includes(id)) {
          setSelectedIndicators(selectedIndicators.filter(i => i !== id));
      } else {
          setSelectedIndicators([...selectedIndicators, id]);
      }
  };

  return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">{ticker} Technical Analysis</h2>
          <div className="flex space-x-2">
            {(Object.keys(timeframeConfig) as Timeframe[]).map((tf) => (
              <Button
                key={tf}
                variant={timeframe === tf ? "default" : "outline"}
                size="sm"
                onClick={() => setTimeframe(tf)}
              >
                {tf}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-6 items-start">
            {/* Left Sidebar: Sectors & Indicators */}
            <div className="space-y-4 order-2 md:order-1 md:sticky md:top-4">
                <SectorList 
                    selectedSectors={selectedSectors} 
                    onToggleSector={handleToggleSector} 
                />
                <IndicatorList
                    selectedIndicators={selectedIndicators}
                    onToggleIndicator={handleToggleIndicator}
                />
            </div>

            {/* Right Main: Chart */}
            <div className="space-y-6 order-1 md:order-2">
                {loading ? (
                    <div className="flex h-[500px] w-full items-center justify-center rounded-lg border bg-card">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <>
                    <div className="h-[500px]">
                        <StockChart 
                            data={data} 
                            period={timeframeConfig[timeframe].period} 
                            comparisons={comparisonData}
                            indicators={selectedIndicators}
                        />
                    </div>
                    <ChartAnalysis 
                        ticker={ticker} 
                        period={timeframeConfig[timeframe].period} 
                        interval={timeframeConfig[timeframe].interval} 
                    />
                    </>
                )}
            </div>
        </div>
      </div>
  );
}

export default function ChartPage() {
  return (
    <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
        <DashboardLayout>
            <ChartContent />
        </DashboardLayout>
    </Suspense>
  );
}
