"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Check, ChevronDown, ChevronRight, Loader2, Send, Sparkles, User, Wrench, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { addToWatchlist, streamAgentChat, type AgentChatMessage } from "@/lib/api";

interface ToolCallEntry {
    tool: string;
    args: Record<string, unknown>;
    status: "running" | "done";
}

interface DisplayMessage {
    role: "user" | "assistant";
    content: string;
    toolCalls?: ToolCallEntry[];
    streaming?: boolean;
    traceExpanded?: boolean;
}

interface WatchlistProposal {
    ticker: string;
    reason: string;
    status: "pending" | "added" | "dismissed" | "error";
}

const SUGGESTIONS = [
    "Which of my watchlist names look overvalued right now?",
    "Any smart-money convergence on NVDA — Congress, 13F, and the Future Leader score?",
    "What's changed in Apple's most recent 10-Q vs. the one before?",
];

// Turns a tool call into a short, human-readable line for the trace, e.g.
// "company info (NVDA)" instead of "get_company_info" + a raw args object.
function describeTool(tool: string, args: Record<string, unknown>) {
    const label = tool.replace(/^get_/, "").replace(/^propose_/, "propose ").replace(/_/g, " ");
    const tickers = Array.isArray(args?.tickers) ? (args.tickers as string[]).join(", ") : "";
    const arg =
        (args?.ticker as string) || tickers || (args?.query as string) || (args?.category as string) || (args?.url as string) || "";
    return arg ? `${label} (${arg})` : label;
}

