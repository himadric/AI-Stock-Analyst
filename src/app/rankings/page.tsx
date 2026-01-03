"use client";

import { useEffect, useState, Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Trophy, Loader2, ArrowUpRight, TrendingUp, HelpCircle } from "lucide-react";
import { fetchRankings } from "@/lib/api";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

function RankingsContent() {
    const [rankings, setRankings] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCategory, setSelectedCategory] = useState("Small Cap");
    const [currentPage, setCurrentPage] = useState(1);
    const [totalItems, setTotalItems] = useState(0);
    const router = useRouter();
    const ITEMS_PER_PAGE = 10;

    useEffect(() => {
        loadRankings(selectedCategory, currentPage);
    }, [selectedCategory, currentPage]);

    // Reset page to 1 when category changes
    const handleCategoryChange = (category: string) => {
        if (selectedCategory !== category) {
            setSelectedCategory(category);
            setCurrentPage(1);
            setRankings([]); // Clear current data
            setLoading(true);
        }
    };

    async function loadRankings(category: string, page: number, forceRefresh: boolean = false) {
        setLoading(true);
        try {
            const response = await fetchRankings(category, page, ITEMS_PER_PAGE);
            // Handle both legacy array response (fallback) and new paginated object
            if (Array.isArray(response)) {
                setRankings(response);
                setTotalItems(response.length);
            } else {
                setRankings(response.data || []);
                setTotalItems(response.total || 0);
            }
        } catch (e) {
            console.error(e);
            setRankings([]);
        } finally {
            setLoading(false);
        }
    }

    const categories = ["Small Cap", "Mid Cap", "Large Cap"];

    const HEADER_TOOLTIPS = {
        "Score": "Composite AI score (0-10) based on Growth, Innovation, Scalability, Valuation, and Management.",
        "Rule of 40": "Growth Rate + Profit Margin. Value > 40% indicates a healthy balance of growth and profitability.",
        "R&D Intensity": "R&D Expense as % of Revenue. Indicates investment in future innovation. Target > 15-20% for tech.",
        "Scalability": "Gross Margin vs Operating Expense trend. 'Positive' means margins are expanding as revenue grows.",
        "PEG Ratio": "Price/Earnings to Growth Ratio. < 1.0 suggests the stock is undervalued relative to its growth.",
        "ROIC": "Return on Invested Capital. Measures how efficiently management allocates capital. Target > 10-15%."
    };

    const getScoreColor = (score: number) => {
        if (score >= 8) return "text-green-500 font-bold";
        if (score >= 5) return "text-yellow-500 font-bold";
        return "text-red-500 font-bold";
    };

    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Future Leaders Ranking</h2>
                <p className="text-muted-foreground">Top growth stocks identified by AI algorithms.</p>
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
                                <Trophy className="h-5 w-5 text-amber-400" />
                                {selectedCategory} Leaderboard
                            </CardTitle>
                            <CardDescription>
                                Scored on Growth Efficiency, Innovation, Scalability, Valuation, and Management.
                            </CardDescription>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => loadRankings(selectedCategory, currentPage, true)} disabled={loading}>
                            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : <TrendingUp className="h-4 w-4 mr-2"/>}
                            Refresh Rankings
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <p>Analyzing market data...</p>
                        </div>
                    ) : (
                        <>
                            <Table>
                                <TableHeader>
                                    <TooltipProvider>
                                        <TableRow>
                                            <TableHead className="w-[80px]">Rank</TableHead>
                                            <TableHead>Ticker</TableHead>
                                            <TableHead className="text-right font-bold text-primary">
                                                <div className="flex items-center justify-end gap-1">
                                                    Score
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Score"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    Rule of 40
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Rule of 40"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    R&D Intensity
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["R&D Intensity"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    Scalability
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["Scalability"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    PEG Ratio
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["PEG Ratio"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-right hidden md:table-cell">
                                                <div className="flex items-center justify-end gap-1">
                                                    ROIC
                                                    <Tooltip>
                                                        <TooltipTrigger><HelpCircle className="h-3 w-3 text-muted-foreground/50" /></TooltipTrigger>
                                                        <TooltipContent max-w="200px">{HEADER_TOOLTIPS["ROIC"]}</TooltipContent>
                                                    </Tooltip>
                                                </div>
                                            </TableHead>
                                            <TableHead className="w-[50px]"></TableHead>
                                        </TableRow>
                                    </TooltipProvider>
                                </TableHeader>
                                <TableBody>
                                    {rankings.map((item) => (
                                        <TableRow 
                                            key={item.ticker} 
                                            className="cursor-pointer hover:bg-muted/50 transition-colors"
                                            onClick={() => router.push(`/?ticker=${item.ticker}`)}
                                        >
                                            <TableCell className="font-medium text-lg text-muted-foreground">
                                                #{item.rank}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    <span className="font-bold text-lg">{item.ticker}</span>
                                                </div>
                                            </TableCell>
                                            <TableCell className={cn("text-right text-lg", getScoreColor(item.total_score))}>
                                                {item.total_score.toFixed(1)}
                                            </TableCell>
                                            <TableCell className="text-right hidden md:table-cell">
                                                <span className={item.factors.rule_of_40.pass ? "text-green-500" : "text-muted-foreground"}>
                                                    {item.factors.rule_of_40.value.toFixed(1)}%
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right hidden md:table-cell">
                                                <span className={item.factors.rnd_intensity.pass ? "text-green-500" : "text-muted-foreground"}>
                                                    {item.factors.rnd_intensity.value.toFixed(1)}%
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right hidden md:table-cell">
                                                <Badge variant={item.factors.scalability.pass ? "default" : "secondary"}>
                                                    {item.factors.scalability.value}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right hidden md:table-cell">
                                                <span className={item.factors.peg_ratio.pass ? "text-green-500" : "text-muted-foreground"}>
                                                    {item.factors.peg_ratio.value}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-right hidden md:table-cell">
                                                 <span className={item.factors.roic.pass ? "text-green-500" : "text-muted-foreground"}>
                                                    {item.factors.roic.value.toFixed(1)}%
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <Button variant="ghost" size="icon">
                                                    <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
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
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default function RankingsPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
            <DashboardLayout>
                <RankingsContent />
            </DashboardLayout>
        </Suspense>
    );
}
