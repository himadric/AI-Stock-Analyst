"use client";

import { BarChart3, FileText, Globe, Home, LayoutDashboard, Search, TrendingUp, Target, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { TickerSearch } from "@/components/dashboard/ticker-search";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const searchParams = useSearchParams();
  const ticker = searchParams.get("ticker") || "AAPL";
  const pathname = usePathname();

  const navItems = [
    { name: "Overview", href: "/", icon: LayoutDashboard },
    { name: "Financials", href: "/financials", icon: BarChart3 },
    { name: "Chart", href: "/chart", icon: TrendingUp },
    { name: "Forecast", href: "/forecast", icon: Target },
    { name: "Ownership", href: "/ownership", icon: Users },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card hidden md:block">
        <div className="p-6 h-full flex flex-col">
          <Link href={`/?ticker=${ticker}`} className="flex items-center gap-2 mb-8 hover:opacity-80 transition-opacity">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold">AI Analyst</h1>
          </Link>

          <nav className="flex-1 space-y-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link 
                  key={item.href}
                  href={`${item.href}?ticker=${ticker}`} 
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    isActive 
                      ? "bg-secondary text-secondary-foreground" 
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto">
            <div className="bg-muted/50 p-4 rounded-lg">
              <h3 className="font-semibold text-sm mb-1">Pro Plan</h3>
              <p className="text-xs text-muted-foreground mb-3">Get advanced AI predictions.</p>
              <Button size="sm" className="w-full">Upgrade</Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b flex items-center justify-between px-6 bg-card">
            <TickerSearch />
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon">
                    <div className="h-8 w-8 rounded-full bg-secondary" />
                </Button>
            </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-auto p-6">
            {children}
        </div>
      </main>
    </div>
  );
}
