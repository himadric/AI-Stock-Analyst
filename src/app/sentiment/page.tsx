"use client";

import { useEffect, useState, Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { SentimentDashboard } from "@/components/dashboard/sentiment-dashboard";
import { fetchSentiment } from "@/lib/api";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function SentimentPageContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const initialTicker = searchParams.get("ticker") || "ONON";
    
    const [ticker, setTicker] = useState(initialTicker);
    const [searchInput, setSearchInput] = useState(initialTicker);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (ticker) {
            loadSentiment(ticker);
        }
    }, [ticker]);

    async function loadSentiment(t: string) {
        setLoading(true);
        try {
            const res = await fetchSentiment(t);
            setData(res);
        } catch (e) {
            console.error(e);
            setData(null);
        } finally {
            setLoading(false);
        }
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchInput.trim()) {
            setTicker(searchInput.toUpperCase());
            router.push(`/sentiment?ticker=${searchInput.toUpperCase()}`);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Brand Sentiment</h2>
                    <p className="text-muted-foreground">Real-time social media analysis for {ticker}.</p>
                </div>
                <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-auto">
                    <Input 
                        placeholder="Search ticker (e.g. AAPL)..." 
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        className="w-full md:w-[200px]"
                    />
                    <Button type="submit" size="icon">
                        <Search className="h-4 w-4" />
                    </Button>
                </form>
            </div>

            <SentimentDashboard data={data} isLoading={loading} />
        </div>
    );
}

export default function SentimentPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
            <DashboardLayout>
                <SentimentPageContent />
            </DashboardLayout>
        </Suspense>
    );
}
