"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowUpRight, DollarSign, Percent, Scale, TrendingUp } from "lucide-react";

interface EtfOverviewProps {
    info: any;
}

export function EtfOverview({ info }: EtfOverviewProps) {
    if (!info) return null;

    const metrics = [
        {
            label: "Net Assets",
            value: info.net_assets ? (info.net_assets / 1e9).toFixed(2) + "B" : "N/A",
            icon: DollarSign,
            desc: "Total value of assets under management."
        },
        {
            label: "Expense Ratio",
            value: info.net_expense_ratio ? info.net_expense_ratio.toFixed(2) + "%" : "N/A",
            icon: Percent,
            desc: "Annual fee charged by the fund."
        },
        {
            label: "Yield",
            value: info.yield ? (info.yield * 100).toFixed(2) + "%" : info.dividend_yield ? (info.dividend_yield * 100).toFixed(2) + "%" : "N/A",
            icon: Percent,
            desc: "Annual dividend yield."
        },
        {
            label: "P/E Ratio",
            value: info.pe_ratio?.toFixed(2) || "N/A",
            icon: Scale,
            desc: "Price-to-Earnings ratio (Weighted average)."
        },
        {
            label: "NAV",
            value: info.nav_price ? "$" + info.nav_price.toFixed(2) : "N/A",
            icon: Scale,
            desc: "Net Asset Value per share."
        },
        {
            label: "YTD Return",
            value: info.ytd_return ? info.ytd_return.toFixed(2) + "%" : "N/A",
            icon: ArrowUpRight,
            desc: "Year-to-date total return."
        },
        {
            label: "Beta (3Y)",
            value: info.beta?.toFixed(2) || "N/A",
            icon: TrendingUp,
            desc: "Volatility relative to the market (1.0)."
        },
        {
            label: "52-Week Range",
            value: info.year_range || "N/A",
            icon: Scale,
            desc: "Lowest and highest price over the last year."
        }
    ];

    return (
        <TooltipProvider>
            <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
                {metrics.map((m, i) => (
                    <Tooltip key={i}>
                        <TooltipTrigger asChild>
                            <Card className="cursor-help hover:bg-accent/5 transition-colors">
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">{m.label}</CardTitle>
                                    <m.icon className="h-4 w-4 text-muted-foreground" />
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold truncate" title={m.value}>{m.value}</div>
                                </CardContent>
                            </Card>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>{m.desc}</p>
                        </TooltipContent>
                    </Tooltip>
                ))}
            </div>
        </TooltipProvider>
    );
}
