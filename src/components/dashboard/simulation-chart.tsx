"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Area, AreaChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface SimulationChartProps {
    historical: any[];
    simulation: any[];
}

export function SimulationChart({ historical, simulation }: SimulationChartProps) {
    // Combine data for continuous chart
    // We need to make sure the structure aligns for the composed chart
    
    // Historical data: { date, price } -> mapped to { date, actual: price }
    const histData = historical.map(d => ({
        date: d.date,
        actual: d.price,
        isHistorical: true
    }));
    
    // Simulation data: { date, p05, p50, p95 ... }
    // The first point of simulation should probably match the last point of history for visual continuity
    const simData = simulation.map(d => ({
        date: d.date,
        p05: d.p05,
        p25: d.p25,
        p50: d.p50,
        p75: d.p75,
        p95: d.p95,
        isHistorical: false
    }));
    
    const combinedData = [...histData, ...simData];

    return (
        <Card className="col-span-full">
            <CardHeader>
                <CardTitle>Price Projection (Monte Carlo)</CardTitle>
                <CardDescription>
                    Historical data (solid) vs Projected Probabilities (shaded)
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={combinedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <defs>
                                <linearGradient id="colorCone" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                            <XAxis 
                                dataKey="date" 
                                tickFormatter={(str) => {
                                    const date = new Date(str);
                                    return `${date.getMonth() + 1}/${date.getDate()}`;
                                }}
                                minTickGap={30}
                            />
                            <YAxis 
                                domain={['auto', 'auto']}
                                tickFormatter={(val) => `$${val.toFixed(0)}`}
                            />
                            <Tooltip 
                                labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                formatter={(value: any, name: any) => {
                                    const map: Record<string, string> = {
                                        "actual": "Historical Price",
                                        "p50": "Median Projection",
                                        "p95": "Upper 95%",
                                        "p05": "Lower 5%"
                                    };
                                    return [`$${Number(value).toFixed(2)}`, map[name as string] || name];
                                }}
                            />
                            <Legend />
                            
                            {/* Historical Price */}
                            <Line 
                                type="monotone" 
                                dataKey="actual" 
                                stroke="#000000" 
                                strokeWidth={2} 
                                dot={false}
                                name="Historical"
                            />
                            
                            {/* Median Projection */}
                            <Line 
                                type="monotone" 
                                dataKey="p50" 
                                stroke="#3b82f6" 
                                strokeDasharray="5 5"
                                strokeWidth={2} 
                                dot={false}
                                name="Median Forecast"
                            />
                            
                            {/* Confidence Interval (5th to 95th) */}
                            {/* Area chart usually requires two bounds, but Recharts Area is simple. 
                                To do a range, we typically use Area with dataKey as range array, but ComposedChart is tricky.
                                STACKED Area cheat: 
                                We want fill between p05 and p95. 
                                Recharts doesn't support 'range area' natively perfectly in Composed.
                                Workaround: Use 'range' prop in Area (available in newer Recharts) OR
                                construct the data so we stack 'bottom invisible' + 'visible range'.
                            */}
                            
                            {/* Simplification: Just plot lines for p05 and p95 for now, or use Area if supported. 
                                Let's try plotting a transparent area for context.
                             */}
                             
                             {/* Upper Bound Area (p95) */}
                             {/* Actually, visually, just lines is clearer for "Cone" boundaries in this specific library version.
                                 Let's add p05, p25, p75, p95 as light lines.
                             */}
                             <Line type="monotone" dataKey="p95" stroke="#22c55e" strokeWidth={1} dot={false} name="Best Case (95%)" strokeOpacity={0.5} />
                             <Line type="monotone" dataKey="p05" stroke="#ef4444" strokeWidth={1} dot={false} name="Worst Case (5%)" strokeOpacity={0.5} />
                             
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
