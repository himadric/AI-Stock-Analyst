"use client";

import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts';
import { useRouter } from 'next/navigation';

// Type definitions
interface HeatmapData {
    ticker: string;
    sector: string;
    market_cap: number;
    relative_strength: {
        "1m": number;
        "3m": number;
        "6m": number;
    };
    children?: HeatmapData[]; // For nested data structure if needed
    name?: string; // Recharts uses 'name'
    size?: number; // Recharts uses 'size' value
}

const COLORS = {
    strong_buy: "#22c55e", // green-500
    buy: "#4ade80", // green-400
    neutral: "#9ca3af", // gray-400
    sell: "#f87171", // red-400
    strong_sell: "#ef4444", // red-500
};

// Helper to get color based on value
const getColor = (value: number | undefined | null) => {
    if (typeof value !== 'number' || isNaN(value)) return "#9ca3af"; // gray-400 for no data
    
    // value is decimal percentage (e.g., 0.05 for 5%)
    if (value > 0.03) return "#15803d"; // green-700
    if (value > 0.01) return "#16a34a"; // green-600
    if (value >= 0.00) return "#22c55e"; // green-500
    if (value > -0.01) return "#9ca3af"; // neutral/gray
    if (value > -0.03) return "#ef4444"; // red-500
    if (value > -0.05) return "#dc2626"; // red-600
    return "#b91c1c"; // red-700
};

const CustomContent = (props: any) => {
    // Destructure directly from props since Recharts spreads the data object
    const { depth, x, y, width, height, index, payload, colors, name, ticker, performance, relative_strength } = props;
    const router = useRouter();

    if (width <= 0 || height <= 0) return null;

    // --- STYLES PRESETS ---
    let fill = "#eee"; 
    let stroke = "#fff"; // Default white border for clean separation
    let strokeWidth = 1;
    let text = "";
    let textColor = "#000";
    let isClickable = false;
    let fontSize = 10;
    
    let displayTicker = ticker || name || "???";
    
    // Attempt to find performance value
    let perf = performance;
    if (perf === undefined && payload) {
        perf = payload.performance ?? payload.relative_strength?.["1m"];
        if (!displayTicker && payload.ticker) displayTicker = payload.ticker;
    }
    if (perf === undefined && relative_strength) {
        perf = relative_strength["1m"];
    }

    // --- DEPTH BASED LOGIC ---
    if (depth === 1) {
        return <g />; 
    } 
    else if (depth === 2) {
        // SECTOR NODE (Group Header Background)
        return (
            <g>
                <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill="transparent"
                    stroke="#374151" // Dark border for sector group
                    strokeWidth={1}
                    className="pointer-events-none"
                />
                {/* Sector Header Text - With Left Padding */}
                {/* We render a small semi-transparent background to ensure readability if overlapping */}
                {width > 60 && height > 20 && (
                    <g pointerEvents="none">
                         <rect x={x} y={y} width={width} height={18} fill="rgba(255,255,255,0.8)"  />
                        <text
                            x={x + 4} // Padding on the side
                            y={y + 13}
                            fill="#000" // gray-900
                            fontSize={12}
                            fontWeight="bold"
                        >
                            {name}
                        </text>
                    </g>
                )}
            </g>
        );
    } 
    else if (depth === 3) {
        // COMPANY NODE
        
        const headerHeight = 18; // Space reserved for sector title
        // GAP REMOVED: Tickers touch each other perfectly now.
        
        let finalX = x;
        let finalY = y + headerHeight;
        let finalWidth = width;
        let finalHeight = height; // - headerHeight;

        // Clamp negative dimensions
        if (finalWidth < 0) finalWidth = 0;
        if (finalHeight < 0) {
             finalY = y;
             finalHeight = height; // If too small for header, take full space
        }

        if (perf !== undefined && perf !== null) {
            fill = getColor(perf);
            text = displayTicker;
        } else {
            fill = "#efefef"; 
            text = displayTicker;
            textColor = "#000";
        }
        
        stroke = "#fff"; // Clean white border
        strokeWidth = 1;
        textColor = perf !== undefined ? "#fff" : "#000";
        isClickable = true;
        // Dynamic font size
        fontSize = Math.min(finalWidth / 5, 14);

        return (
            <g>
                <rect
                    x={finalX}
                    y={finalY}
                    width={finalWidth}
                    height={finalHeight}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                    className={isClickable ? "cursor-pointer hover:opacity-90 transition-opacity" : ""}
                    onClick={() => {
                        if (isClickable && displayTicker !== "???") {
                            router.push(`/simulation/${displayTicker}`);
                        }
                    }}
                />
                
                {/* Ticker Label */}
                {text && finalWidth > 30 && finalHeight > 20 && (
                    <text
                        x={finalX + finalWidth / 2}
                        y={finalY + finalHeight / 2}
                        textAnchor="middle"
                        fill={textColor}
                        fontSize={fontSize}
                        fontWeight="bold"
                        pointerEvents="none"
                        style={{ textShadow: perf !== undefined ? '0 1px 2px rgba(0,0,0,0.3)' : 'none' }}
                        dominantBaseline="central"
                    >
                        {text}
                    </text>
                )}
    
                {/* Performance % */}
                {finalWidth > 40 && finalHeight > 35 && perf !== undefined && (
                    <text
                        x={finalX + finalWidth / 2}
                        y={finalY + finalHeight / 2 + 20}
                        textAnchor="middle"
                        fill="rgba(255,255,255,0.9)"
                        fontSize={Math.max(10, fontSize - 2)}
                        pointerEvents="none"
                    >
                         {(perf * 100).toFixed(1)}%
                    </text>
                )}
            </g>
        );
    }

    return null;
};

