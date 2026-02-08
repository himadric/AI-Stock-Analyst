"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import Link from "next/link";

interface Holding {
    symbol: string;
    name: string;
    percent: number;
}

interface EtfHoldingsProps {
    holdings: Holding[];
}

export function EtfHoldings({ holdings }: EtfHoldingsProps) {
    if (!holdings || holdings.length === 0) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Top Holdings</CardTitle>
                    <CardDescription>Top 10 Portfolio Constituents</CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-center p-6 text-muted-foreground">
                    No holdings data available.
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle>Top Holdings</CardTitle>
                <CardDescription>Top constituents by weight</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="pl-6">Symbol</TableHead>
                            <TableHead>Company</TableHead>
                            <TableHead className="text-right pr-6">Weight</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {holdings.map((holding, i) => (
                            <TableRow key={i}>
                                <TableCell className="font-medium pl-6">
                                    <Link href={`/?ticker=${holding.symbol}`} className="hover:underline text-primary">
                                        {holding.symbol}
                                    </Link>
                                </TableCell>
                                <TableCell className="truncate max-w-[150px]" title={holding.name}>
                                    <Link href={`/?ticker=${holding.symbol}`} className="hover:underline">
                                        {holding.name}
                                    </Link>
                                </TableCell>
                                <TableCell className="text-right pr-6">{(holding.percent * 100).toFixed(2)}%</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
