"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { runSimulation } from "@/lib/api";
import { Loader2, Play, RefreshCw, AlertTriangle } from "lucide-react";
import { DCFHistogram } from "@/components/dashboard/dcf-histogram";

function SimulationContent() {
    const searchParams = useSearchParams();
    const defaultTicker = searchParams.get("ticker") || "MSFT";
    
    // Inputs
    const [ticker, setTicker] = useState(defaultTicker);
    const [wacc, setWacc] = useState(0.09); // 9%
    const [growthRate, setGrowthRate] = useState<number | null>(null); // Auto by default
    const [simulations, setSimulations] = useState(10000);
    const [bearCase, setBearCase] = useState(false);
    
    // UI State for sliders (percentage for easier UX)
    const [waccPct, setWaccPct] = useState(9); // 9%
    
    // State
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    // Run on mount
    useEffect(() => {
        handleRun();
    }, []); 

    async function handleRun() {
        setLoading(true);
        setError(null);
        try {
            // waccPct is integer 9 -> 0.09
            // waccPct is integer 9 -> 0.09
            const finalGrowth = growthRate !== null ? growthRate / 100 : null; // Handle manual override
            const data = await runSimulation(ticker, waccPct / 100, finalGrowth, simulations, bearCase);
            
            if (data.error) throw new Error(data.error);
            setResult(data);
        } catch (e: any) {
            console.error(e);
            setError(e.message || "Simulation failed. Please check the ticker symbol.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Probabilistic DCF Valuation</h2>
                    <p className="text-muted-foreground">Monte Carlo Simulation of Fundamental Value</p>
                </div>
                <Button onClick={handleRun} disabled={loading}>
                    {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                    Run Valuation
                </Button>
            </div>

            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle>Model Assumptions</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <Label>Ticker Symbol</Label>
                                {result?.dcf_metrics?.current_price && (
                                    <span className="text-sm font-medium text-green-600">
                                        Current Price: ${result.dcf_metrics.current_price.toFixed(2)}
                                    </span>
                                )}
                            </div>
                            <Input 
                                value={ticker} 
                                readOnly
                                disabled
                                className="bg-muted font-bold"
                            />
                        </div>
                        
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <Label>Discount Rate (WACC)</Label>
                                <span className="text-sm text-muted-foreground">{waccPct}%</span>
                            </div>
                            <Slider 
                                value={[waccPct]} 
                                onValueChange={(vals: number[]) => {
                                    if(vals[0] !== waccPct) setWaccPct(vals[0]);
                                }} 
                                min={5} 
                                max={15} 
                                step={0.5}
                            />
                             <p className="text-xs text-muted-foreground">Higher rate = Lower Valuation (Conservative)</p>
                        </div>
                        
                         <div className="space-y-2">
                            <div className="flex justify-between">
                                <Label>Manual Growth Rate (Optional)</Label>
                                <span className="text-sm text-muted-foreground">
                                    {growthRate !== null 
                                        ? `${growthRate}%` 
                                        : (result?.dcf_metrics?.assumptions?.growth_mean 
                                            ? `${(result.dcf_metrics.assumptions.growth_mean * 100).toFixed(1)}% (Historical)`
                                            : "Auto (Historical)")
                                    }
                                </span>
                            </div>
                            <div className="flex gap-2 items-center">
                                <div className="flex-1">
                                    <Slider 
                                        disabled={growthRate === null}
                                        value={[growthRate || 10]} 
                                        onValueChange={(vals: number[]) => {
                                             if(vals[0] !== growthRate) setGrowthRate(vals[0]);
                                        }} 
                                        min={0} 
                                        max={40} 
                                        step={1}
                                    />
                                </div>
                                <Button 
                                    variant="outline" 
                                    size="sm" 
                                    onClick={() => setGrowthRate(growthRate === null ? 10 : null)}
                                >
                                    {growthRate === null ? "Override" : "Reset"}
                                </Button>
                            </div>
                            </div>
                        </div>

                        <div className="space-y-4 pt-1">
                            <div className="flex items-center justify-between space-x-2">
                                <Label htmlFor="bear-mode" className="font-medium text-red-600">Bear Case Mode</Label>
                                <Switch id="bear-mode" checked={bearCase} onCheckedChange={setBearCase} />
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Simulates severe downside: -1.5x Growth StdDev, +2% WACC, -5% Margins, Stagnant Terminal Growth.
                            </p>
                        </div>
                </CardContent>
            </Card>

            {error && (
                <div className="bg-destructive/10 text-destructive p-4 rounded-md flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5" />
                    {error}
                </div>
            )}

            {result && result.dcf_metrics && (
                <>
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                     <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Expected Fair Value</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className={`text-2xl font-bold ${bearCase && result.dcf_metrics.expected_value < result.dcf_metrics.current_price ? "text-red-600" : "text-blue-600"}`}>
                                ${result.dcf_metrics.expected_value.toFixed(2)}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Median of 10,000 outcomes
                            </p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Margin of Safety</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className={`text-2xl font-bold ${result.dcf_metrics.expected_value > result.dcf_metrics.current_price ? "text-green-600" : "text-amber-600"}`}>
                                {((result.dcf_metrics.expected_value - result.dcf_metrics.current_price) / result.dcf_metrics.current_price * 100).toFixed(1)}%
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Upside to Mean Value
                            </p>
                        </CardContent>
                    </Card>
                    
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Probability of Undervaluation</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {result.dcf_metrics.win_probability.toFixed(1)}%
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Chance Intrinsic Value {">"} Price
                            </p>
                        </CardContent>
                    </Card>

                    {result.dcf_metrics.max_drawdown_prob !== undefined && (
                        <Card>
                             <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-medium text-red-600">Max Drawdown Risk</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold text-red-600">
                                    {result.dcf_metrics.max_drawdown_prob.toFixed(1)}%
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Prob. of {">"}30% Loss
                                </p>
                            </CardContent>
                        </Card>
                    )}
                </div>
                
                <div className="grid grid-cols-1 gap-4">
                    {/* Chart */}
                     <DCFHistogram 
                        data={result.histogram} 
                        currentPrice={result.dcf_metrics.current_price} 
                        expectedValue={result.dcf_metrics.expected_value} 
                        buyZonePrice={result.dcf_metrics.buy_zone_price}
                    />
                </div>
                
                
                
                <Card className="bg-muted/50">
                    <CardContent className="pt-6 text-sm text-muted-foreground space-y-2">
                        <p><strong>Assumptions Used:</strong></p>
                        <ul className="list-disc pl-5">
                            <li>WACC: {(result.dcf_metrics.assumptions.wacc * 100).toFixed(1)}%</li>
                            <li>Mean Revenue Growth: {(result.dcf_metrics.assumptions.growth_mean * 100).toFixed(1)}% (StdDev: {(result.dcf_metrics.assumptions.growth_std * 100).toFixed(1)}%)</li>
                            <li>Mean FCF Margin: {(result.dcf_metrics.assumptions.margin_mean * 100).toFixed(1)}% (StdDev: {(result.dcf_metrics.assumptions.margin_std * 100).toFixed(1)}%)</li>
                            <li>Terminal Growth Rate: {(result.dcf_metrics.assumptions.terminal_growth * 100).toFixed(1)}%</li>
                            {result.is_bear_case && <li className="text-red-500 font-bold">Bear Case Scenarios Applied</li>}
                        </ul>
                    </CardContent>
                </Card>
                </>
            )}
        </div>
    );
}

export default function SimulationPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <SimulationContent />
            </DashboardLayout>
        </Suspense>
    );
}
