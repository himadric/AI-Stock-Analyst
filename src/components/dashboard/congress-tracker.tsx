"use client";

import { useEffect, useState } from "react";
import { fetchCongressTrades } from "@/lib/api"; // You need to add this
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, Landmark } from "lucide-react";
import Link from "next/link";

export function CongressTracker() {
    const [trades, setTrades] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const res = await fetchCongressTrades(100);
                if (res.trades) {
                    setTrades(res.trades);
                } else if (res.error) {
                    setError(res.error);
                }
            } catch (e) {
                setError("Failed to load Congress data");
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) return <div className="flex justify-center p-10"><Loader2 className="animate-spin" /></div>;
    // Show error but maybe also show empty state if just no trades
    if (error) return (
        <div className="text-red-500 p-4 border border-red-200 rounded-md bg-red-50">
            Error: {error}. Make sure FMP_API_KEY is set in your .env
        </div>
    );
    
    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Congress Trading Tracker</h1>
                <p className="text-muted-foreground">
                    Tracking recent stock trading activity by US Senators and Representatives. Data via Financial Modeling Prep.
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Landmark className="h-5 w-5" /> Recent Disclosures
                    </CardTitle>
                </CardHeader>
                <CardContent className="h-[800px] overflow-auto">
                     <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Representative</TableHead>
                                <TableHead>Ticker</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Amount</TableHead>
                                <TableHead>Asset</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {trades.length === 0 && <TableRow><TableCell colSpan={6} className="text-center">No recent trades found.</TableCell></TableRow>}
                            {trades.map((row: any, i: number) => (
                                <TableRow key={i}>
                                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                                        {row.disclosure_date}
                                        <div className="text-[10px] opacity-70">Tx: {row.transaction_date}</div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-medium">{row.representative}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {row.chamber} {row.party ? `(${row.party})` : ''}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        {row.ticker ? (
                                            <Link href={`/?ticker=${row.ticker}`} className="hover:underline text-primary">
                                                {row.ticker}
                                            </Link>
                                        ) : (
                                            <span className="text-muted-foreground">-</span>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                         <Badge variant={
                                             row.type?.toLowerCase().includes("purchase") || row.type?.toLowerCase().includes("buy") ? "outline" : 
                                             row.type?.toLowerCase().includes("sale") ? "secondary" : "default"
                                         } className={
                                             row.type?.toLowerCase().includes("purchase") || row.type?.toLowerCase().includes("buy") ? "text-green-600 border-green-200 bg-green-50" : 
                                             row.type?.toLowerCase().includes("sale") ? "text-red-600 bg-red-50" : ""
                                         }>
                                            {row.type}
                                         </Badge>
                                    </TableCell>
                                    <TableCell className="text-xs font-mono">
                                        {row.amount}
                                    </TableCell>
                                    <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate" title={row.asset_description}>
                                        {row.asset_description}
                                        {row.link && (
                                            <a href={row.link} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-500 hover:underline">
                                                [Source]
                                            </a>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
