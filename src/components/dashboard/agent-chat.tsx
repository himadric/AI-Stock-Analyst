"use client";

import { useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Bot, Check, ChevronDown, ChevronRight, Loader2, Send, Sparkles, User, Users, Wrench, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
    addToWatchlist,
    streamAgentChat,
    streamMultiAgentAnalysis,
    fetchQuotes,
    addPortfolioPosition,
    sellPortfolioPosition,
    type AgentChatMessage,
} from "@/lib/api";

interface ToolCallEntry {
    tool: string;
    args: Record<string, unknown>;
    status: "running" | "done";
}

interface SubagentEntry {
    id: string;
    label: string;
    status: "running" | "done";
    toolCalls: ToolCallEntry[];
    fullReport?: string;
    expanded?: boolean;
}

interface DisplayMessage {
    role: "user" | "assistant";
    content: string;
    toolCalls?: ToolCallEntry[];
    subagents?: SubagentEntry[];
    streaming?: boolean;
    traceExpanded?: boolean;
}

interface WatchlistProposal {
    ticker: string;
    reason: string;
    status: "pending" | "added" | "dismissed" | "error";
}

// Mirrors WatchlistProposal's gated-confirmation shape exactly - nothing is
// written to the portfolio until the user clicks Confirm. action-specific
// statuses ("bought"/"sold") instead of a shared "added" so the card can
// show the right past-tense label.
interface TradeProposal {
    ticker: string;
    action: "buy" | "sell";
    reason: string;
    status: "pending" | "bought" | "sold" | "dismissed" | "error";
}

