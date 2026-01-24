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
import { X, ArrowUp, ArrowDown } from "lucide-react"
import { useRouter } from "next/navigation"

interface WatchlistItem {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

interface WatchlistTableProps {
  data: WatchlistItem[];
  onRemove: (ticker: string) => void;
}

export function WatchlistTable({ data, onRemove }: WatchlistTableProps) {
  const router = useRouter();

  if (!data || data.length === 0) {
    return <div className="text-center p-8 text-muted-foreground border rounded-md">No stocks in watchlist</div>
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Symbol</TableHead>
            <TableHead>Company</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="text-right">Change</TableHead>
            <TableHead className="text-right">% Change</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((item) => (
            <TableRow 
                key={item.ticker} 
                className="group cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => router.push(`/?ticker=${item.ticker}`)}
            >
              <TableCell className="font-medium">
                <Badge variant="outline" className="bg-background">
                    {item.ticker}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{item.name}</TableCell>
              <TableCell className="text-right font-mono">
                ${item.price.toFixed(2)}
              </TableCell>
              <TableCell className={`text-right font-mono ${item.change >= 0 ? "text-green-600" : "text-red-600"}`}>
                {item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}
              </TableCell>
              <TableCell className={`text-right font-mono ${item.change_percent >= 0 ? "text-green-600" : "text-red-600"}`}>
                 <div className="flex items-center justify-end gap-1">
                    {item.change_percent >= 0 ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
                    {Math.abs(item.change_percent).toFixed(2)}%
                 </div>
              </TableCell>
              <TableCell>
                <Button 
                    variant="ghost" 
                    size="icon" 
                    className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                        e.stopPropagation();
                        onRemove(item.ticker);
                    }}
                >
                    <X className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
