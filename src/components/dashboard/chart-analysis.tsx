"use client";

import { useState } from "react";
import { analyzeChart } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Sparkles } from "lucide-react";

interface ChartAnalysisProps {
  ticker: string;
  period: string;
  interval: string;
}

export function ChartAnalysis({ ticker, period, interval }: ChartAnalysisProps) {
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    setLoading(true);
    try {
      const result = await analyzeChart(ticker, period, interval);
      setAnalysis(result);
    } catch (err) {
      console.error(err);
      setAnalysis("Failed to generate analysis. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-medium">AI Chart Analysis</CardTitle>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={handleAnalyze} 
          disabled={loading}
          className="gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4 text-purple-500" />
          )}
          Summarize with AI
        </Button>
      </CardHeader>
      <CardContent>
        {!analysis && !loading && (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground bg-muted/30 rounded-md border border-dashed">
            Click "Summarize" to generate a technical analysis of the current chart.
          </div>
        )}
        
        {loading && (
          <div className="flex h-32 items-center justify-center space-y-2 flex-col">
            <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
            <span className="text-sm text-muted-foreground">Analyzing price action...</span>
          </div>
        )}

        {analysis && !loading && (
          <div className="prose prose-sm dark:prose-invert max-w-none mt-4 p-4 bg-muted/30 rounded-md">
            {/* Simple Markdown rendering by splitting lines or just preserving whitespace */}
            <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {analysis}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
