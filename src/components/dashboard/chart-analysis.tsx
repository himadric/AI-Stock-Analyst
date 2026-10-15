"use client";

import { useState, type RefObject } from "react";
import { toPng } from "html-to-image";
import { analyzeChart } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Sparkles } from "lucide-react";

interface ChartAnalysisProps {
  ticker: string;
  period: string;
  interval: string;
  // The rendered chart's container - captured to a PNG so the model reads
  // the actual chart on screen (indicators, comparisons, and all), not a
  // table of numbers reconstructed separately from a fresh data fetch.
  chartRef: RefObject<HTMLDivElement | null>;
}

export function ChartAnalysis({ ticker, period, interval, chartRef }: ChartAnalysisProps) {
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Kept purely to show the user what was actually sent to the model - proof
  // this is reading the rendered chart, not just a table of numbers.
  const [capturedImage, setCapturedImage] = useState<string | null>(null);

  async function handleAnalyze() {
    setLoading(true);
    try {
      // Capture is best-effort: if it fails for any reason (an unusual
      // browser, a transient DOM issue), fall back to the numeric-only
      // analysis rather than blocking the whole feature on a screenshot.
      let chartImage: string | undefined;
      if (chartRef.current) {
        try {
          chartImage = await toPng(chartRef.current, { pixelRatio: 2 });
        } catch (captureErr) {
          console.error("Chart capture failed, falling back to numeric analysis:", captureErr);
        }
      }
      setCapturedImage(chartImage ?? null);

      const result = await analyzeChart(ticker, period, interval, chartImage);
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
          <>
            {capturedImage && (
              <div className="mt-4">
                <p className="text-xs font-medium text-muted-foreground mb-1.5">
                  🖼️ Image sent to the AI — this is what it actually analyzed, not just the numbers
                </p>
                <a href={capturedImage} target="_blank" rel="noopener noreferrer">
                  <img
                    src={capturedImage}
                    alt="Chart image analyzed by the AI"
                    className="rounded-md border max-h-48 w-auto hover:opacity-90 transition-opacity cursor-zoom-in"
                  />
                </a>
              </div>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none mt-4 p-4 bg-muted/30 rounded-md">
              {/* Simple Markdown rendering by splitting lines or just preserving whitespace */}
              <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                {analysis}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
