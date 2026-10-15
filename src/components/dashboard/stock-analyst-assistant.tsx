"use client";

import { Suspense, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { usePathname } from "next/navigation";
import { MessageCircle, X } from "lucide-react";
import { AgentChat } from "@/components/dashboard/agent-chat";
import { cn } from "@/lib/utils";

const DEFAULT_WIDTH = 384; // matches the old fixed w-96
const MIN_WIDTH = 320;
const MAX_WIDTH = 800;
const WIDTH_STORAGE_KEY = "chatWidgetWidth";

// Mounted once in the root layout (src/app/layout.tsx), not inside
// DashboardLayout - each page re-creates DashboardLayout on navigation,
// but the root layout doesn't, so this is what keeps the conversation
// alive across pages instead of resetting every time you click a nav link.
export function StockAnalystAssistant() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    // Only matters on desktop - on mobile the panel stays full-width-minus-
    // margin (the existing w-[calc(100vw-3rem)] class) and there's no mouse
    // to drag with anyway. Starts false to match the server-rendered HTML;
    // set for real in an effect so there's no SSR/client mismatch.
    const [isDesktop, setIsDesktop] = useState(false);
    const draggingRef = useRef(false);

    useEffect(() => {
        const mq = window.matchMedia("(min-width: 640px)");
        setIsDesktop(mq.matches);
        const onChange = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
        mq.addEventListener("change", onChange);
        return () => mq.removeEventListener("change", onChange);
    }, []);

    useEffect(() => {
        try {
            const saved = localStorage.getItem(WIDTH_STORAGE_KEY);
            if (saved) {
                const parsed = Number(saved);
                if (Number.isFinite(parsed)) setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, parsed)));
            }
        } catch {
            // localStorage can throw (private browsing, blocked storage) -
            // falling back to DEFAULT_WIDTH is fine, not worth surfacing.
        }
    }, []);

    function startResize(e: ReactMouseEvent) {
        e.preventDefault();
        draggingRef.current = true;
        const startX = e.clientX;
        const startWidth = width;

        function onMouseMove(moveEvent: MouseEvent) {
            if (!draggingRef.current) return;
            // The panel is right-anchored (right-6), so dragging its LEFT
            // edge further left should grow it - moving left decreases
            // clientX, so (startX - clientX) is positive in that direction.
            const next = startWidth + (startX - moveEvent.clientX);
            const maxAllowed = Math.min(MAX_WIDTH, window.innerWidth - 48);
            setWidth(Math.min(maxAllowed, Math.max(MIN_WIDTH, next)));
        }

        function onMouseUp() {
            draggingRef.current = false;
            document.removeEventListener("mousemove", onMouseMove);
            document.removeEventListener("mouseup", onMouseUp);
            setWidth((w) => {
                try {
                    localStorage.setItem(WIDTH_STORAGE_KEY, String(w));
                } catch {
                    // Same reasoning as the load above - a failed save just
                    // means the width resets next visit, not worth surfacing.
                }
                return w;
            });
        }

        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    }

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
                style={isDesktop ? { width: `${width}px` } : undefined}
            >
                {/* Drag handle - only usable with a mouse, so only rendered
                    on desktop; mobile keeps the full-width-minus-margin layout. */}
                {isDesktop && (
                    <div
                        onMouseDown={startResize}
                        className="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-primary/30 active:bg-primary/40 transition-colors z-10"
                        title="Drag to resize"
                    />
                )}
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
