"use client";

import { useRef, useState, type ClipboardEvent } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Bot, Check, ChevronDown, ChevronRight, Loader2, RotateCcw, Send, ShieldAlert, ShieldCheck, Sparkles, Square, User, Users, Wrench, X, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import {
    addToWatchlist,
    streamAgentChat,
    streamMultiAgentAnalysis,
    fetchQuotes,
    addPortfolioPosition,
    sellPortfolioPosition,
    type AgentChatMessage,
    type AgentContentBlock,
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

interface Citation {
    citedText: string;
    source: string | null;
    title: string | null;
}

interface Groundedness {
    confidenceScore: number;
    verdict: "grounded" | "partially_grounded" | "ungrounded";
    flaggedClaims: { claim: string; issue: string }[];
    reasoning: string;
    expanded?: boolean;
}

interface Reflection {
    needsRevision: boolean;
    critique: string;
    revisedAnswer?: string;
}

interface DisplayMessage {
    role: "user" | "assistant";
    content: string;
    toolCalls?: ToolCallEntry[];
    subagents?: SubagentEntry[];
    streaming?: boolean;
    traceExpanded?: boolean;
    // Display-only: a pasted image shown in the transcript so a past turn
    // like "what's wrong with this chart" still makes sense when scrolled
    // back to. Separate from what actually gets sent to the backend (see
    // send()), which builds its own Anthropic content-block array.
    image?: string;
    // From search_filings results with citations enabled (Anthropic's
    // citations feature) - real source grounding, not the model's own
    // claim. Deduped by (source, citedText) as they stream in, since the
    // same chunk can back more than one sentence in the final answer.
    citations?: Citation[];
    // Prompt caching stats, summed across this message's internal tool-call
    // rounds (a single question can span several). cacheCreated is only
    // ever non-zero on the round that first creates the cache; cacheRead
    // is the system prompt + tool schemas reused from cache on every round
    // after that, in this conversation or an earlier one within the TTL.
    usage?: { cacheCreated: number; cacheRead: number };
    // LLM-as-judge: a second, cheaper model (Haiku) checking this answer
    // against the real tool data it was based on - see
    // api/app/agent/groundedness_judge.py. Undefined until the
    // "groundedness" event lands (which can take a second or two after the
    // visible answer finishes - see the "Verifying groundedness" indicator
    // below), and never set at all for a turn with no tool calls.
    groundedness?: Groundedness;
    // Opt-in self-critique (see api/app/agent/reflection.py) - the SAME
    // model reviewing and possibly rewriting its own draft, a different
    // technique from groundedness. reflectRequested is stamped at send()
    // time from the toggle's value then (not read live later), so a
    // mid-stream toggle flip can't relabel an in-flight message.
    reflectRequested?: boolean;
    reflection?: Reflection;
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
//
// Trades under AUTO_EXECUTE_THRESHOLD (see multi_agent.py) skip this
// confirm/dismiss step entirely - they arrive as a trade_executed event,
// already bought/sold by the time the frontend sees them. `auto` marks
// those so the card can say "auto-executed" instead of implying a button
// was clicked; `shares`/`price` are only populated for that case, since a
// human-confirmed trade's price is fetched live at confirm time instead.
interface TradeProposal {
    ticker: string;
    action: "buy" | "sell";
    reason: string;
    status: "pending" | "bought" | "sold" | "dismissed" | "error";
    auto?: boolean;
    shares?: number;
    price?: number;
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
        (args?.ticker as string) || tickers || (args?.query as string) || (args?.category as string) ||
        (args?.url as string) || (args?.skill_id as string) || "";
    return arg ? `${label} (${arg})` : label;
}

// Splits a "data:image/png;base64,AAAA..." URL into Anthropic's expected
// {media_type, data} shape. FileReader.readAsDataURL() always produces
// this exact format, so no validation beyond the split itself.
function parseDataUrl(dataUrl: string): { mediaType: string; data: string } {
    const [header, data] = dataUrl.split(",", 2);
    const mediaType = header.match(/data:(.*?);base64/)?.[1] || "image/png";
    return { mediaType, data };
}

export function AgentChat() {
    const [messages, setMessages] = useState<DisplayMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    // Shared by send() and runMultiAgentAnalysis() - only one of either can
    // be in flight at a time anyway (both gate on the same `loading` state),
    // so one ref covers whichever is currently running.
    const abortControllerRef = useRef<AbortController | null>(null);
    // A pasted image waiting to be sent with the next message - cleared
    // once send() uses it. Claude reads it natively alongside tool calls in
    // the same turn, unlike the one-shot, tool-free Chart page analysis.
    const [attachedImage, setAttachedImage] = useState<string | null>(null);
    // Opt-in self-critique toggle (see api/app/agent/reflection.py) - off
    // by default, session-only (not localStorage, matching this widget's
    // existing client-only-history philosophy). send() stamps its value
    // onto each new message at send time via reflectRequested.
    const [reflectEnabled, setReflectEnabled] = useState(false);
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

    function toggleGroundedness(index: number) {
        setMessages((prev) =>
            prev.map((m, i) =>
                i === index && m.groundedness ? { ...m, groundedness: { ...m.groundedness, expanded: !m.groundedness.expanded } } : m,
            ),
        );
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
        if ((!trimmed && !attachedImage) || loading) return;

        // The new message's content is a plain string, same as every prior
        // turn, unless an image is attached - then it's Anthropic content
        // blocks (text + image) instead. Claude reads the image natively
        // alongside whatever tools it calls in the same turn; this isn't a
        // separate one-shot analysis the way the Chart page's is.
        let newContent: AgentChatMessage["content"] = trimmed;
        if (attachedImage) {
            const { mediaType, data } = parseDataUrl(attachedImage);
            const blocks: AgentContentBlock[] = [
                { type: "text", text: trimmed || "Please analyze this image." },
                { type: "image", source: { type: "base64", media_type: mediaType, data } },
            ];
            newContent = blocks;
        }

        // Only role/content go to the backend - tool-call traces are a
        // frontend-only, per-turn display; the wire format doesn't carry them.
        const history: AgentChatMessage[] = [
            ...messages.map((m) => ({ role: m.role, content: m.content })),
            { role: "user", content: newContent },
        ];

        setMessages((prev) => [
            ...prev,
            { role: "user", content: trimmed, image: attachedImage ?? undefined },
            { role: "assistant", content: "", toolCalls: [], streaming: true, reflectRequested: reflectEnabled },
        ]);
        setInput("");
        setAttachedImage(null);
        setLoading(true);
        scrollToBottom();

        let assistantText = "";
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            for await (const event of streamAgentChat(history, controller.signal, reflectEnabled)) {
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
                } else if (event.type === "citation") {
                    updateLast((m) => {
                        const existing = m.citations || [];
                        const isDupe = existing.some((c) => c.source === event.source && c.citedText === event.cited_text);
                        if (isDupe) return m;
                        return { ...m, citations: [...existing, { citedText: event.cited_text, source: event.source, title: event.title }] };
                    });
                } else if (event.type === "usage") {
                    updateLast((m) => {
                        const prev = m.usage || { cacheCreated: 0, cacheRead: 0 };
                        return {
                            ...m,
                            usage: {
                                cacheCreated: prev.cacheCreated + event.cache_creation_input_tokens,
                                cacheRead: prev.cacheRead + event.cache_read_input_tokens,
                            },
                        };
                    });
                } else if (event.type === "reflection") {
                    updateLast((m) => ({
                        ...m,
                        reflection: {
                            needsRevision: event.needs_revision,
                            critique: event.critique,
                            revisedAnswer: event.revised_answer,
                        },
                    }));
                } else if (event.type === "groundedness") {
                    updateLast((m) => ({
                        ...m,
                        groundedness: {
                            confidenceScore: event.confidence_score,
                            verdict: event.verdict,
                            flaggedClaims: event.flagged_claims,
                            reasoning: event.reasoning,
                        },
                    }));
                } else if (event.type === "error") {
                    assistantText += (assistantText ? "\n\n" : "") + `⚠️ ${event.message}`;
                    updateLast((m) => ({ ...m, content: assistantText }));
                }
            }
        } catch (e) {
            if (e instanceof DOMException && e.name === "AbortError") {
                // User-initiated stop, not a real failure - keep whatever
                // text/tool trace already streamed in, just note it was cut
                // short rather than showing a scary error.
                updateLast((m) => ({ ...m, content: m.content ? `${m.content}\n\n_(stopped)_` : "_(stopped)_" }));
            } else {
                const errorText = `⚠️ ${e instanceof Error ? e.message : "Something went wrong reaching the analyst agent."}`;
                updateLast((m) => ({ ...m, content: m.content ? `${m.content}\n\n${errorText}` : errorText }));
            }
        } finally {
            abortControllerRef.current = null;
            updateLast((m) => ({ ...m, streaming: false }));
            setLoading(false);
            scrollToBottom();
        }
    }

    // Handles a pasted screenshot (e.g. Cmd+V after a screen capture) -
    // reads the clipboard's image data directly, no file picker needed.
    // Plain pasted text is untouched; only an actual image item triggers this.
    function handlePaste(e: ClipboardEvent<HTMLTextAreaElement>) {
        const imageItem = Array.from(e.clipboardData.items).find((item) => item.type.startsWith("image/"));
        if (!imageItem) return;
        e.preventDefault();
        const file = imageItem.getAsFile();
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => setAttachedImage(reader.result as string);
        reader.readAsDataURL(file);
    }

    // Dedicated action, not a regular chat turn - takes just the current
    // ticker, not the message history. Reuses the same DisplayMessage shape
    // as send() (so the same markdown/collapse rendering applies to the
    // final synthesized answer), but builds a `subagents` trace per entry
    // instead of a flat `toolCalls` trace.
    async function runMultiAgentAnalysis() {
        if (loading) return;

        // Reuses whatever image is already attached from a paste (same
        // state send() uses) - goes to the coordinator's synthesis only,
        // not to the four subagents. See streamMultiAgentAnalysis's comment.
        const chartImage = attachedImage ?? undefined;

        setMessages((prev) => [
            ...prev,
            { role: "user", content: `Run full multi-agent analysis on ${ticker}`, image: chartImage },
            { role: "assistant", content: "", subagents: [], streaming: true },
        ]);
        setAttachedImage(null);
        setLoading(true);
        scrollToBottom();

        let assistantText = "";
        const controller = new AbortController();
        abortControllerRef.current = controller;

        function updateSubagent(agentId: string, updater: (a: SubagentEntry) => SubagentEntry) {
            updateLast((m) => ({
                ...m,
                subagents: (m.subagents || []).map((a) => (a.id === agentId ? updater(a) : a)),
            }));
        }

        try {
            for await (const event of streamMultiAgentAnalysis(ticker, controller.signal, chartImage)) {
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
                } else if (event.type === "trade_executed") {
                    setTradeProposals((prev) => [
                        ...prev,
                        {
                            ticker: event.ticker,
                            action: event.action,
                            reason: event.reason,
                            status: event.action === "buy" ? "bought" : "sold",
                            auto: true,
                            shares: event.shares,
                            price: event.price,
                        },
                    ]);
                } else if (event.type === "groundedness") {
                    updateLast((m) => ({
                        ...m,
                        groundedness: {
                            confidenceScore: event.confidence_score,
                            verdict: event.verdict,
                            flaggedClaims: event.flagged_claims,
                            reasoning: event.reasoning,
                        },
                    }));
                } else if (event.type === "error") {
                    assistantText += (assistantText ? "\n\n" : "") + `⚠️ ${event.message}`;
                    updateLast((m) => ({ ...m, content: assistantText }));
                }
            }
        } catch (e) {
            if (e instanceof DOMException && e.name === "AbortError") {
                updateLast((m) => ({ ...m, content: m.content ? `${m.content}\n\n_(stopped)_` : "_(stopped)_" }));
            } else {
                const errorText = `⚠️ ${e instanceof Error ? e.message : "Something went wrong reaching the analyst agent."}`;
                updateLast((m) => ({ ...m, content: m.content ? `${m.content}\n\n${errorText}` : errorText }));
            }
        } finally {
            abortControllerRef.current = null;
            updateLast((m) => ({ ...m, streaming: false }));
            setLoading(false);
            scrollToBottom();
        }
    }

    function stop() {
        abortControllerRef.current?.abort();
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
                                    {!m.streaming && m.usage && (m.usage.cacheCreated > 0 || m.usage.cacheRead > 0) && (
                                        // Prompt caching made visible - the system prompt + tool
                                        // schemas (thousands of tokens, identical on every round)
                                        // reused from cache instead of reprocessed. cacheCreated is
                                        // normally only non-zero the first time in a while this
                                        // conversation (or an earlier one, within the cache's 5-minute
                                        // TTL) sent that prefix; cacheRead is every round after that.
                                        <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
                                            <Zap className="h-3 w-3 text-amber-500" />
                                            {[
                                                m.usage.cacheCreated > 0 ? `${m.usage.cacheCreated.toLocaleString()} tokens cached` : null,
                                                m.usage.cacheRead > 0 ? `${m.usage.cacheRead.toLocaleString()} tokens read from cache` : null,
                                            ].filter(Boolean).join(" · ")}
                                        </p>
                                    )}
                                    {!m.streaming && m.citations && m.citations.length > 0 && (
                                        // Real source grounding (Anthropic's citations feature, via
                                        // search_filings) - each one is a specific filing excerpt the
                                        // model actually drew on, not a claim to take on faith. Shown
                                        // only once the turn finishes, not live, since the dedup order
                                        // can shift mid-stream and a footnote list reads better finished.
                                        <div className="mt-2 pt-2 border-t border-border/50">
                                            <p className="text-xs font-medium text-muted-foreground mb-1">
                                                Sources ({m.citations.length})
                                            </p>
                                            <ol className="space-y-1 text-xs text-muted-foreground list-decimal list-inside">
                                                {m.citations.map((c, ci) => (
                                                    <li key={ci}>
                                                        {c.source ? (
                                                            <a href={c.source} target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground" title={c.citedText}>
                                                                {c.title || c.source}
                                                            </a>
                                                        ) : (
                                                            <span title={c.citedText}>{c.title || "Source"}</span>
                                                        )}
                                                    </li>
                                                ))}
                                            </ol>
                                        </div>
                                    )}
                                    {m.streaming && m.content && m.reflectRequested && !m.reflection && (
                                        // The self-critique pass (reflection.py) runs before groundedness
                                        // and uses the full Sonnet model, so this gap can run a few
                                        // seconds longer than the groundedness one below.
                                        <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
                                            <Loader2 className="h-3 w-3 animate-spin" /> Reflecting on this answer…
                                        </p>
                                    )}
                                    {!m.streaming && m.reflection && (
                                        // Opt-in self-critique (reflection.py) - the SAME model reviewing
                                        // its own draft. The original draft above is left untouched; a
                                        // revision is shown as a clearly separate section below it, never
                                        // a silent swap, so the improvement is visible, not hidden.
                                        <div className="mt-2 pt-2 border-t border-border/50">
                                            {m.reflection.needsRevision ? (
                                                <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-2">
                                                    <p className="flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                                                        <RotateCcw className="h-3 w-3" /> Revised on review
                                                    </p>
                                                    <p className="mt-1 text-xs text-muted-foreground">{m.reflection.critique}</p>
                                                    {m.reflection.revisedAnswer && (
                                                        <div className="prose prose-sm dark:prose-invert max-w-none mt-2">
                                                            <ReactMarkdown>{m.reflection.revisedAnswer}</ReactMarkdown>
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Check className="h-3 w-3" /> Reviewed — no changes needed
                                                </p>
                                            )}
                                        </div>
                                    )}
                                    {m.streaming && m.content && (!m.reflectRequested || m.reflection) && !m.groundedness && (
                                        // The judge call (groundedness_judge.py) happens after the visible
                                        // answer (and any reflection pass) is already complete, so there's
                                        // a silent 1-2s gap here before "done" fires - without this line it
                                        // can read as a stall. Held off until reflection resolves, if it
                                        // was requested, so the two gap messages don't overlap.
                                        <p className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
                                            <Loader2 className="h-3 w-3 animate-spin" /> Verifying groundedness…
                                        </p>
                                    )}
                                    {!m.streaming && m.groundedness && (
                                        // LLM-as-judge: a second, cheaper model (Haiku) checked this
                                        // answer's claims against the real tool data it was based on -
                                        // see api/app/agent/groundedness_judge.py. Color threshold
                                        // matches this app's existing green/red semantic convention.
                                        <div className="mt-2 pt-2 border-t border-border/50">
                                            <button
                                                onClick={() => m.groundedness!.flaggedClaims.length > 0 && toggleGroundedness(i)}
                                                className={cn(
                                                    "flex items-center gap-1 text-xs font-medium",
                                                    m.groundedness.flaggedClaims.length > 0 && "cursor-pointer hover:opacity-80",
                                                    m.groundedness.confidenceScore >= 85
                                                        ? "text-emerald-600 dark:text-emerald-400"
                                                        : m.groundedness.confidenceScore >= 50
                                                          ? "text-amber-600 dark:text-amber-400"
                                                          : "text-destructive",
                                                )}
                                            >
                                                {m.groundedness.confidenceScore >= 50 ? (
                                                    <ShieldCheck className="h-3 w-3" />
                                                ) : (
                                                    <ShieldAlert className="h-3 w-3" />
                                                )}
                                                {m.groundedness.confidenceScore}% grounded
                                                {m.groundedness.flaggedClaims.length > 0 && (
                                                    <>
                                                        · {m.groundedness.flaggedClaims.length} flagged claim{m.groundedness.flaggedClaims.length > 1 ? "s" : ""}
                                                        {m.groundedness.expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                                    </>
                                                )}
                                            </button>
                                            {m.groundedness.expanded && m.groundedness.flaggedClaims.length > 0 && (
                                                <>
                                                    <ul className="mt-1 space-y-1 text-xs text-muted-foreground pl-4 list-disc">
                                                        {m.groundedness.flaggedClaims.map((f, fi) => (
                                                            <li key={fi}>
                                                                <span className="italic">&quot;{f.claim}&quot;</span> — {f.issue}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                    <p className="mt-1 text-xs text-muted-foreground">{m.groundedness.reasoning}</p>
                                                </>
                                            )}
                                        </div>
                                    )}
                                </>
                            ) : (
                                <>
                                    {m.image && (
                                        <img
                                            src={m.image}
                                            alt="Image sent to the analyst agent"
                                            className="rounded-md mb-1.5 max-h-40 w-auto"
                                        />
                                    )}
                                    {m.content}
                                </>
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
                                        {p.status === "error"
                                            ? "Failed to record the trade — try again from the Portfolio page."
                                            : p.auto
                                              ? `Auto-executed (under $1,000, no confirmation needed) — ${p.shares} shares at $${p.price?.toFixed(2)}. ${p.reason}`
                                              : p.reason}
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

            <div className="flex items-center justify-between gap-2 pt-2 border-t">
                <label htmlFor="reflect-toggle" className="text-xs text-muted-foreground">
                    Reflect before finalizing
                    <span className="block text-[10px] opacity-75">A second Sonnet pass reviews and can revise each answer — slower, off by default</span>
                </label>
                <Switch id="reflect-toggle" checked={reflectEnabled} onCheckedChange={setReflectEnabled} />
            </div>
            {attachedImage && (
                <div className="flex items-center gap-2 pt-2">
                    <img src={attachedImage} alt="Pasted image to send" className="h-12 w-12 rounded border object-cover" />
                    <span className="text-xs text-muted-foreground flex-1">Image attached — will be sent with your next message or multi-agent analysis</span>
                    <Button type="button" variant="ghost" size="icon" className="h-6 w-6" onClick={() => setAttachedImage(null)}>
                        <X className="h-3.5 w-3.5" />
                    </Button>
                </div>
            )}
            <form
                onSubmit={(e) => {
                    e.preventDefault();
                    send(input);
                }}
                className="flex gap-2 pt-2"
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
                <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onPaste={handlePaste}
                    onKeyDown={(e) => {
                        // Enter sends, Shift+Enter inserts a newline - the
                        // standard chat convention. Without this, Enter would
                        // just insert a newline too (a <textarea>'s default),
                        // leaving no way to submit from the keyboard.
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            send(input);
                        }
                    }}
                    placeholder="Ask about a ticker, your watchlist, or paste a chart screenshot… (Shift+Enter for a new line)"
                    disabled={loading}
                    rows={1}
                    className="min-h-10 max-h-32 resize-none py-2"
                />
                {loading ? (
                    <Button type="button" variant="destructive" onClick={stop} title="Stop" aria-label="Stop">
                        <Square className="h-3.5 w-3.5 fill-current" />
                    </Button>
                ) : (
                    <Button type="submit" disabled={!input.trim() && !attachedImage}>
                        <Send className="h-4 w-4" />
                    </Button>
                )}
            </form>
        </div>
    );
}
