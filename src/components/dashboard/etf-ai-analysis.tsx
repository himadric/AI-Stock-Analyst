"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { analyzeEtf } from "@/lib/api";

interface EtfAiAnalysisProps {
  ticker: string;
}

export function EtfAiAnalysis({ ticker }: EtfAiAnalysisProps) {
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeEtf(ticker);
      setAnalysis(data.analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xl font-bold flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-indigo-500" />
          AI Investment Strategist
        </CardTitle>
        {!analysis && !loading && (
          <Button onClick={handleAnalyze} size="sm" className="gap-2">
            <FileText className="h-4 w-4" />
            Generate Report
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
           <div className="flex flex-col items-center justify-center py-12 space-y-4">
             <Loader2 className="h-8 w-8 animate-spin text-primary" />
             <p className="text-sm text-muted-foreground animate-pulse">
               Conducting "Quality Core" analysis for {ticker}...
             </p>
             <div className="text-xs text-muted-foreground space-y-1 text-center">
                <p>Analyzing Expense Efficiency...</p>
                <p>Computing Risk Metrics (Beta, Sharpe)...</p>
                <p>Evaluating Portfolio Composition...</p>
             </div>
           </div>
        ) : error ? (
          <div className="text-red-500 text-sm py-4">
            Error: {error}. Please try again.
            <Button variant="outline" size="sm" onClick={handleAnalyze} className="ml-2">Retry</Button>
          </div>
        ) : analysis ? (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{analysis}</ReactMarkdown>
            <div className="mt-6 flex justify-end">
               <Button variant="outline" size="sm" onClick={() => setAnalysis(null)}>
                 Close Report
               </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground space-y-2">
            <p>Generate a comprehensive "Quality Core" analysis for {ticker}.</p>
            <p className="text-xs max-w-md mx-auto">
              Includes Structural Efficiency, Portfolio Composition, Risk Metrics, and Long-Term Performance verdict.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