const PLACEHOLDER_BUY_SHARES = 10;

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
    const [tradeProposals, setTradeProposals] = useState<TradeProposal[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);
    // useSearchParams reflects the URL's current ?ticker= regardless of where
    // this component is mounted in the tree (it's driven by Next's router
    // context, not file position) - same reasoning usePathname relies on in
    // stock-analyst-assistant.tsx. Falls back to the app's standard default.
    const ticker = useSearchParams().get("ticker") || "AAPL";

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

    function toggleSubagentExpand(messageIndex: number, agentId: string) {
        setMessages((prev) =>
            prev.map((m, i) =>
                i === messageIndex
                    ? {
                          ...m,
                          subagents: m.subagents?.map((a) => (a.id === agentId ? { ...a, expanded: !a.expanded } : a)),
                      }
                    : m
            )
        );
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

    // Dedicated action, not a regular chat turn - takes just the current
    // ticker, not the message history. Reuses the same DisplayMessage shape
    // as send() (so the same markdown/collapse rendering applies to the
    // final synthesized answer), but builds a `subagents` trace per entry
    // instead of a flat `toolCalls` trace.
    async function runMultiAgentAnalysis() {
        if (loading) return;

        setMessages((prev) => [
            ...prev,
            { role: "user", content: `Run full multi-agent analysis on ${ticker}` },
            { role: "assistant", content: "", subagents: [], streaming: true },
        ]);
        setLoading(true);
        scrollToBottom();

        let assistantText = "";

        function updateSubagent(agentId: string, updater: (a: SubagentEntry) => SubagentEntry) {
            updateLast((m) => ({
                ...m,
                subagents: (m.subagents || []).map((a) => (a.id === agentId ? updater(a) : a)),
            }));
        }

        try {
            for await (const event of streamMultiAgentAnalysis(ticker)) {
                if (event.type === "text") {
                    assistantText += event.text;
                    updateLast((m) => ({ ...m, content: assistantText }));
                    scrollToBottom();
                } else if (event.type === "agent_start") {
                    updateLast((m) => ({
                        ...m,
                        subagents: [...(m.subagents || []), { id: event.agent_id, label: event.label, status: "running", toolCalls: [] }],
                    }));
                    scrollToBottom();
                } else if (event.type === "agent_tool_start") {
                    updateSubagent(event.agent_id, (a) => ({
                        ...a,
                        toolCalls: [...a.toolCalls, { tool: event.tool, args: event.args, status: "running" }],
                    }));
                    scrollToBottom();
                } else if (event.type === "agent_tool_end") {
                    updateSubagent(event.agent_id, (a) => {
                        const calls = [...a.toolCalls];
                        for (let j = calls.length - 1; j >= 0; j--) {
                            if (calls[j].tool === event.tool && calls[j].status === "running") {
                                calls[j] = { ...calls[j], status: "done" };
                                break;
                            }
                        }
                        return { ...a, toolCalls: calls };
                    });
                } else if (event.type === "agent_done") {
                    updateSubagent(event.agent_id, (a) => ({ ...a, status: "done", fullReport: event.full_report }));
                } else if (event.type === "trade_proposal") {
                    setTradeProposals((prev) => [
                        ...prev,
                        { ticker: event.ticker, action: event.action, reason: event.reason, status: "pending" },
                    ]);
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

    // Buy uses today's live price as the cost basis (fetched fresh here, not
    // whatever price the coordinator saw mid-analysis) and a placeholder
    // share count - confirmed scope, see PLACEHOLDER_BUY_SHARES. Sell always
    // uses today's live price too, same as a real trade would.
    async function confirmTradeProposal(index: number) {
        const proposal = tradeProposals[index];
        try {
            if (proposal.action === "buy") {
                const quotes = await fetchQuotes([proposal.ticker]);
                const price = quotes?.[0]?.price;
                if (!price) throw new Error("Could not fetch a current price");
                await addPortfolioPosition(proposal.ticker, PLACEHOLDER_BUY_SHARES, price);
                setTradeProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "bought" } : p)));
            } else {
                await sellPortfolioPosition(proposal.ticker);
                setTradeProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "sold" } : p)));
            }
        } catch {
            setTradeProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "error" } : p)));
        }
    }

    function dismissTradeProposal(index: number) {
        setTradeProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "dismissed" } : p)));
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
                            <button
                                onClick={() => runMultiAgentAnalysis()}
                                className="flex items-center gap-1.5 w-full text-left text-xs px-2.5 py-2 rounded-md border border-indigo-500/30 bg-indigo-500/5 hover:bg-indigo-500/10 transition-colors"
                            >
                                <Users className="h-3.5 w-3.5 text-indigo-500 shrink-0" />
                                Run full multi-agent analysis on {ticker}
                            </button>
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
                                    {m.subagents && m.subagents.length > 0 && (
                                        // One card per subagent, stacked (not a grid - the floating
                                        // widget is only ~384px wide, too narrow for side-by-side
                                        // columns to stay legible). Each card is a nested version of
                                        // the single-trace pattern above: its own live spinner/check
                                        // list while running, then an expandable full report.
                                        <div className="mb-2 space-y-1.5">
                                            {m.subagents.map((a) => (
                                                <div key={a.id} className="rounded-md border bg-background/50 p-2">
                                                    <div className="flex items-center gap-1.5 text-xs font-medium">
                                                        {a.status === "running" ? (
                                                            <Loader2 className="h-3 w-3 animate-spin shrink-0 text-indigo-500" />
                                                        ) : (
                                                            <Check className="h-3 w-3 text-green-600 shrink-0" />
                                                        )}
                                                        {a.label}
                                                    </div>
                                                    {a.toolCalls.length > 0 && (
                                                        <div className="mt-1 space-y-0.5 pl-4">
                                                            {a.toolCalls.map((c, ci) => (
                                                                <div key={ci} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                                    {c.status === "running" ? (
                                                                        <Loader2 className="h-2.5 w-2.5 animate-spin shrink-0" />
                                                                    ) : (
                                                                        <Check className="h-2.5 w-2.5 text-green-600 shrink-0" />
                                                                    )}
                                                                    {describeTool(c.tool, c.args)}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {a.status === "done" && a.fullReport && (
                                                        <>
                                                            <button
                                                                onClick={() => toggleSubagentExpand(i, a.id)}
                                                                className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                                            >
                                                                {a.expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                                                {a.expanded ? "Hide full report" : "View full report"}
                                                            </button>
                                                            {a.expanded && (
                                                                <div className="mt-1 pl-4 prose prose-sm dark:prose-invert max-w-none text-xs">
                                                                    <ReactMarkdown>{a.fullReport}</ReactMarkdown>
                                                                </div>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {m.content ? (
                                        <div className="prose prose-sm dark:prose-invert max-w-none">
                                            <ReactMarkdown>{m.content}</ReactMarkdown>
                                        </div>
                                    ) : (
                                        // Shown whenever we're still waiting for the first token of the
                                        // answer, including the gap after the last tool finishes and
                                        // before Claude starts responding - that gap can be several
                                        // seconds (model "thinking" time, not visible any other way) and
                                        // previously showed nothing at all once a tool trace existed,
                                        // which looked identical to a hang.
                                        m.streaming && <Loader2 className="h-4 w-4 animate-spin" />
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

                {tradeProposals.map((p, i) =>
                    p.status === "dismissed" ? null : (
                        <Card key={i} className="border-indigo-500/30">
                            <CardContent className="p-3 flex items-center justify-between gap-3">
                                <div>
                                    <p className="text-sm font-semibold">
                                        {p.action === "buy" ? "Buy" : "Sell"} <span className="text-indigo-500">{p.ticker}</span>
                                        {p.action === "buy" ? ` (${PLACEHOLDER_BUY_SHARES} shares)` : " (your full position)"}?
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        {p.status === "error" ? "Failed to record the trade — try again from the Portfolio page." : p.reason}
                                    </p>
                                </div>
                                {p.status === "pending" ? (
                                    <div className="flex gap-2 shrink-0">
                                        <Button size="sm" variant="outline" onClick={() => dismissTradeProposal(i)}>
                                            <X className="h-4 w-4" />
                                        </Button>
                                        <Button size="sm" onClick={() => confirmTradeProposal(i)}>
                                            <Check className="h-4 w-4 mr-1" /> {p.action === "buy" ? "Buy" : "Sell"}
                                        </Button>
                                    </div>
                                ) : p.status === "bought" || p.status === "sold" ? (
                                    <span className="text-sm text-green-600 flex items-center gap-1 shrink-0">
                                        <Check className="h-4 w-4" /> {p.status === "bought" ? "Bought" : "Sold"}
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
                <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    disabled={loading}
                    onClick={() => runMultiAgentAnalysis()}
                    title={`Run full multi-agent analysis on ${ticker}`}
                    aria-label={`Run full multi-agent analysis on ${ticker}`}
                >
                    <Users className="h-4 w-4" />
                </Button>
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
