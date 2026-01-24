"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Bar, BarChart, CartesianGrid, Label, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface DCFHistogramProps {
    data: { value: number; frequency: number }[];
    currentPrice: number;
    expectedValue: number;
    buyZonePrice: number;
}

export function DCFHistogram({ data, currentPrice, expectedValue, buyZonePrice }: DCFHistogramProps) {
    if (!data || data.length === 0) return null;

    // Helper to find closest bin for X-axis snapping (Recharts Categorical Axis limitation)
    const snapToBin = (targetVal: number) => {
        if (!data || data.length === 0) return targetVal;
        return data.reduce((prev, curr) => 
            Math.abs(curr.value - targetVal) < Math.abs(prev.value - targetVal) ? curr : prev
        ).value;
    };

    const snappedCurrent = snapToBin(currentPrice);
    const snappedExpected = snapToBin(expectedValue);
    const snappedBuyZone = snapToBin(buyZonePrice);

    return (
        <Card className="col-span-full">
            <CardHeader>
                <CardTitle>Intrinsic Value Distribution</CardTitle>
                <CardDescription>
                    Probabilistic outcome of 10,000 simulations.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                            <XAxis 
                                dataKey="value" 
                                tickFormatter={(val) => `$${val.toFixed(0)}`}
                                label={{ value: 'Intrinsic Value ($)', position: 'insideBottom', offset: -10 }}
                            />
                            <YAxis hide label={{ value: 'Probability', angle: -90, position: 'insideLeft' }}/>
                            <Tooltip 
                                labelFormatter={(label: any) => `Value: $${Number(label).toFixed(2)}`}
                                formatter={(value: any) => [(Number(value) * 100).toFixed(2) + "%", "Probability"]}
                            />
                            <Bar dataKey="frequency" fill="#3b82f6" name="Probability" radius={[4, 4, 0, 0]} />
                            
                            {/* Current Price Line */}
                            <ReferenceLine x={snappedCurrent} stroke="#ef4444" strokeWidth={2} label={{ value: "Current Price", position: "top", fill: "#ef4444" }} />
                            
                            {/* Expected Value Line */}
                            <ReferenceLine x={snappedExpected} stroke="#22c55e" strokeDasharray="5 5" label={{ value: "Median Price", position: "top", fill: "#22c55e" }} />

                            {/* Buy Zone Line (< 25th percentile) */}
                            <ReferenceLine x={snappedBuyZone} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Buy Zone", position: 'top', fill: '#f59e0b' }} />
                            
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
