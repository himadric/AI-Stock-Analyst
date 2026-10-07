"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowUp, ArrowDown, Trash2 } from "lucide-react"
import { useRouter } from "next/navigation"
import type { PortfolioPosition } from "@/lib/api"

function fmt(n: number | null | undefined, digits = 2) {
  return n == null ? "—" : n.toFixed(digits)
}

function GainLoss({ value, percent }: { value: number | null | undefined; percent: number | null | undefined }) {
  if (value == null) return <span className="text-muted-foreground">—</span>
  const positive = value >= 0
  return (
    <div className={`flex items-center justify-end gap-1 font-mono ${positive ? "text-green-600" : "text-red-600"}`}>
      {positive ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
      ${Math.abs(value).toFixed(2)} ({Math.abs(percent ?? 0).toFixed(2)}%)
    </div>
  )
}

interface OpenTableProps {
  data: PortfolioPosition[];
  onSell: (ticker: string) => void;
}

export function PortfolioOpenTable({ data, onSell }: OpenTableProps) {
  const router = useRouter()

  if (!data || data.length === 0) {
    return <div className="text-center p-8 text-muted-foreground border rounded-md">No open positions</div>
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead className="text-right">Shares</TableHead>
            <TableHead className="text-right">Cost Basis</TableHead>
            <TableHead className="text-right">Current Price</TableHead>
            <TableHead className="text-right">Market Value</TableHead>
            <TableHead className="text-right">Gain/Loss</TableHead>
            <TableHead className="w-[80px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((p) => (
            <TableRow
              key={p.id}
              className="group cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => router.push(`/?ticker=${p.ticker}`)}
            >
              <TableCell className="font-medium">
                <Badge variant="outline" className="bg-background">{p.ticker}</Badge>
              </TableCell>
              <TableCell className="text-right font-mono">{fmt(p.shares)}</TableCell>
              <TableCell className="text-right font-mono">${fmt(p.cost_basis)}</TableCell>
              <TableCell className="text-right font-mono">${fmt(p.current_price)}</TableCell>
              <TableCell className="text-right font-mono">${fmt(p.market_value)}</TableCell>
              <TableCell className="text-right">
                <GainLoss value={p.gain_loss} percent={p.gain_loss_percent} />
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation()
                    onSell(p.ticker)
                  }}
                >
                  Sell
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

interface ClosedTableProps {
  data: PortfolioPosition[];
  onDelete: (id: string) => void;
}

export function PortfolioClosedTable({ data, onDelete }: ClosedTableProps) {
  if (!data || data.length === 0) {
    return <div className="text-center p-8 text-muted-foreground border rounded-md">No closed positions yet</div>
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead className="text-right">Shares</TableHead>
            <TableHead className="text-right">Buy Price</TableHead>
            <TableHead className="text-right">Sell Price</TableHead>
            <TableHead>Sell Date</TableHead>
            <TableHead className="text-right">Realized Gain/Loss</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((p) => (
            <TableRow key={p.id} className="group">
              <TableCell className="font-medium">
                <Badge variant="outline" className="bg-background">{p.ticker}</Badge>
              </TableCell>
              <TableCell className="text-right font-mono">{fmt(p.shares)}</TableCell>
              <TableCell className="text-right font-mono">${fmt(p.cost_basis)}</TableCell>
              <TableCell className="text-right font-mono">${fmt(p.sell_price)}</TableCell>
              <TableCell className="text-muted-foreground">
                {p.sell_date ? new Date(p.sell_date).toLocaleDateString() : "—"}
              </TableCell>
              <TableCell className="text-right">
                <GainLoss value={p.realized_gain_loss} percent={p.realized_gain_loss_percent} />
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={() => onDelete(p.id)}
                  title="Remove this closed position from history"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
