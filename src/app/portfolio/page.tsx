"use client"

import { useEffect, useState, Suspense } from "react"
import { getPortfolio, addPortfolioPosition, sellPortfolioPosition, deletePortfolioPosition, type PortfolioPosition } from "@/lib/api"
import { PortfolioOpenTable, PortfolioClosedTable } from "@/components/dashboard/portfolio-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Plus } from "lucide-react"

function PortfolioContent() {
    const [open, setOpen] = useState<PortfolioPosition[]>([])
    const [closed, setClosed] = useState<PortfolioPosition[]>([])
    const [loading, setLoading] = useState(true)
    const [showAddForm, setShowAddForm] = useState(false)
    const [addTicker, setAddTicker] = useState("")
    const [addShares, setAddShares] = useState("")
    const [addCostBasis, setAddCostBasis] = useState("")
    const [addError, setAddError] = useState<string | null>(null)
    const [adding, setAdding] = useState(false)

    const fetchData = async () => {
        setLoading(true)
        try {
            const res = await getPortfolio()
            setOpen(res.open)
            setClosed(res.closed)
        } catch (e) {
            console.error("Failed to fetch portfolio", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
    }, [])

    async function handleAdd(e: React.FormEvent) {
        e.preventDefault()
        setAddError(null)
        const shares = parseFloat(addShares)
        const costBasis = parseFloat(addCostBasis)
        if (!addTicker.trim() || !shares || shares <= 0 || !costBasis || costBasis <= 0) {
            setAddError("Enter a ticker, a positive share count, and a positive cost basis.")
            return
        }
        setAdding(true)
        try {
            await addPortfolioPosition(addTicker.trim().toUpperCase(), shares, costBasis)
            setAddTicker("")
            setAddShares("")
            setAddCostBasis("")
            setShowAddForm(false)
            await fetchData()
        } catch (e) {
            setAddError(e instanceof Error ? e.message : "Failed to add position")
        } finally {
            setAdding(false)
        }
    }

    // Optimistic: moves the position from open to closed immediately, reverts
    // on failure - same pattern the watchlist page already uses for removal.
    async function handleSell(ticker: string) {
        const previousOpen = [...open]
        setOpen((prev) => prev.filter((p) => p.ticker !== ticker))
        try {
            await sellPortfolioPosition(ticker)
            await fetchData()
        } catch (e) {
            console.error(e)
            setOpen(previousOpen)
        }
    }

    async function handleDeleteClosed(id: string) {
        const previousClosed = [...closed]
        setClosed((prev) => prev.filter((p) => p.id !== id))
        try {
            await deletePortfolioPosition(id)
        } catch (e) {
            console.error(e)
            setClosed(previousClosed)
        }
    }

    return (
        <DashboardLayout>
            <div className="container py-10 max-w-5xl space-y-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
                        <p className="text-muted-foreground mt-2">
                            A demo portfolio — not a real brokerage link. Track positions and see the chat
                            assistant&apos;s buy/sell suggestions weighed against your actual cost basis.
                        </p>
                    </div>
                    <Button onClick={() => setShowAddForm((s) => !s)} variant={showAddForm ? "outline" : "default"}>
                        <Plus className="h-4 w-4 mr-1" /> Add Position
                    </Button>
                </div>

                {showAddForm && (
                    <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3 p-4 border rounded-md bg-muted/10">
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Ticker</label>
                            <Input value={addTicker} onChange={(e) => setAddTicker(e.target.value)} placeholder="AAPL" className="w-28" />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Shares</label>
                            <Input value={addShares} onChange={(e) => setAddShares(e.target.value)} placeholder="10" type="number" className="w-24" />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Cost Basis ($/share)</label>
                            <Input value={addCostBasis} onChange={(e) => setAddCostBasis(e.target.value)} placeholder="180.50" type="number" className="w-32" />
                        </div>
                        <Button type="submit" disabled={adding}>{adding ? "Adding…" : "Add"}</Button>
                        {addError && <p className="text-sm text-red-600 basis-full">{addError}</p>}
                    </form>
                )}

                {loading ? (
                    <div className="flex items-center justify-center h-64 border rounded-md bg-muted/10">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    </div>
                ) : (
                    <>
                        <div className="space-y-3">
                            <h2 className="text-xl font-semibold">Open Positions</h2>
                            <PortfolioOpenTable data={open} onSell={handleSell} />
                        </div>
                        <div className="space-y-3">
                            <h2 className="text-xl font-semibold">Closed Positions</h2>
                            <PortfolioClosedTable data={closed} onDelete={handleDeleteClosed} />
                        </div>
                    </>
                )}
            </div>
        </DashboardLayout>
    )
}

export default function PortfolioPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>}>
            <PortfolioContent />
        </Suspense>
    )
}
