"use client";

import { useEffect, useState } from "react";
import { fetchVanguardTrades } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowUp, ArrowDown, Loader2, DollarSign } from "lucide-react";
import Link from "next/link";

export function VanguardTracker() {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const res = await fetchVanguardTrades();
                setData(res);
            } catch (e) {
                setError("Failed to load Vanguard data");
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) return <div className="flex justify-center p-10"><Loader2 className="animate-spin" /></div>;
    if (error) return <div className="text-red-500 p-4">{error}</div>;
    if (!data) return null;

    const TradeTable = ({ trades, type }: { trades: any[], type: 'buy' | 'sell' }) => (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead className="text-right">Shares {type === 'buy' ? 'Added' : 'Sold'}</TableHead>
                    <TableHead className="text-right">Value Chg ($1000s)</TableHead>
                    <TableHead className="text-right">% Change</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {trades.map((row: any, i: number) => (
                    <TableRow key={i}>
                        <TableCell className="font-medium">
                            {row.ticker !== "N/A" ? (
                                <Link href={`/?ticker=${row.ticker}`} className="hover:underline text-primary">
                                    {row.ticker}
                                </Link>
                            ) : (
                                <span className="text-muted-foreground">N/A</span>
                            )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{row.name}</TableCell>
                        <TableCell className={type === 'buy' ? "text-green-600 text-right" : "text-red-600 text-right"}>
                            {type === 'buy' ? '+' : ''}{row.shares_change.toLocaleString()}
                        </TableCell>
                         <TableCell className="text-right">
                            {type === 'buy' ? '+' : ''}{Math.round(row.value_change).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                             <Badge variant={type === 'buy' ? "outline" : "secondary"}>
                                {row.percent_change.toFixed(1)}%
                             </Badge>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Vanguard Instituional Tracker (13F)</h1>
                <p className="text-muted-foreground">
                    Tracking major portfolio moves by The Vanguard Group based on quarterly SEC 13F filings.
                    Last Report: {data.report_date} (Changed from {data.prev_report_date})
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">

                <Card className="h-[600px] flex flex-col">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-green-600">
                            <ArrowUp className="h-5 w-5" /> Top Buys (Share Count)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-auto">
                        <TradeTable trades={data.top_buys} type="buy" />
                    </CardContent>
                </Card>

                <Card className="h-[600px] flex flex-col">
                    <CardHeader>
                         <CardTitle className="flex items-center gap-2 text-red-600">
                            <ArrowDown className="h-5 w-5" /> Top Sells (Share Count)
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 overflow-auto">
                        <TradeTable trades={data.top_sells} type="sell" />
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
