"use client";

import { useEffect, useState, Suspense } from "react";
import { fetchMarketMap, fetchQuotes } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowUpRight, ArrowDownRight, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";

import { formatLargeNumber } from "@/lib/utils";

function FinderContent() {
    const router = useRouter();
    const [marketMap, setMarketMap] = useState<Record<string, string[]> | null>(null);
    const [selectedSector, setSelectedSector] = useState<string | null>(null);
    const [sectorData, setSectorData] = useState<any[]>([]);
    const [loadingMap, setLoadingMap] = useState(true);
    const [loadingSector, setLoadingSector] = useState(false);

    useEffect(() => {
        loadMap();
    }, []);

    async function loadMap() {
        try {
            const data = await fetchMarketMap('sector');
            setMarketMap(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingMap(false);
        }
    }

    async function handleSelectSector(sector: string, tickers: string[]) {
        setSelectedSector(sector);
        setSectorData([]); 
        setLoadingSector(true);
        try {
            // Fetch live quotes
            const quotes = await fetchQuotes(tickers);
            // Sort by Volume descending
            quotes.sort((a: any, b: any) => (b.volume || 0) - (a.volume || 0));
            setSectorData(quotes);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingSector(false);
        }
    }

    return (
        <div className="container mx-auto p-6 space-y-8">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Market Explorer</h1>
                <p className="text-muted-foreground">Discover top performing assets across every major industry.</p>
            </div>

            {loadingMap ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <>
                    {/* Sector Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {marketMap && Object.entries(marketMap).map(([sector, tickers]) => (
                             <Card 
                                 key={sector}
                                 className={`flex flex-col items-center justify-center h-32 cursor-pointer transition-all hover:scale-105 active:scale-95 ${selectedSector === sector ? 'bg-primary text-primary-foreground shadow-lg scale-105' : 'bg-card hover:bg-accent/50'}`}
                                 onClick={() => handleSelectSector(sector, tickers)}
                             >
                                 <h3 className="text-lg font-semibold text-center px-2">{sector}</h3>
                                 <Badge variant={selectedSector === sector ? "secondary" : "outline"} className="mt-2">
                                     {tickers.length} Assets
                                 </Badge>
                             </Card>
                        ))}
                    </div>

                    {/* Detail Table */}
                    {selectedSector && (
                        <Card className="animate-in fade-in slide-in-from-bottom-4 duration-500 mt-8">
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle>{selectedSector} Leaders</CardTitle>
                                        <CardDescription>Real-time performance of top {selectedSector} components</CardDescription>
                                    </div>
                                    <Badge variant="outline" className="font-mono">
                                        {sectorData.length} Loaded
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {loadingSector ? (
                                    <div className="flex justify-center py-12">
                                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                    </div>
                                ) : (
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Ticker</TableHead>
                                                <TableHead>Company Name</TableHead>
                                                <TableHead className="text-right">P/E Ratio</TableHead>
                                                <TableHead className="text-right">Price</TableHead>
                                                <TableHead className="text-right">Change</TableHead>
                                                <TableHead className="text-right">% Change</TableHead>
                                                <TableHead className="text-right">Volume</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {sectorData.map((stock) => {
                                                const isPositive = stock.change >= 0;
                                                return (
                                                    <TableRow 
                                                        key={stock.ticker} 
                                                        className="cursor-pointer hover:bg-muted/50"
                                                        onClick={() => router.push(`/?ticker=${stock.ticker}`)}
                                                    >
                                                        <TableCell className="font-medium">{stock.ticker}</TableCell>
                                                        <TableCell className="text-muted-foreground">{stock.name || stock.ticker}</TableCell>
                                                        <TableCell className="text-right font-mono">
                                                            {stock.pe ? stock.pe.toFixed(2) : "-"}
                                                        </TableCell>
                                                        <TableCell className="text-right font-mono">
                                                            ${stock.price?.toFixed(2)}
                                                        </TableCell>
                                                        <TableCell className={`text-right font-mono ${isPositive ? "text-green-500" : "text-red-500"}`}>
                                                            {isPositive ? "+" : ""}{stock.change?.toFixed(2)}
                                                        </TableCell>
                                                        <TableCell className={`text-right font-medium ${isPositive ? "text-green-600 bg-green-500/10" : "text-red-600 bg-red-500/10"} rounded-md`}>
                                                            <div className="flex items-center justify-end gap-1">
                                                                {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                                                                {stock.change_percent ? stock.change_percent.toFixed(2) + "%" : "0.00%"}
                                                            </div>
                                                        </TableCell>
                                                        <TableCell className="text-right font-mono text-muted-foreground">
                                                            {formatLargeNumber(stock.volume)}
                                                        </TableCell>
                                                    </TableRow>
                                                );
                                            })}
                                        </TableBody>
                                    </Table>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {!selectedSector && (
                        <div className="h-[200px] flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg bg-muted/10">
                            <Search className="h-8 w-8 mb-2 opacity-50" />
                            <p>Select a sector above to view top stocks</p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default function FinderPage() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
            <DashboardLayout>
                <FinderContent />
            </DashboardLayout>
        </Suspense>
    );
}
