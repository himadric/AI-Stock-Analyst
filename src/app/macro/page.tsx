"use client";

import { useEffect, useState } from "react";
import { fetchMacroData } from "@/lib/api";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { MacroChartCard } from "@/components/dashboard/macro-chart-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, TrendingUp, TrendingDown, DollarSign, Activity, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

export default function MacroPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchMacroData();
        setData(result);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Group by type
  const groups = data.reduce((acc: any, item: any) => {
    const type = item.type || "Other";
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});

  const typeIcons: any = {
      "Index": Globe,
      "Commodity": Activity,
      "Rate": TrendingUp,
      "Currency": DollarSign,
      "Risk": Activity,
      "Crypto": DollarSign
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Macro Dashboard</h2>
          <p className="text-muted-foreground">Global market indicators and economic health signals.</p>
        </div>

        {loading ? (
             <div className="flex justify-center p-12"><Loader2 className="animate-spin h-8 w-8 text-primary" /></div>
        ) : (
            <div className="space-y-8">
                {Object.keys(groups).map((type) => {
                    const Icon = typeIcons[type] || Activity;
                    return (
                        <div key={type} className="space-y-4">
                            <h3 className="text-xl font-semibold flex items-center gap-2">
                                <div className="p-1.5 bg-primary/10 rounded-md">
                                    <Icon className="h-5 w-5 text-primary" />
                                </div>
                                {type} Indicators
                            </h3>
                            <div className={cn(
                                "grid gap-6",
                                type === "Economy" ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" : "grid-cols-1"
                            )}>
                                {groups[type].map((item: any) => (
                                    <MacroChartCard 
                                        key={item.ticker} 
                                        ticker={item.ticker} 
                                        name={item.name} 
                                        type={item.type} 
                                        price={item.price}
                                        change={item.change}
                                        changePercent={item.change_percent}
                                        history={item.history}
                                    />
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        )}
      </div>
    </DashboardLayout>
  );
}
