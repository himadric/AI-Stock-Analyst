"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { searchTickers } from "@/lib/api";
import { cn } from "@/lib/utils";

export function TickerSearch() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (query.length > 1) {
        setLoading(true);
        try {
            const data = await searchTickers(query);
            setResults(data);
            setOpen(true);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
      } else {
        setResults([]);
        setOpen(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const handleSelect = (ticker: string) => {
    router.push(`/?ticker=${ticker}`);
    setOpen(false);
    setQuery("");
  }

  return (
    <div className="relative w-96 z-50">
      <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input 
        placeholder="Search ticker (e.g. AAPL)..." 
        className="pl-9" 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setOpen(true); }}
        onBlur={() => { setTimeout(() => setOpen(false), 200); }} 
      />
      
      {open && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full rounded-md border bg-popover text-popover-foreground shadow-md outline-none animate-in fade-in-0 zoom-in-95">
            <div className="p-1">
                {results.map((item) => (
                    <div 
                        key={item.ticker}
                        className={cn(
                            "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground",
                        )}
                        onMouseDown={(e) => {
                            e.preventDefault(); // Prevent input blur
                            handleSelect(item.ticker);
                        }}
                    >
                        <span className="font-bold w-16">{item.ticker}</span>
                        <span className="text-muted-foreground truncate">{item.title}</span>
                    </div>
                ))}
            </div>
        </div>
      )}
      {loading && open && (
        <div className="absolute top-full mt-2 w-full p-2 bg-popover border rounded-md shadow-md flex justify-center">
            <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      )}
    </div>
  );
}
