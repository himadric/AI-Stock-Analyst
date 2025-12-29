"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts"; // Minimized imports
import { fetchStockHistory } from "@/lib/api";
import { Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

type Timeframe = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";

interface MacroChartCardProps {
  ticker: string;
  name: string;
  type: string;
  price?: number;
  change?: number;
  history?: { date: string; value: number }[];
}

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function MacroChartCard({ ticker, name, type, price, change, changePercent, history }: MacroChartCardProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(type !== "Economy"); // Don't load if economy
  const [timeframe, setTimeframe] = useState<Timeframe>("1D");
  const [currentQuote, setCurrentQuote] = useState<{ price: number; change: number; percent: number } | null>(
      price !== undefined ? { price, change: change || 0, percent: changePercent || 0 } : null
  );

  const timeframeConfig: Record<Timeframe, { period: string; interval: string }> = {
    "1D": { period: "1d", interval: "5m" },
    "1W": { period: "5d", interval: "15m" },
    "1M": { period: "1mo", interval: "1d" },
    "3M": { period: "3mo", interval: "1d" },
    "1Y": { period: "1y", interval: "1d" },
    "ALL": { period: "max", interval: "1wk" },
  };
  useEffect(() => {
        if (price !== undefined) {
             setCurrentQuote({ 
                 price, 
                 change: change || 0, 
                 percent: changePercent || 0 
             });
        }
  }, [price, change, changePercent]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      // Skip history for Economy indicators
      if (type === "Economy") {
          setLoading(false);
          return;
      }

      setLoading(true);
      try {
        const config = timeframeConfig[timeframe];
        const history = await fetchStockHistory(ticker, config.period, config.interval);
        
        if (mounted && history && history.length > 0) {
          setData(history);
          const last = history[history.length - 1];
          const first = history[0]; 
          
          setCurrentQuote({
              price: last.close,
              change: last.close - first.close,
              percent: ((last.close - first.close) / first.close) * 100
          });
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [ticker, timeframe, type]);

  const isPositive = currentQuote ? currentQuote?.change >= 0 : false;
  const color = isPositive ? "#22c55e" : "#ef4444"; 

  const getXAxisFormat = (dateStr: string) => {
    try {
        const date = new Date(dateStr);
        if (timeframe === "1D") return format(date, "HH:mm");
        if (timeframe === "1W" || timeframe === "1M") return format(date, "MMM d");
        if (timeframe === "ALL") return format(date, "yyyy");
        return format(date, "MMM");
    } catch {
        return "";
    }
  }; 

  // Special Render for Economic Data (Compact Scorecard)
  if (type === "Economy" && currentQuote) {
      return (
        <Card className="flex flex-col h-[180px] hover:shadow-md transition-shadow">
          <CardHeader className="pb-2">
             <div className="flex justify-between items-start">
                <CardTitle className="text-sm font-medium text-muted-foreground">{name}</CardTitle>
                <div className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">{ticker}</div>
             </div>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center flex-1 pb-6">
              <div className="text-5xl font-bold tracking-tighter text-foreground">
                  {currentQuote.price.toFixed(2)}%
              </div>
              <div className="text-xs text-muted-foreground mt-2 font-medium uppercase tracking-wider">
                  Latest Reading
              </div>
          </CardContent>
        </Card>
      );
  }

  // Standard Chart Card
  return (
    <Card className="flex flex-col h-[400px]">
      <CardHeader className="pb-4 space-y-4 border-b bg-muted/5">
        <div className="flex items-center justify-between">
            <div>
                <CardTitle className="text-base font-semibold">{name}</CardTitle>
                <div className="text-sm text-muted-foreground font-mono mt-1">{ticker}</div>
            </div>
            <div className="text-right">
                {currentQuote && (
                    <>
                        <div className="font-bold text-2xl">
                            {currentQuote.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className={cn("text-sm font-medium", isPositive ? "text-green-600" : "text-red-600")}>
                            {isPositive ? "+" : ""}{currentQuote.percent.toFixed(2)}%
                        </div>
                    </>
                )}
            </div>
        </div>
        
        <div className="flex justify-end gap-2">
            {(Object.keys(timeframeConfig) as Timeframe[]).map((tf) => (
                <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={cn(
                        "px-3 py-1.5 text-xs font-medium rounded-md border transition-all",
                        timeframe === tf 
                            ? "bg-slate-900 text-white border-slate-900 shadow-sm" 
                            : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:border-slate-300"
                    )}
                >
                    {tf}
                </button>
            ))}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 p-0 min-h-0 relative">
        {loading ? (
             <div className="absolute inset-0 flex items-center justify-center">
                 <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
             </div>
        ) : (
            <div className="h-full w-full pt-6 pr-4">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id={`gradient-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={color} stopOpacity={0.2}/>
                                <stop offset="95%" stopColor={color} stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <XAxis 
                            dataKey="date" 
                            tickFormatter={getXAxisFormat}
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={40}
                            interval="preserveStartEnd"
                            dy={10}
                        />
                        <YAxis 
                            domain={['auto', 'auto']} 
                            tickFormatter={(val) => val.toLocaleString(undefined, { maximumFractionDigits: 2, notation: "compact" })}
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={false}
                            width={50}
                            dx={-10}
                        />
                         <Tooltip 
                            contentStyle={{ borderRadius: '8px', fontSize: '12px', border: '1px solid #e2e8f0' }}
                            labelFormatter={() => ''}
                            formatter={(value: number) => [value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), 'Price']}
                        />
                        <Area 
                            type="monotone" 
                            dataKey="close" 
                            stroke={color} 
                            fillOpacity={1} 
                            fill={`url(#gradient-${ticker})`} 
                            strokeWidth={2}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                 </ResponsiveContainer>
            </div>
        )}
      </CardContent>
    </Card>
  );
}
