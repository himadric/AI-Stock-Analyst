"use client"

import { useEffect, useState, Suspense } from "react"
import { getWatchlist, removeFromWatchlist, fetchWatchlistReport, type WatchlistReport } from "@/lib/api"
import { WatchlistTable } from "@/components/watchlist/watchlist-table"
import { DailyReportCard } from "@/components/watchlist/daily-report-card"
import DashboardLayout from "@/components/layout/dashboard-layout"

interface WatchlistItem {
    ticker: string;
    name: string;
    price: number;
    change: number;
    change_percent: number;
}

function WatchlistContent() {
    const [data, setData] = useState<WatchlistItem[]>([])
    const [report, setReport] = useState<WatchlistReport | null>(null)
    const [loading, setLoading] = useState(true)

    const fetchData = async () => {
        setLoading(true)
        try {
            const [watchlistRes, reportRes] = await Promise.all([
                getWatchlist(),
                fetchWatchlistReport(),
            ])
            setData(watchlistRes)
            setReport(reportRes)
        } catch (e) {
            console.error("Failed to fetch watchlist", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
    }, [])

    const handleRemove = async (ticker: string) => {
        // Optimistic update
        const previousData = [...data]
        setData(prev => prev.filter(i => i.ticker !== ticker))
        
        try {
            await removeFromWatchlist(ticker)
        } catch (e) {
            console.error(e)
            // Revert on failure
            setData(previousData)
        }
    }

    return (
        <DashboardLayout>
            <div className="container py-10 max-w-5xl">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
                        <p className="text-muted-foreground mt-2">Monitor your favorite stocks in real-time.</p>
                    </div>
                </div>
                
                {loading ? (
                    <div className="flex items-center justify-center h-64 border rounded-md bg-muted/10">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    </div>
                ) : (
                    <div className="space-y-6">
                        <DailyReportCard report={report} />
                        <WatchlistTable data={data} onRemove={handleRemove} />
                    </div>
                )}
            </div>
        </DashboardLayout>
    )
}

export default function WatchlistPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>}>
            <WatchlistContent />
        </Suspense>
    )
}
