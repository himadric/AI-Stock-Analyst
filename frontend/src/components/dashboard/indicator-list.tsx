"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { Activity } from "lucide-react";

const INDICATORS = [
  { id: "SMA20", name: "SMA 20", color: "#f59e0b" },  // Amber
  { id: "SMA50", name: "SMA 50", color: "#3b82f6" },  // Blue
  { id: "SMA200", name: "SMA 200", color: "#ef4444" }, // Red
];

interface IndicatorListProps {
  selectedIndicators: string[];
  onToggleIndicator: (id: string) => void;
}

export function IndicatorList({ selectedIndicators, onToggleIndicator }: IndicatorListProps) {
  return (
    <Card className="h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base font-semibold">Technical Indicators</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y">
          {INDICATORS.map((indicator) => {
            const isSelected = selectedIndicators.includes(indicator.id);
            return (
              <div 
                key={indicator.id} 
                className={cn(
                  "flex items-center gap-3 px-4 py-3 text-sm hover:bg-muted/50 transition-colors cursor-pointer",
                  isSelected && "bg-muted/30"
                )}
                onClick={() => onToggleIndicator(indicator.id)}
              >
                <div onClick={(e) => e.stopPropagation()}>
                    <Checkbox 
                        checked={isSelected}
                        onCheckedChange={() => onToggleIndicator(indicator.id)}
                    />
                </div>
                <div className="flex-1 font-medium">{indicator.name}</div>
                <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: indicator.color }}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
