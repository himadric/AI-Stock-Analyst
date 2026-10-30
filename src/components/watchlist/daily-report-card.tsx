"use client"

import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Newspaper, ArrowUp, ArrowDown } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import type { WatchlistReport } from "@/lib/api"

interface DailyReportCardProps {
  report: WatchlistReport | null;
}

export function DailyReportCard({ report }: DailyReportCardProps) {
  const router = useRouter();

  if (!report) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Newspaper className="h-4 w-4" /> Daily Report
          </CardTitle>
          <CardDescription>
            No report yet — runs daily before market open. Check back tomorrow, or trigger it manually (see api/scripts/generate_watchlist_report.py).
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Newspaper className="h-4 w-4" /> Daily Report
        </CardTitle>
        <CardDescription>
          Generated {formatDistanceToNow(new Date(report.generated_at), { addSuffix: true })} — one AI summary per ticker, written from that day&apos;s price move and headlines.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {report.reports.map((r) => (
          <div
            key={r.ticker}
            className="rounded-md border p-3 cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => router.push(`/?ticker=${r.ticker}`)}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="bg-background">{r.ticker}</Badge>
                <span className="text-sm text-muted-foreground">{r.name}</span>
              </div>
              {r.price != null && r.change_percent != null && (
                <div className={`flex items-center gap-1 font-mono text-sm ${r.change_percent >= 0 ? "text-green-600" : "text-red-600"}`}>
                  {r.change_percent >= 0 ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
                  ${r.price.toFixed(2)} ({Math.abs(r.change_percent).toFixed(2)}%)
                </div>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{r.summary}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
