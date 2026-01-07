"use client";

import { useEffect, useState } from "react";
import { fetchHouseTrades } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, Landmark } from "lucide-react";
import Link from "next/link";

export function HouseTracker() {
    const [trades, setTrades] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                const res = await fetchHouseTrades();
                if (res.trades) {
                    setTrades(res.trades);
                    if (res.updated_at) {
                        setLastUpdated(new Date(res.updated_at).toLocaleString());
                    }
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    if (loading) return <div className="flex justify-center p-10"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">US House Tracker</h1>
                <p className="text-muted-foreground">
                    Automated tracking of US House of Representatives stock trading activity.
                    {lastUpdated && <span className="block text-xs mt-1">Last Updated: {lastUpdated}</span>}
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Landmark className="h-5 w-5" /> Recent House Trades
                    </CardTitle>
                </CardHeader>
                <CardContent className="h-[800px] overflow-auto">
                     <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Disclosure Date</TableHead>
                                <TableHead>Representative</TableHead>
                                <TableHead>Ticker</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Amount</TableHead>
                                <TableHead>Asset</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {trades.length === 0 && <TableRow><TableCell colSpan={6} className="text-center">No trades found.</TableCell></TableRow>}
                            {trades.map((row: any, i: number) => (
                                <TableRow key={i}>
                                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                                        {row.disclosureDate}
                                        <div className="text-[10px] opacity-70">Tx: {row.transactionDate}</div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-medium">{row.firstName} {row.lastName}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {row.district}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        {row.symbol ? (
                                            <Link href={`/?ticker=${row.symbol}`} className="hover:underline text-primary">
                                                {row.symbol}
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
                                    <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate" title={row.assetDescription}>
                                        {row.assetDescription}
                                        {row.link && (
                                            <a href={row.link} target="_blank" rel="noopener noreferrer" className="ml-2 text-blue-500 hover:underline">
                                                [PDF]
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
