"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface SectorData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

interface SectorHeatmapProps {
  data: SectorData[];
}

export function SectorHeatmap({ data }: SectorHeatmapProps) {
  // Sort data by performance for better visual flow (Heatmap logic often groups similar colors)
  // or strictly by name? Let's sort by percent change descending (Best to Worst)
  const sortedData = [...data].sort((a, b) => b.change_percent - a.change_percent);

  if (data.length === 0) {
      return (
          <Card className="h-[300px] flex items-center justify-center text-muted-foreground">
              No sector data available
          </Card>
      )
  }

  // Determine max intensity for coloring scaling (optional, or just threshold)
  // Simple threshold logic:
  // > +2% = Bright Green
  // 0 to +2% = Soft Green
  // 0% = Gray
  // 0 to -2% = Soft Red
  // < -2% = Bright Red

  const getColor = (percent: number) => {
      if (percent >= 2.0) return "bg-green-500 text-white";
      if (percent > 0) return "bg-green-500/80 text-white";
      if (percent === 0) return "bg-gray-500 text-white";
      if (percent > -2.0) return "bg-red-500/80 text-white";
      return "bg-red-500 text-white";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Sector Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
            <TooltipProvider>
            {sortedData.map((sector) => (
                <Tooltip key={sector.ticker}>
                    <TooltipTrigger asChild>
                        <div 
                            className={cn(
                                "h-24 rounded-md flex flex-col items-center justify-center cursor-pointer transition-transform hover:scale-105",
                                getColor(sector.change_percent)
                            )}
                        >
                            <span className="text-xs font-semibold text-center px-1 truncate w-full">{sector.name}</span>
                            <span className="text-lg font-bold">{sector.change_percent > 0 ? "+" : ""}{sector.change_percent.toFixed(2)}%</span>
                            <span className="text-[10px] opacity-80">{sector.ticker}</span>
                        </div>
                    </TooltipTrigger>
                    <TooltipContent>
                        <div className="text-xs">
                            <p className="font-bold">{sector.name} ({sector.ticker})</p>
                            <p>Price: ${sector.price.toFixed(2)}</p>
                            <p>Change: {sector.change.toFixed(2)}</p>
                        </div>
                    </TooltipContent>
                </Tooltip>
            ))}
            </TooltipProvider>
        </div>
      </CardContent>
    </Card>
  );
}
