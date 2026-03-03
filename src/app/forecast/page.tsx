"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchForecast, fetchAnalystActions } from "@/lib/api";
import { Loader2, TrendingUp, TrendingDown, Target, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

function ForecastContent() {
  const searchParams = useSearchParams();
  const ticker = searchParams.get("ticker") || "AAPL";
  const [data, setData] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [forecastRes, actionsRes] = await Promise.all([
             fetchForecast(ticker),
             fetchAnalystActions(ticker),
        ]);
        setData(forecastRes);
        setActions(actionsRes);
      } catch (err) {
        console.error("Failed to load forecast:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [ticker]);

  if (loading) {
     return <div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>;
  }

  if (!data || !data.currentPrice) {
      return (
        <div className="p-8 text-center text-muted-foreground">
            No analyst forecast data available for {ticker}.
        </div>
      );
  }

  // Calculate potential upside/downside
  const upside = ((data.targetMeanPrice - data.currentPrice) / data.currentPrice) * 100;
  const isUpside = upside > 0;

  // Prepare chart data
  const chartData = [
      { name: "Current", price: data.currentPrice, fill: "#3b82f6" }, // Blue
      { name: "Low", price: data.targetLowPrice, fill: "#ef4444" },    // Red
      { name: "Average", price: data.targetMeanPrice, fill: "#f59e0b" }, // Amber
      { name: "High", price: data.targetHighPrice, fill: "#22c55e" },   // Green
  ];

  // Map recommendation key to standard terms
  const recKey = (data.recommendationKey || "").replace("_", " ").toUpperCase();
  
  const score = data.recommendationMean;
  let consensusColor = "text-yellow-500";
  if (score <= 1.5) consensusColor = "text-green-600";
  else if (score <= 2.5) consensusColor = "text-green-500";
  else if (score > 3.5) consensusColor = "text-red-500";

  return (
    <div className="space-y-6">
        <div>
            <h2 className="text-3xl font-bold tracking-tight">{ticker} Stock Forecast</h2>
            <p className="text-muted-foreground">Analyst consensus and price targets</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Target Chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Stock Price Forecast (12 Months)</CardTitle>
                    <CardDescription>
                         Based on <strong>{data.numberOfAnalystOpinions}</strong> analysts.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col items-center justify-center mb-6">
                        <div className="text-4xl font-bold flex items-center gap-2">
                             ${data.targetMeanPrice?.toFixed(2)}
                             <span className={`text-lg font-medium ${isUpside ? 'text-green-500' : 'text-red-500'}`}>
                                ({isUpside ? "+" : ""}{upside.toFixed(2)}%)
                             </span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">Average Price Target</p>
                    </div>

                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                                <XAxis dataKey="name" tick={{fontSize: 12}} />
                                <YAxis domain={['auto', 'auto']} tickFormatter={(val) => `$${val}`} />
                                <Tooltip 
                                    formatter={(val: any) => [`$${Number(val).toFixed(2)}`, "Price"]}
                                    cursor={{fill: 'transparent'}}
                                />
                                <Bar dataKey="price" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* Analyst Consensus */}
            <Card>
                <CardHeader>
                    <CardTitle>Analyst Consensus</CardTitle>
                    <CardDescription>Aggregate recommendation rating</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center min-h-[300px]">
                     {/* Gauge Visualization */}
                     <div className="relative w-64 h-32 overflow-hidden mb-4">
                        <div className="absolute w-full h-full bg-slate-200 rounded-t-full" />
                        <div 
                            className="absolute bottom-0 left-1/2 w-1 h-32 bg-black origin-bottom transition-transform duration-1000 ease-out z-10"
                            style={{ 
                                transform: `translateX(-50%) rotate(${(score - 1) * 45 - 90}deg)` 
                            }}
                        />
                        <div className="absolute w-full h-full rounded-t-full opacity-80" 
                            style={{ 
                                background: `conic-gradient(from 270deg, #22c55e 0deg 36deg, #84cc16 36deg 72deg, #eab308 72deg 108deg, #f97316 108deg 144deg, #ef4444 144deg 180deg, transparent 180deg)` 
                            }} 
                        />
                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-40 h-20 bg-background rounded-t-full" />
                     </div>

                     <div className={`text-3xl font-bold ${consensusColor} mt-4`}>
                        {recKey}
                     </div>
                     <p className="text-muted-foreground mt-2">
                         Score: <span className="font-mono font-bold text-foreground">{score?.toFixed(2)}</span> / 5.0
                     </p>
                     <p className="text-xs text-muted-foreground mt-1">(1.0 = Strong Buy, 5.0 = Sell)</p>
                </CardContent>
            </Card>
        </div>

        {/* Detailed Metrics Table */}
        <Card>
            <CardHeader>
                <CardTitle>Forecast Data</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                    <div>
                        <p className="text-sm text-muted-foreground mb-1">Low Target</p>
                        <p className="text-2xl font-bold font-mono text-red-500">${data.targetLowPrice?.toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-sm text-muted-foreground mb-1">Average Target</p>
                        <p className="text-2xl font-bold font-mono text-amber-500">${data.targetMeanPrice?.toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-sm text-muted-foreground mb-1">High Target</p>
                        <p className="text-2xl font-bold font-mono text-green-500">${data.targetHighPrice?.toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-sm text-muted-foreground mb-1">Current Price</p>
                        <p className="text-2xl font-bold font-mono text-blue-500">${data.currentPrice?.toFixed(2)}</p>
                    </div>
                </div>
            </CardContent>
        </Card>

        {/* Analyst Actions Table */}
        <Card>
            <CardHeader>
                <CardTitle>Latest Forecasts</CardTitle>
                <CardDescription>Recent analyst ratings and price target changes</CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Firm</TableHead>
                            <TableHead>Rating</TableHead>
                            <TableHead>Action</TableHead>
                            <TableHead>Price Target</TableHead>
                            <TableHead className="text-right">Date</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {actions.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center text-muted-foreground h-24">
                                    No recent analyst actions found.
                                </TableCell>
                            </TableRow>
                        ) : (
                            actions.map((action, i) => {
                                const targetChangeV = action.current_price_target - action.prior_price_target;
                                const hasTargetChange = action.prior_price_target > 0 && action.current_price_target > 0 && targetChangeV !== 0;
                                
                                return (
                                <TableRow key={i}>
                                    <TableCell className="font-medium">{action.firm}</TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className={
                                            action.to_grade.toLowerCase().includes("buy") || action.to_grade.toLowerCase().includes("outperform") ? "bg-green-100 text-green-800 hover:bg-green-200" :
                                            action.to_grade.toLowerCase().includes("sell") || action.to_grade.toLowerCase().includes("under") ? "bg-red-100 text-red-800 hover:bg-red-200" :
                                            "bg-gray-100 text-gray-800 hover:bg-gray-200"
                                        }>
                                            {action.to_grade}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        {({
                                            "main": "Maintains",
                                            "reit": "Reiterates",
                                            "init": "Initiates",
                                            "up": "Upgrades",
                                            "down": "Downgrades"
                                        } as Record<string, string>)[action.action?.toLowerCase()] || action.action}
                                    </TableCell>
                                    <TableCell>
                                        {action.current_price_target > 0 ? (
                                            <div className="flex items-center gap-1">
                                                {hasTargetChange && (
                                                   <span className="text-muted-foreground line-through text-xs">${action.prior_price_target}</span>
                                                )}
                                                <span className="font-mono">${action.current_price_target}</span>
                                                {hasTargetChange && (
                                                    targetChangeV > 0 
                                                    ? <ArrowUpRight className="h-3 w-3 text-green-500" />
                                                    : <ArrowDownRight className="h-3 w-3 text-red-500" />
                                                )}
                                            </div>
                                        ) : (
                                            <span className="text-muted-foreground">-</span>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                        {action.date ? new Date(action.date).toLocaleDateString() : "-"}
                                    </TableCell>
                                </TableRow>
                            )})
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    </div>
  );
}

export default function ForecastPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <ForecastContent />
            </DashboardLayout>
        </Suspense>
    );
}
