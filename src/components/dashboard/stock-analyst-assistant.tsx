"use client";

import { Suspense, useState } from "react";
import { usePathname } from "next/navigation";
import { MessageCircle, X } from "lucide-react";
import { AgentChat } from "@/components/dashboard/agent-chat";
import { cn } from "@/lib/utils";

// Mounted once in the root layout (src/app/layout.tsx), not inside
// DashboardLayout - each page re-creates DashboardLayout on navigation,
// but the root layout doesn't, so this is what keeps the conversation
// alive across pages instead of resetting every time you click a nav link.
export function StockAnalystAssistant() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    // No session exists yet on the login page - nothing to chat with, and
    // showing the bubble there just invites a 401.
    if (pathname === "/login") return null;

    return (
        <>
            {/* Always mounted, visibility toggled by class - not {open && <div>}, which would
                unmount AgentChat (and its message state) on every close, not just navigation. */}
            <div
                className={cn(
                    "fixed z-50 bottom-24 right-6",
                    "w-[calc(100vw-3rem)] sm:w-96",
                    "h-[70vh] sm:h-[600px] max-h-[75vh]",
                    "bg-card border rounded-xl shadow-2xl flex-col overflow-hidden",
                    open ? "flex" : "hidden"
                )}
            >
                <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
                    <div>
                        <p className="font-semibold text-sm">Stock Analyst Assistant</p>
                        <p className="text-xs text-muted-foreground">Ask about your portfolio or any ticker</p>
                    </div>
                    <button
                        onClick={() => setOpen(false)}
                        className="h-7 w-7 rounded-md flex items-center justify-center hover:bg-muted transition-colors shrink-0"
                        aria-label="Close Stock Analyst Assistant"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <div className="flex-1 min-h-0 overflow-hidden px-3 pb-3 pt-2">
                    {/* AgentChat reads ?ticker= via useSearchParams, which Next requires a
                        Suspense boundary for - this component is mounted in the root layout,
                        so it wraps every page including the auto-generated /_not-found, and
                        skipping this breaks the production build during static generation. */}
                    <Suspense fallback={null}>
                        <AgentChat />
                    </Suspense>
                </div>
            </div>

            <button
                onClick={() => setOpen((o) => !o)}
                className="fixed z-50 bottom-6 right-6 h-14 w-14 rounded-full shadow-lg flex items-center justify-center bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
                aria-label={open ? "Close Stock Analyst Assistant" : "Open Stock Analyst Assistant"}
            >
                {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
            </button>
        </>
    );
}
