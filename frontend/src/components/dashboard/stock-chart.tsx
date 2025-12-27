"use client";

import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { format, parseISO } from "date-fns";
import { cn } from "@/lib/utils"; // Assuming utils exists, or just use strings if not needed for logic

// SMA Helpers
const calculateSMA = (data: any[], window: number) => {
    let smaData = new Array(data.length).fill(null);
    for (let i = window - 1; i < data.length; i++) {
        const slice = data.slice(i - window + 1, i + 1);
        const sum = slice.reduce((acc, curr) => acc + curr.close, 0);
        smaData[i] = sum / window;
    }
    return smaData;
};

interface StockChartProps {
  data: any[];
  period: string;
  comparisons?: { ticker: string; data: any[]; color: string }[];
  indicators?: string[]; // e.g. ["SMA20", "SMA50"]
}

const CustomTooltip = ({ active, payload, label, showComparison }: any) => {
  if (active && payload && payload.length) {
    const mainPayload = payload.find((p: any) => p.dataKey === "close" || (showComparison && p.dataKey === "normalizedClose"));
    const data = mainPayload ? mainPayload.payload : payload[0].payload;
    
    // If comparison mode (normalized), we show percentages
    // Otherwise standard price/volume

    return (
      <div className="rounded-lg border bg-background p-3 shadow-lg ring-1 ring-black/5 min-w-[200px]">
        <p className="mb-2 font-medium text-foreground border-b pb-1">
          {label ? format(new Date(label), "PP p") : ""}
        </p>
        
        {/* Main Stock Data */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-2">
            {!showComparison && (
                <>
                <div className="text-muted-foreground">Open:</div>
                <div className="font-mono text-foreground">{data.open?.toFixed(2)}</div>
                <div className="text-muted-foreground">High:</div>
                <div className="font-mono text-foreground">{data.high?.toFixed(2)}</div>
                <div className="text-muted-foreground">Low:</div>
                <div className="font-mono text-foreground">{data.low?.toFixed(2)}</div>
                </>
            )}
            
            <div className="text-muted-foreground font-semibold">Close:</div>
            <div className="font-mono text-foreground font-bold">
                {showComparison ? `${data.normalizedClose?.toFixed(2)}%` : data.close?.toFixed(2)}
            </div>

            {!showComparison && (
            <>
                <div className="text-muted-foreground">Vol:</div>
                <div className={cn("font-mono font-medium", data.close >= data.open ? "text-green-500" : "text-red-500")}>
                    {(data.volume / 1000000).toFixed(2)}M
                </div>
            </>
            )}
        </div>
        
        {/* Indicators (SMA) - Only show if NOT in comparison mode (to avoid clutter and mismatch) */}
        {!showComparison && payload.map((entry: any) => {
            if (!entry.dataKey || typeof entry.dataKey !== 'string' || !entry.dataKey.startsWith('SMA')) return null;
            return (
                <div key={entry.dataKey} className="flex justify-between text-sm mt-1">
                    <span style={{ color: entry.color }}>{entry.name}:</span>
                    <span className="font-mono">{entry.value?.toFixed(2)}</span>
                </div>
            );
        })}

        {/* Comparison Data */}
        {showComparison && payload.map((entry: any) => {
            if (entry.dataKey === "close" || entry.dataKey === "normalizedClose" || entry.dataKey === "volume") return null;
            // entry.name should be the ticker
            return (
                <div key={entry.name} className="flex justify-between text-sm mt-1">
                    <span style={{ color: entry.color }}>{entry.name}:</span>
                    <span className="font-mono">{entry.value?.toFixed(2)}%</span>
                </div>
            );
        })}
      </div>
    );
  }
  return null;
};

export function StockChart({ data, period, comparisons = [], indicators = [] }: StockChartProps) {
  if (!data || data.length === 0) return null;

  const showComparison = comparisons.length > 0;
  
  // Prepare data for rendering
  // If comparing, we normalize EVERYTHING to % change from first point
  let chartData = [...data];
  
  // Calculate Indicators if strictly NOT comparing (mixing % relative change and absolute SMA price is confusing/wrong)
  // Actually one *could* normalize SMA too, but usually you want indicators on the main chart
  // For now, let's disable indicators if comparisons are active to keep it clean, or just render them.
  // Rendering absolute SMA on normalized chart is BAD.
  // If showComparison is true, we skip indicators.
  
  if (!showComparison && indicators.length > 0) {
      if (indicators.includes("SMA20")) {
          const sma = calculateSMA(data, 20);
          chartData = chartData.map((d, i) => ({ ...d, SMA20: sma[i] }));
      }
      if (indicators.includes("SMA50")) {
          const sma = calculateSMA(data, 50);
          chartData = chartData.map((d, i) => ({ ...d, SMA50: sma[i] }));
      }
      if (indicators.includes("SMA200")) {
          const sma = calculateSMA(data, 200);
          chartData = chartData.map((d, i) => ({ ...d, SMA200: sma[i] }));
      }
  }
  
  if (showComparison) {
      const basePrice = data[0].close;
      chartData = chartData.map((d, i) => ({
          ...d,
          normalizedClose: ((d.close - basePrice) / basePrice) * 100
      }));

      // Merge comparison data
      comparisons.forEach((comp) => {
           if (comp.data && comp.data.length > 0) {
               const compBase = comp.data[0].close;
               // Create a map for quick lookup by date
               const compMap = new Map(comp.data.map((cd: any) => [cd.date, cd.close]));
               
               chartData = chartData.map((d) => {
                   const cClose = compMap.get(d.date);
                   const val = cClose ? ((cClose - compBase) / compBase) * 100 : null;
                   return {
                       ...d,
                       [`comp_${comp.ticker}`]: val
                   };
               });
           }
      });
  }

  // Determine X-axis format based on period
  const getXAxisFormat = (dateStr: string) => {
    try {
        const date = new Date(dateStr);
        if (period === "1d" || period === "5d") {
            return format(date, "HH:mm"); // Time for intraday
        } else if (period === "1mo" || period === "3mo") {
            return format(date, "MMM d"); 
        } else {
            return format(date, "MMM yy");
        }
    } catch {
        return dateStr;
    }
  };

  const dataKey = showComparison ? "normalizedClose" : "close";

  // Calculate min/max for auto-scaling Y-axis nicely
  const minVal = Math.min(...chartData.map((d) => d[dataKey] || 0));
  const maxVal = Math.max(...chartData.map((d) => d[dataKey] || 0));
  const domainPadding = (maxVal - minVal) * 0.1;

  return (
    <Card className="h-full w-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-medium">
            {showComparison ? "Performance Comparison (%)" : "Price & Volume"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.2} />
              <Legend />
              <XAxis 
                dataKey="date" 
                tickFormatter={getXAxisFormat}
                minTickGap={50}
                tick={{ fontSize: 12 }}
                stroke="#888888"
              />
              {/* Left Axis: Price/% */}
              <YAxis 
                yAxisId="left"
                domain={[minVal - domainPadding, maxVal + domainPadding]}
                tickFormatter={(val) => val.toFixed(showComparison ? 1 : 2) + (showComparison ? "%" : "")}
                tick={{ fontSize: 12 }}
                width={50}
                stroke="#888888"
              />
              
              {!showComparison && (
                <YAxis 
                    yAxisId="right" 
                    orientation="right" 
                    tick={false} 
                    axisLine={false} 
                    domain={[0, 'dataMax * 4']} 
                />
              )}
              
              <Tooltip content={<CustomTooltip showComparison={showComparison} />} />
              
              {!showComparison && (
                  <Bar 
                    yAxisId="right" 
                    dataKey="volume" 
                    opacity={0.5} 
                    barSize={period === '1y' ? 2 : 10}
                  >
                    {data.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.close < entry.open ? "#ef4444" : "#22c55e"} 
                      />
                    ))}
                  </Bar>
              )}
              
              {/* Main Series */}
              <Area
                yAxisId="left"
                type="monotone"
                dataKey={dataKey}
                name="Main"
                stroke="#2563eb"
                strokeWidth={2}
                fillOpacity={showComparison ? 0 : 1} // No fill in comparison mode for clarity
                fill="url(#colorPrice)"
                isAnimationActive={false}
              />

              {/* Indicators */}
              {!showComparison && indicators.includes("SMA20") && (
                  <Line yAxisId="left" type="monotone" dataKey="SMA20" stroke="#f59e0b" strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 20" />
              )}
              {!showComparison && indicators.includes("SMA50") && (
                  <Line yAxisId="left" type="monotone" dataKey="SMA50" stroke="#3b82f6" strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 50" />
              )}
              {!showComparison && indicators.includes("SMA200") && (
                  <Line yAxisId="left" type="monotone" dataKey="SMA200" stroke="#ef4444" strokeWidth={1.5} dot={false} isAnimationActive={false} name="SMA 200" />
              )}

              {/* Comparison Lines */}
              {comparisons.map((comp) => (
                  <Line
                    key={comp.ticker}
                    yAxisId="left"
                    type="monotone"
                    dataKey={`comp_${comp.ticker}`}
                    name={comp.ticker}
                    stroke={comp.color}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls
                  />
              ))}

            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
