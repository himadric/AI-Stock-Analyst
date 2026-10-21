"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { streamInjectionDemo, InjectionScenario } from "@/lib/api";

interface InjectionDemoColumnProps {
    scenario: InjectionScenario;
    defensesOn: boolean;
    runToken: number;
}

export function InjectionDemoColumn({ scenario, defensesOn, runToken }: InjectionDemoColumnProps) {
    const [text, setText] = useState("");
    const [verdict, setVerdict] = useState<{ attackSucceeded: boolean; detail: string } | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [running, setRunning] = useState(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    useEffect(() => {
        if (runToken === 0) return;

        const controller = new AbortController();
        abortControllerRef.current = controller;
        setText("");
        setVerdict(null);
        setError(null);
        setRunning(true);

        (async () => {
            try {
                for await (const event of streamInjectionDemo(scenario, defensesOn, controller.signal)) {
                    if (event.type === "text") {
                        setText((prev) => prev + event.text);
                    } else if (event.type === "verdict") {
                        setVerdict({ attackSucceeded: event.attack_succeeded, detail: event.detail });
                    } else if (event.type === "error") {
                        setError(event.message);
                    }
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err instanceof Error ? err.message : "Something went wrong.");
                }
            } finally {
                setRunning(false);
            }
        })();

        return () => controller.abort();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [runToken]);

    return (
        <Card className="flex-1 min-w-0">
            <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
                <CardTitle className="text-sm font-semibold">
                    {defensesOn ? "Defended" : "Undefended"}
                </CardTitle>
                <Badge variant={defensesOn ? "secondary" : "outline"} className="gap-1">
                    {defensesOn ? <ShieldCheck className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
                    {defensesOn ? "Delimiter + system rule ON" : "No defense"}
                </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
                {running && !text && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" /> Running…
                    </div>
                )}
                {text && (
                    <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                        <ReactMarkdown>{text}</ReactMarkdown>
                    </div>
                )}
                {error && <p className="text-sm text-destructive">{error}</p>}
                {verdict && (
                    <div
                        className={cn(
                            "rounded-md border px-3 py-2 text-sm font-medium",
                            verdict.attackSucceeded
                                ? "border-destructive/40 bg-destructive/10 text-destructive"
                                : "border-green-500/40 bg-green-500/10 text-green-600 dark:text-green-400",
                        )}
                    >
                        {verdict.attackSucceeded ? "⚠️ Injection succeeded" : "✅ Injection blocked"}
                        <p className="mt-1 font-normal opacity-90">{verdict.detail}</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
