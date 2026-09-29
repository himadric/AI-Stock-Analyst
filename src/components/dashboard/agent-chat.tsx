"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, Check, Loader2, Send, Sparkles, User, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { addToWatchlist, streamAgentChat, type AgentChatMessage } from "@/lib/api";

interface DisplayMessage {
    role: "user" | "assistant";
    content: string;
}

interface WatchlistProposal {
    ticker: string;
    reason: string;
    status: "pending" | "added" | "dismissed";
}

const SUGGESTIONS = [
    "Which of my watchlist names look overvalued right now?",
    "Any smart-money convergence on NVDA — Congress, 13F, and the Future Leader score?",
    "What's changed in Apple's most recent 10-Q vs. the one before?",
];

export function AgentChat() {
    const [messages, setMessages] = useState<DisplayMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [statusLine, setStatusLine] = useState<string | null>(null);
    const [proposals, setProposals] = useState<WatchlistProposal[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));
    };

    async function send(text: string) {
        const trimmed = text.trim();
        if (!trimmed || loading) return;

        const history: AgentChatMessage[] = [...messages, { role: "user", content: trimmed }];
        setMessages(history);
        setInput("");
        setLoading(true);
        setStatusLine(null);
        scrollToBottom();

        let assistantText = "";
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

        try {
            for await (const event of streamAgentChat(history)) {
                if (event.type === "text") {
                    assistantText += event.text;
                    setMessages((prev) => {
                        const next = [...prev];
                        next[next.length - 1] = { role: "assistant", content: assistantText };
                        return next;
                    });
                    scrollToBottom();
                } else if (event.type === "tool_start") {
                    const ticker = (event.args?.ticker as string) || (event.args?.query as string) || "";
                    setStatusLine(`Looking up ${event.tool.replace(/^get_/, "").replace(/_/g, " ")}${ticker ? ` (${ticker})` : ""}…`);
                } else if (event.type === "tool_end") {
                    setStatusLine(null);
                } else if (event.type === "watchlist_proposal") {
                    setProposals((prev) => [...prev, { ticker: event.ticker, reason: event.reason, status: "pending" }]);
                } else if (event.type === "error") {
                    assistantText += (assistantText ? "\n\n" : "") + `⚠️ ${event.message}`;
                    setMessages((prev) => {
                        const next = [...prev];
                        next[next.length - 1] = { role: "assistant", content: assistantText };
                        return next;
                    });
                }
            }
        } catch (e) {
            setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = {
                    role: "assistant",
                    content: `⚠️ ${e instanceof Error ? e.message : "Something went wrong reaching the analyst agent."}`,
                };
                return next;
            });
        } finally {
            setLoading(false);
            setStatusLine(null);
            scrollToBottom();
        }
    }

    async function confirmProposal(index: number) {
        const proposal = proposals[index];
        try {
            await addToWatchlist(proposal.ticker);
            setProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "added" } : p)));
        } catch {
            setStatusLine(`Failed to add ${proposal.ticker} — try again from the Watchlist page.`);
        }
    }

    function dismissProposal(index: number) {
        setProposals((prev) => prev.map((p, i) => (i === index ? { ...p, status: "dismissed" } : p)));
    }

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)] max-w-3xl mx-auto">
            <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                {messages.length === 0 && (
                    <Card>
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center gap-2 text-lg font-semibold">
                                <Sparkles className="h-5 w-5 text-indigo-500" />
                                Ask the analyst
                            </div>
                            <p className="text-sm text-muted-foreground">
                                It reads live data across this app — fundamentals, filings, ownership, sentiment,
                                congress and institutional trades — before answering. It can suggest watchlist
                                additions, but it never adds one without your confirmation, and it can&apos;t place
                                trades.
                            </p>
                            <div className="space-y-2">
                                {SUGGESTIONS.map((s) => (
                                    <button
                                        key={s}
                                        onClick={() => send(s)}
                                        className="block w-full text-left text-sm px-3 py-2 rounded-md border hover:bg-muted transition-colors"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {messages.map((m, i) => (
                    <div key={i} className={cn("flex gap-3", m.role === "user" && "justify-end")}>
                        {m.role === "assistant" && (
                            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                                <Bot className="h-4 w-4" />
                            </div>
                        )}
                        <div
                            className={cn(
                                "rounded-lg px-4 py-2 max-w-[85%] text-sm",
                                m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                            )}
                        >
                            {m.role === "assistant" ? (
                                m.content ? (
                                    <div className="prose prose-sm dark:prose-invert max-w-none">
                                        <ReactMarkdown>{m.content}</ReactMarkdown>
                                    </div>
                                ) : (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                )
                            ) : (
                                m.content
                            )}
                        </div>
                        {m.role === "user" && (
                            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                                <User className="h-4 w-4" />
                            </div>
                        )}
                    </div>
                ))}

                {statusLine && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground pl-11">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        {statusLine}
                    </div>
                )}

                {proposals.map((p, i) =>
                    p.status === "dismissed" ? null : (
                        <Card key={i} className="border-indigo-500/30">
                            <CardContent className="p-4 flex items-center justify-between gap-4">
                                <div>
                                    <p className="font-semibold">
                                        Add <span className="text-indigo-500">{p.ticker}</span> to your watchlist?
                                    </p>
                                    <p className="text-sm text-muted-foreground">{p.reason}</p>
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
                                ) : (
                                    <span className="text-sm text-green-600 flex items-center gap-1 shrink-0">
                                        <Check className="h-4 w-4" /> Added
                                    </span>
                                )}
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
