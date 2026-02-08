"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface Sector {
    sector: string;
    weight: number;
}

interface SectorAllocationProps {
    sectors: Sector[];
}

const COLORS = [
    "#2563eb", "#16a34a", "#db2777", "#ea580c", "#8b5cf6", 
    "#0891b2", "#c026d3", "#ca8a04", "#4b5563", "#0f172a", "#dc2626"
];

export function SectorAllocation({ sectors }: SectorAllocationProps) {
    if (!sectors || sectors.length === 0) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Sector Allocation</CardTitle>
                    <CardDescription>Portfolio exposure by sector</CardDescription>
                </CardHeader>
                <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No sector data available.
                </CardContent>
            </Card>
        );
    }

    // Format sector names (e.g., 'consumer_cyclical' -> 'Consumer Cyclical')
    const formattedData = sectors
        .map(s => ({
            name: s.sector.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
            value: s.weight
        }))
        .sort((a, b) => b.value - a.value); // Sort descending

    return (
        <Card className="h-full">
            <CardHeader>
                <CardTitle>Sector Allocation</CardTitle>
                <CardDescription>Portfolio exposure by industry sector</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={formattedData}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                outerRadius={120}
                                fill="#8884d8"
                                dataKey="value"
                            >
                                {formattedData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip 
                                formatter={(value: any) => ((value || 0) * 100).toFixed(2) + "%"}
                                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                                itemStyle={{ color: 'hsl(var(--foreground))' }}
                            />
                            <Legend layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: '12px' }}/>
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
