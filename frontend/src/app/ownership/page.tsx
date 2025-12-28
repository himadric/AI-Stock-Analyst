"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { fetchOwnership, fetchOwnershipDetails } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Users } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";

function OwnershipContent() {
    const searchParams = useSearchParams();
    const ticker = searchParams.get("ticker") || "AAPL";
    const [ownership, setOwnership] = useState<any>(null);
    const [details, setDetails] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            setLoading(true);
            try {
                const [ownRes, detailsRes] = await Promise.all([
                    fetchOwnership(ticker),
                    fetchOwnershipDetails(ticker)
                ]);
                setOwnership(ownRes);
                setDetails(detailsRes);
            } catch (err) {
                console.error("Failed to load ownership data:", err);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [ticker]);

    if (loading) {
        return <div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>;
    }

    if (!ownership && !details) {
        return <div className="p-8 text-center text-muted-foreground">No ownership data available for {ticker}.</div>;
    }

    // Prepare chart data
    const ownershipData = ownership ? [
        { name: "Institutions", value: ownership.institutions, fill: "#3b82f6" },
        { name: "Insiders", value: ownership.insiders, fill: "#f59e0b" },
        { name: "Public", value: ownership.public, fill: "#22c55e" },
    ] : [];

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">{ticker} Ownership</h2>
                <p className="text-muted-foreground">Shareholder structure and recent activity</p>
            </div>

            {/* Share Distribution Chart */}
            {ownership && (
                <Card>
                    <CardHeader>
                        <CardTitle>Share Distribution</CardTitle>
                        <CardDescription>Ownership breakdown by investor type</CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={ownershipData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={70}
                                        outerRadius={90}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {ownershipData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.fill} />
                                        ))}
                                    </Pie>
                                    <Tooltip formatter={(val: any) => [`${Number(val).toFixed(2)}%`, "Held"]} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="space-y-4">
                            {ownershipData.map((item) => (
                                <div key={item.name} className="flex items-center justify-between p-4 border rounded-lg bg-card/50">
                                    <div className="flex items-center gap-3">
                                        <div className="w-4 h-4 rounded-full shadow-sm" style={{ backgroundColor: item.fill }} />
                                        <span className="font-semibold text-lg">{item.name}</span>
                                    </div>
                                    <span className="font-bold text-xl font-mono">{item.value.toFixed(2)}%</span>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Detailed Tables */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Institutional Holders */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                             <Users className="h-5 w-5 text-blue-500" />
                             Top Institutional Holders
                        </CardTitle>
                        <CardDescription>Major funds and institutions</CardDescription>
                    </CardHeader>
                    <CardContent>
                         <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Holder</TableHead>
                                    <TableHead className="text-right">Shares</TableHead>
                                    <TableHead className="text-right">Date Reported</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {details?.institutions?.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center text-muted-foreground">No data available</TableCell>
                                    </TableRow>
                                ) : (
                                    details?.institutions?.map((inst: any, i: number) => (
                                        <TableRow key={i}>
                                            <TableCell className="font-medium text-xs md:text-sm">{inst.holder}</TableCell>
                                            <TableCell className="text-right font-mono text-xs md:text-sm">{inst.shares.toLocaleString()}</TableCell>
                                            <TableCell className="text-right text-muted-foreground text-xs">{new Date(inst.date_reported).toLocaleDateString()}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                         </Table>
                    </CardContent>
                </Card>

                {/* Insider Holders */}
                <Card>
                    <CardHeader>
                         <CardTitle className="flex items-center gap-2">
                             <Users className="h-5 w-5 text-amber-500" />
                             Top Insider Holders
                        </CardTitle>
                        <CardDescription>Key executives and directors</CardDescription>
                    </CardHeader>
                    <CardContent>
                         <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead className="text-right">Shares Owned</TableHead>
                                    <TableHead className="text-right">Date</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {details?.insiders?.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={3} className="text-center text-muted-foreground">No data available</TableCell>
                                    </TableRow>
                                ) : (
                                    details?.insiders?.map((ins: any, i: number) => (
                                        <TableRow key={i}>
                                            <TableCell className="font-medium text-xs md:text-sm">{ins.holder}</TableCell>
                                            <TableCell className="text-right font-mono text-xs md:text-sm">{ins.shares.toLocaleString()}</TableCell>
                                            <TableCell className="text-right text-muted-foreground text-xs">{ins.date_reported ? new Date(ins.date_reported).toLocaleDateString() : "-"}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                         </Table>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

export default function OwnershipPage() {
    return (
        <DashboardLayout>
            <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
                <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
                    <OwnershipContent />
                </Suspense>
            </div>
        </DashboardLayout>
    );
}