export function AgentChat() {
    const [messages, setMessages] = useState<DisplayMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [proposals, setProposals] = useState<WatchlistProposal[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));
    };

    function updateLast(updater: (m: DisplayMessage) => DisplayMessage) {
        setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = updater(next[next.length - 1]);
            return next;
        });
    }

    function toggleTrace(index: number) {
        setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, traceExpanded: !m.traceExpanded } : m)));
    }

    async function send(text: string) {
        const trimmed = text.trim();
        if (!trimmed || loading) return;

        // Only role/content go to the backend - tool-call traces are a
        // frontend-only, per-turn display; the wire format doesn't carry them.
        const history: AgentChatMessage[] = [
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: trimmed },
        ];

        setMessages((prev) => [
            ...prev,
            { role: "user", content: trimmed },
            { role: "assistant", content: "", toolCalls: [], streaming: true },
        ]);
        setInput("");
        setLoading(true);
        scrollToBottom();

        let assistantText = "";

        try {
            for await (const event of streamAgentChat(history)) {
                if (event.type === "text") {
                    assistantText += event.text;
                    updateLast((m) => ({ ...m, content: assistantText }));
                    scrollToBottom();
                } else if (event.type === "tool_start") {
                    updateLast((m) => ({
                        ...m,
                        toolCalls: [...(m.toolCalls || []), { tool: event.tool, args: event.args, status: "running" }],
                    }));
                    scrollToBottom();
                } else if (event.type === "tool_end") {
                    updateLast((m) => {
                        const calls = [...(m.toolCalls || [])];
                        for (let j = calls.length - 1; j >= 0; j--) {
                            if (calls[j].tool === event.tool && calls[j].status === "running") {
                                calls[j] = { ...calls[j], status: "done" };
                                break;
                            }
                        }
                        return { ...m, toolCalls: calls };
                    });
                } else if (event.type === "watchlist_proposal") {
                    setProposals((prev) => [...prev, { ticker: event.ticker, reason: event.reason, status: "pending" }]);
                } else if (event.type === "error") {
                    assistantText += (assistantText ? "\n\n" : "") + `⚠️ ${event.message}`;
                    updateLast((m) => ({ ...m, content: assistantText }));
                }
            }
        } catch (e) {
            const errorText = `⚠️ ${e instanceof Error ? e.message : "Something went wrong reaching the analyst agent."}`;
            updateLast((m) => ({ ...m, content: m.content ? `${m.content}\n\n${errorText}` : errorText }));
        } finally {
            updateLast((m) => ({ ...m, streaming: false }));
            setLoading(false);
            scrollToBottom();
        }
    }

    async function confirmProposal(index: number) {
        const proposal = proposals[index];
        try {
            await addToWatchlist(proposal.ticker);
            setProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "added" } : p)));
        } catch {
            setProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "error" } : p)));
        }
    }

    function dismissProposal(index: number) {
        setProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "dismissed" } : p)));
    }

    return (
        <div className="flex flex-col h-full min-h-0">
            <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                {messages.length === 0 && (
                    <Card>
                        <CardContent className="p-4 space-y-3">
                            <div className="flex items-center gap-2 text-base font-semibold">
                                <Sparkles className="h-4 w-4 text-indigo-500" />
                                Ask the analyst
                            </div>
                            <p className="text-xs text-muted-foreground">
                                It reads live data across this app before answering, and shows its work as it goes.
                                It can suggest watchlist additions, but it never adds one without your confirmation,
                                and it can&apos;t place trades.
                            </p>
                            <div className="space-y-1.5">
                                {SUGGESTIONS.map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => send(s)}
                                        className="block w-full text-left text-xs px-2.5 py-2 rounded-md border hover:bg-muted transition-colors"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {messages.map((m, i) => (
                    <div key={i} className={cn("flex gap-2", m.role === "user" && "justify-end")}>
                        {m.role === "assistant" && (
                            <div className="h-7 w-7 rounded-full bg-secondary flex items-center justify-center shrink-0">
                                <Bot className="h-3.5 w-3.5" />
                            </div>
                        )}
                        <div
                            className={cn(
                                "rounded-lg px-3 py-2 max-w-[85%] text-sm",
                                m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                            )}
                        >
                            {m.role === "assistant" ? (
                                <>
                                    {m.toolCalls && m.toolCalls.length > 0 && (
                                        <div className="mb-1.5">
                                            {m.streaming ? (
                                                // Live, verbose trace while the turn is in progress.
                                                <div className="space-y-1">
                                                    {m.toolCalls.map((c, ci) => (
                                                        <div key={ci} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                            {c.status === "running" ? (
                                                                <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                                                            ) : (
                                                                <Check className="h-3 w-3 text-green-600 shrink-0" />
                                                            )}
                                                            {describeTool(c.tool, c.args)}
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                // Collapsed once the answer is ready - click to inspect what it did.
                                                <button
                                                    onClick={() => toggleTrace(i)}
                                                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                                >
                                                    {m.traceExpanded ? (
                                                        <ChevronDown className="h-3 w-3" />
                                                    ) : (
                                                        <ChevronRight className="h-3 w-3" />
                                                    )}
                                                    <Wrench className="h-3 w-3" />
                                                    Used {m.toolCalls.length} tool{m.toolCalls.length > 1 ? "s" : ""}
                                                </button>
                                            )}
                                            {!m.streaming && m.traceExpanded && (
                                                <div className="mt-1 space-y-1 pl-4 border-l-2 border-border">
                                                    {m.toolCalls.map((c, ci) => (
                                                        <div key={ci} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                            <Check className="h-3 w-3 text-green-600 shrink-0" />
                                                            {describeTool(c.tool, c.args)}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                    {m.content ? (
                                        <div className="prose prose-sm dark:prose-invert max-w-none">
                                            <ReactMarkdown>{m.content}</ReactMarkdown>
                                        </div>
                                    ) : (
                                        !m.toolCalls?.length && <Loader2 className="h-4 w-4 animate-spin" />
                                    )}
                                </>
                            ) : (
                                m.content
                            )}
                        </div>
                        {m.role === "user" && (
                            <div className="h-7 w-7 rounded-full bg-secondary flex items-center justify-center shrink-0">
                                <User className="h-3.5 w-3.5" />
                            </div>
                        )}
                    </div>
                ))}

                {proposals.map((p, i) =>
                    p.status === "dismissed" ? null : (
                        <Card key={i} className="border-indigo-500/30">
                            <CardContent className="p-3 flex items-center justify-between gap-3">
                                <div>
                                    <p className="text-sm font-semibold">
                                        Add <span className="text-indigo-500">{p.ticker}</span> to your watchlist?
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {p.status === "error" ? "Failed to add — try again from the Watchlist page." : p.reason}
                                    </p>
                                </div>
                                {p.status === "pending" ? (
                                    <div className="flex gap-2 shrink-0">
                                        <Button size="sm" variant="outline" onClick={() => dismissProposal(i)}>
                                            <X className="h-4 w-4" />
                                        </Button>
                                        <Button size="sm" onClick={() => confirmProposal(i)}>
                                            <Check className="h-4 w-4 mr-1" /> Add
                                        </Button>
                                    </div>
                                ) : p.status === "added" ? (
                                    <span className="text-sm text-green-600 flex items-center gap-1 shrink-0">
                                        <Check className="h-4 w-4" /> Added
                                    </span>
                                ) : null}
                            </CardContent>
                        </Card>
                    )
                )}
                <div ref={bottomRef} />
            </div>

            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    send(input);
                }}
                className="flex gap-2 pt-2 border-t"
            >
                <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about a ticker, your watchlist, or the market…"
                    disabled={loading}
                />
                <Button type="submit" disabled={loading || !input.trim()}>
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
            </form>
        </div>
    );
}
