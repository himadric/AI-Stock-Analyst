"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts";

interface PeerData {
  ticker: string;
  name: string;
  price: number;
  pe_ratio: number;
  market_cap: number;
  revenue_growth: number;
  profit_margin: number;
  roe: number;
}

interface PeerComparisonProps {
  data: PeerData[];
  ticker: string; // The active ticker to highlight
}

export function PeerComparison({ data, ticker }: PeerComparisonProps) {
  if (!data || data.length === 0) return null;

  // Format big numbers
  const formatMarketCap = (val: number) => {
      if (!val) return "-";
      return (val / 1e12).toFixed(2) + "T";
  };

  const formatPercent = (val: number) => {
      if (val === undefined || val === null) return "-";
      return (val * 100).toFixed(1) + "%";
  };

  // Prepare chart data (maybe just P/E for now as it's the most common comparison)
  const chartData = data.map(d => ({
      name: d.ticker,
      pe: d.pe_ratio || 0,
      active: d.ticker === ticker
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Metrics Table */}
        <Card className="lg:col-span-2">
            <CardHeader>
                <CardTitle>Competitor Benchmarking</CardTitle>
                <CardDescription>Relative valuation and efficiency against top peers.</CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Company</TableHead>
                            <TableHead className="text-right">Mkt Cap</TableHead>
                            <TableHead className="text-right">P/E</TableHead>
                            <TableHead className="text-right">Rev Growth</TableHead>
                            <TableHead className="text-right">Margins</TableHead>
                            <TableHead className="text-right">ROE</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {data.map((peer) => (
                            <TableRow key={peer.ticker} className={peer.ticker === ticker ? "bg-muted/50 font-medium" : ""}>
                                <TableCell>
                                    <div className="flex flex-col">
                                        <span>{peer.ticker}</span>
                                        <span className="text-xs text-muted-foreground truncate max-w-[100px]">{peer.name}</span>
                                    </div>
                                </TableCell>
                                <TableCell className="text-right">{formatMarketCap(peer.market_cap)}</TableCell>
                                <TableCell className="text-right font-mono">
                                    {peer.pe_ratio ? peer.pe_ratio.toFixed(1) : "-"}
                                </TableCell>
                                <TableCell className="text-right text-green-600">
                                    {formatPercent(peer.revenue_growth)}
                                </TableCell>
                                <TableCell className="text-right">
                                    {formatPercent(peer.profit_margin)}
                                </TableCell>
                                <TableCell className="text-right">
                                    {formatPercent(peer.roe)}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>

        {/* Right: Valuation Chart */}
        <Card className="lg:col-span-1">
             <CardHeader>
                <CardTitle>Valuation Spread (P/E)</CardTitle>
                <CardDescription>Lower is generally "cheaper".</CardDescription>
            </CardHeader>
            <CardContent className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                        <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                        {/* <YAxis hide /> */}
                        <Tooltip 
                            cursor={{fill: 'transparent'}}
                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                        />
                        <Bar dataKey="pe" radius={[4, 4, 0, 0]}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.active ? "#3b82f6" : "#cbd5e1"} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    </div>
  );
}
