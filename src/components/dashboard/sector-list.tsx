"use client";

import { useEffect, useState } from "react";
import { fetchQuotes } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { ExternalLink } from "lucide-react";

const SECTORS = [
  { ticker: "XLK", name: "Technology" },
  { ticker: "XLI", name: "Industrials" },
  { ticker: "XLV", name: "Health Care" },
  { ticker: "XLF", name: "Financials" },
  { ticker: "XLB", name: "Materials" },
  { ticker: "XLC", name: "Communications" },
  { ticker: "XLE", name: "Energy" },
  { ticker: "XLRE", name: "Real Estate" },
  { ticker: "XLY", name: "Cons. Discretionary" },
  { ticker: "XLP", name: "Cons. Staples" },
  { ticker: "XLU", name: "Utilities" },
];

interface SectorListProps {
  selectedSectors: string[];
  onToggleSector: (ticker: string) => void;
}

export function SectorList({ selectedSectors, onToggleSector }: SectorListProps) {
  const [quotes, setQuotes] = useState<any[]>([]);

  useEffect(() => {
    async function loadQuotes() {
      try {
        const tickers = SECTORS.map(s => s.ticker);
        const data = await fetchQuotes(tickers);
        setQuotes(data);
      } catch (err) {
        console.error("Failed to load sector quotes", err);
      }
    }
    loadQuotes();
  }, []);

  // Map quotes to easy lookup
  const quoteMap = quotes.reduce((acc, q) => {
    acc[q.ticker] = q;
    return acc;
  }, {} as Record<string, any>);

  return (
    <Card className="h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base font-semibold">U.S. Equity Sectors</CardTitle>
        <ExternalLink className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid grid-cols-[auto_1fr_auto_auto_auto] gap-x-2 px-4 py-2 bg-muted/50 text-xs font-medium text-muted-foreground border-b">
          <div className="w-4" /> {/* Checkbox placeholder */}
          <div>S&P Sector ETFs</div>
          <div className="text-right">Price</div>
          <div className="text-right w-12">Chg</div>
          <div className="text-right w-12">%</div>
        </div>
        <div className="divide-y max-h-[500px] overflow-auto">
          {SECTORS.map((sector) => {
            const q = quoteMap[sector.ticker] || {};
            const isUp = q.change >= 0;
            const isSelected = selectedSectors.includes(sector.ticker);

            return (
              <div 
                key={sector.ticker} 
                className={cn(
                  "grid grid-cols-[auto_1fr_auto_auto_auto] gap-x-2 px-4 py-3 items-center text-sm hover:bg-muted/50 transition-colors cursor-pointer",
                  isSelected && "bg-muted/30"
                )}
                onClick={() => onToggleSector(sector.ticker)}
              >
                <div onClick={(e) => e.stopPropagation()}>
                    <Checkbox 
                        checked={isSelected}
                        onCheckedChange={() => onToggleSector(sector.ticker)}
                    />
                </div>
                <div className="flex items-center gap-2 truncate">
                   <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                   <span className="font-medium truncate">{sector.name}</span>
                </div>
                <div className="text-right font-mono">
                    {q.price ? q.price.toFixed(2) : "-"}
                </div>
                <div className={cn("text-right font-mono w-12", isUp ? "text-green-600" : "text-red-600")}>
                    {q.change ? (isUp ? "+" : "") + q.change.toFixed(2) : "-"}
                </div>
                <div className={cn("text-right font-mono w-12", isUp ? "text-green-600" : "text-red-600")}>
                    {q.change_percent ? (Math.abs(q.change_percent)).toFixed(1) + "%" : "-"}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