export default function SnpHeatmap() {
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [period, setPeriod] = useState<"1m" | "3m" | "6m">("1m");

    useEffect(() => {
        fetch('/api/heatmap/relative-strength')
            .then(res => res.json())
            .then(rawData => {
                setData(rawData);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    // Transform data for Treemap
    const processedData = React.useMemo(() => {
        if (!data.length) return [];

        // 1. Group by Sector
        const sectors: Record<string, any[]> = {};
        
        data.forEach(item => {
            const sector = item.sector || "Unknown";
            if (!sectors[sector]) sectors[sector] = [];
            
            // Recharts Treemap data node
            sectors[sector].push({
                name: item.ticker,
                ticker: item.ticker,
                size: item.market_cap || 1, // Ensure non-zero
                performance: item.relative_strength ? item.relative_strength[period] : 0,
                ...item
            });
        });

        // 2. Format for Recharts with a Single Root
        const sectorsArray = Object.keys(sectors).map(sectorName => ({
            name: sectorName,
            children: sectors[sectorName]
        }));
        
        return [{
            name: 'S&P 500',
            children: sectorsArray
        }];
    }, [data, period]);


    // Log data for debugging
    console.log("Processed Heatmap Data:", processedData);

    if (loading) return <div className="text-center p-10">Loading Heatmap...</div>;

    return (
        <div className="w-full h-full p-4 space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">S&P 500 Relative Strength Heatmap</h2>
                <div className="space-x-2">
                     <span className="text-sm font-medium mr-2">Period:</span>
                    {(["1m", "3m", "6m"] as const).map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                                period === p
                                    ? "bg-blue-600 text-white"
                                    : "bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200"
                            }`}
                        >
                            {p.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-[600px] w-full border rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-900 overflow-x-auto">
                    <Treemap
                        width={1000}
                        height={600}
                        data={processedData}
                        dataKey="size"
                        aspectRatio={4 / 3}
                        stroke="#fff"
                        content={<CustomContent selectedPeriod={period} />}
                    >
                         <Tooltip 
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const d = payload[0].payload;
                                    return (
                                        <div className="bg-white dark:bg-gray-800 p-2 border rounded shadow text-sm">
                                            <p className="font-bold">{d.ticker}</p>
                                            <p className="text-gray-500">{d.sector}</p>
                                            <p>Market Cap: ${(d.size / 1e9).toFixed(1)}B</p>
                                            <p className={`${d.performance >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                Rel. Strength ({period}): {(d.performance * 100).toFixed(2)}%
                                            </p>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                    </Treemap>
            </div>
             <div className="text-xs text-gray-500 text-right mt-1">
                Size represents Market Cap. Color represents Relative Strength vs SPY.
            </div>
        </div>
    );
}
