"use client";

import { useEffect, useState, Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Shield, Loader2, ArrowUpRight, TrendingUp, HelpCircle } from "lucide-react"; // Shield icon for govt
import { fetchGovtRankings } from "@/lib/api";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

function DefenseContent() {
    const [rankings, setRankings] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCategory, setSelectedCategory] = useState("Small Cap");
    const [currentPage, setCurrentPage] = useState(1);
    
    // Client-side pagination state
    const ITEMS_PER_PAGE = 10;
    
    const router = useRouter();

    useEffect(() => {
        loadRankings(selectedCategory);
    }, [selectedCategory]);

    const handleCategoryChange = (category: string) => {
        if (selectedCategory !== category) {
            setSelectedCategory(category);
            setCurrentPage(1);
            setRankings([]); // Clear current data
            setLoading(true);
        }
    };

    async function loadRankings(category: string, forceRefresh: boolean = false) {
        setLoading(true);
        try {
            const data = await fetchGovtRankings(category);
            // API returns full array
            setRankings(data || []);
        } catch (e) {
            console.error(e);
            setRankings([]);
        } finally {
            setLoading(false);
        }
    }

    const categories = ["Small Cap", "Mid Cap", "Large Cap"];

    const HEADER_TOOLTIPS = {
        "Book-to-Bill": "Ratio of Orders Received (90d) to Revenue Billed (Quarterly). > 1.0 means backlog is growing (Strong Buy).",
        "Orders": "New contract awards (Input) from USAspending.gov in the last 90 days.",
        "Revenue": "Quarterly Revenue (Output) from latest financial statements."
    };

    const getRatioColor = (ratio: number) => {
        if (ratio >= 1.2) return "text-green-500 font-bold";
        if (ratio >= 1.0) return "text-green-400 font-bold";
        if (ratio >= 0.8) return "text-yellow-500";
        return "text-red-500";
    };

    // Client-Side Pagination Logic
    const totalItems = rankings.length;
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    const paginatedRankings = rankings.slice(
        (currentPage - 1) * ITEMS_PER_PAGE,
        currentPage * ITEMS_PER_PAGE
    );

    const formatMoney = (val: number) => {
        if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
        if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
        return `$${val.toLocaleString()}`;
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Govt Spending Tracker</h2>
                <p className="text-muted-foreground">
                    Analyzing government contract inflows vs. revenue outflows to predict future growth.
                </p>
            </div>
            
            <div className="flex gap-4">
                {categories.map((cat) => (
                    <div 
                        key={cat}
                        onClick={() => handleCategoryChange(cat)}
                        className={cn(
                            "cursor-pointer px-8 py-3 rounded-xl font-bold text-lg transition-all border shadow-sm", 
                            selectedCategory === cat 
                                ? "bg-black text-white hover:bg-gray-800 border-black ring-2 ring-offset-2 ring-black" 
                                : "bg-white text-black hover:bg-gray-50 border-gray-200"
                        )}
                    >
                        {cat}
                    </div>
                ))}
            </div>

            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="h-5 w-5 text-blue-600" />
                                {selectedCategory} Backlog Analysis
                            </CardTitle>
                            <CardDescription>
                                Ranked by Book-to-Bill Ratio (USAspending Awards / Financial Revenue)
                            </CardDescription>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => loadRankings(selectedCategory, true)} disabled={loading}>
                            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <TrendingUp className="h-4 w-4 mr-2"/>}
                            Refresh Data
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <p>Scanning government contracts...</p>
                        </div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TooltipProvider>
                                        <TableRow>
                                            <TableHead className="w-[80px]">Rank</TableHead>
                                            <TableHead>Company</TableHead>
                                            <TableHead className="text-right font-bold text-primary">
                                                <div className="flex items-center justify-end gap-1">
                                                    Book-to-Bill
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Book-to-Bill"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    Orders (90d)
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Orders"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    Revenue (Qtr)
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Revenue"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="hidden md:table-cell">Analysis</TableHead>
                                            <TableHead className="w-[50px]"></TableHead>
                                        </TableRow>
                                    </TooltipProvider>
                                </TableHeader>
                                <TableBody>
                                    {paginatedRankings.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={7} className="h-24 text-center">
                                                No defense contractors found with backlog data in this category.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        paginatedRankings.map((item, index) => (
                                            <TableRow 
                                                key={item.ticker} 
                                                className="cursor-pointer hover:bg-muted/50 transition-colors"
                                                onClick={() => router.push(`/?ticker=${item.ticker}`)}
                                            >
                                                <TableCell className="font-medium text-lg text-muted-foreground">
                                                    #{(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex flex-col">
                                                        <span className="font-bold text-lg">{item.ticker}</span>
                                                        <span className="text-sm text-muted-foreground">{item.company_name}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell className={cn("text-right text-lg", getRatioColor(item.book_to_bill_ratio))}>
                                                    {item.book_to_bill_ratio.toFixed(2)}x
                                                </TableCell>
                                                <TableCell className="text-right hidden md:table-cell font-mono">
                                                    {formatMoney(item.orders_inflow)}
                                                </TableCell>
                                                <TableCell className="text-right hidden md:table-cell font-mono">
                                                    {formatMoney(item.revenue_billed)}
                                                </TableCell>
                                                <TableCell className="hidden md:table-cell">
                                                    <Badge variant={item.book_to_bill_ratio > 1 ? "default" : "secondary"}>
                                                        {item.analysis}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <Button variant="ghost" size="icon">
                                                        <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                            
                            {/* Pagination Controls */}
                            {totalItems > 0 && (
                                <div className="flex items-center justify-between py-4 border-t mt-4">
                                    <div className="text-sm text-muted-foreground">
                                        Page {currentPage} of {Math.max(1, totalPages)}
                                    </div>
                                    <div className="flex gap-2">
                                        <Button 
                                            variant="outline" 
                                            size="sm" 
                                            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                            disabled={currentPage === 1}
                                        >
                                            Previous
                                        </Button>
                                        <Button 
                                            variant="outline" 
                                            size="sm" 
                                            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                            disabled={currentPage >= totalPages}
                                        >
                                            Next
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default function DefensePage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
            <DashboardLayout>
                <DefenseContent />
            </DashboardLayout>
        </Suspense>
    );
}
