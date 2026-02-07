"use client";

import { BarChart3, FileText, Globe, Home, LayoutDashboard, Search, TrendingUp, Target, Users, Menu, Trophy, Shield, Landmark, Building2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { TickerSearch } from "@/components/dashboard/ticker-search";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from "@/components/ui/sheet";

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
    { name: "Simulation", href: "/simulation", icon: TrendingUp },
    { name: "Forecast", href: "/forecast", icon: Target },
    { name: "Ownership", href: "/ownership", icon: Users },
    { name: "Brand Sentiment", href: "/sentiment", icon: Users },
    { name: "Watchlist", href: "/watchlist", icon: FileText },
    { name: "Finder", href: "/finder", icon: Search },
    { name: "Market Heatmap", href: "/heatmap", icon: LayoutDashboard }, // Using LayoutDashboard or similar
    { name: "Institutional Trackers", href: "/institutional", icon: Building2 },
    { name: "US House Tracker", href: "/house", icon: Landmark },
    { name: "US Senate Tracker", href: "/senate", icon: Landmark },
    { name: "Rankings", href: "/rankings", icon: Trophy },
    { name: "Govt Spending Tracker", href: "/govt", icon: Shield },
    { name: "Macro", href: "/macro", icon: Globe },
  ];

  const SidebarContent = () => (
    <div className="h-full flex flex-col">
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
            <div key={item.href}>
                {item.name === "Watchlist" && <div className="my-2 mx-3 border-t border-border" />}
                <Link 
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
            </div>
          );
        })}
      </nav>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar (Desktop) */}
      <aside className="w-64 border-r bg-card hidden md:block">
        <div className="p-6 h-full">
            <SidebarContent />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b flex items-center justify-between px-6 bg-card shrink-0">
            {/* Mobile Menu Trigger */}
            <div className="md:hidden mr-4">
                <Sheet>
                    <SheetTrigger asChild>
                        <Button variant="ghost" size="icon">
                            <Menu className="h-5 w-5" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="p-6 w-64">
                         <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
                         <SheetDescription className="sr-only">
                            Main navigation sidebar
                         </SheetDescription>
                         <SidebarContent />
                    </SheetContent>
                </Sheet>
            </div>

            <TickerSearch />
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon">
                    <div className="h-8 w-8 rounded-full bg-secondary" />
                </Button>
            </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-auto p-4 md:p-6">
            {children}
        </div>
      </main>
    </div>
  );
}
