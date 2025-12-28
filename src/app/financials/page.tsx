"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { fetchCompanyInfo, fetchFinancials, fetchBalanceSheet, fetchCashFlow, fetchRatios } from "@/lib/api";
import { FinancialTable } from "@/components/dashboard/financial-table";
import { FinancialCharts } from "@/components/dashboard/financial-charts";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";

import { Suspense } from "react";

function FinancialsContent() {
  const searchParams = useSearchParams();
  const ticker = searchParams.get("ticker") || "AAPL";
  
  const [financials, setFinancials] = useState<any[]>([]);
  const [balanceSheet, setBalanceSheet] = useState<any[]>([]);
  const [cashFlow, setCashFlow] = useState<any[]>([]);
  const [ratios, setRatios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [inc, bal, cash, rat] = await Promise.all([
          fetchFinancials(ticker),
          fetchBalanceSheet(ticker),
          fetchCashFlow(ticker),
          fetchRatios(ticker)
        ]);
        setFinancials(inc);
        setBalanceSheet(bal);
        setCashFlow(cash);
        setRatios(rat);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  return (
        <div className="space-y-4">
            <div className="flex items-center justify-between space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">{ticker} Financials</h2>
            </div>

            {loading ? (
                <div className="flex h-[400px] w-full items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <div className="space-y-4">
                    {/* Re-use charts for visual context */}
                    <FinancialCharts data={financials} />
                    
                    <Tabs defaultValue="income" className="w-full">
                      <TabsList>
                        <TabsTrigger value="income">Income Statement</TabsTrigger>
                        <TabsTrigger value="balance">Balance Sheet</TabsTrigger>
                        <TabsTrigger value="cash">Cash Flow</TabsTrigger>
                        <TabsTrigger value="ratios">Ratios</TabsTrigger>
                      </TabsList>
                      <TabsContent value="income" className="space-y-4">
                        <FinancialTable data={financials} type="income" />
                      </TabsContent>
                      <TabsContent value="balance" className="space-y-4">
                        <FinancialTable data={balanceSheet} type="balance" />
                      </TabsContent>
                      <TabsContent value="cash" className="space-y-4">
                        <FinancialTable data={cashFlow} type="cash" />
                      </TabsContent>
                      <TabsContent value="ratios" className="space-y-4">
                        <FinancialTable data={ratios} type="ratios" />
                      </TabsContent>
                    </Tabs>
                </div>
            )}
        </div>
  );
}

export default function FinancialsPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <FinancialsContent />
            </DashboardLayout>
        </Suspense>
    );
}
