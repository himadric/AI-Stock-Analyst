import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

interface Factor {
    value: number | string;
    score: number;
    max: number;
    pass: boolean;
    label: string;
}

interface ScoreData {
    ticker: string;
    total_score: number;
    factors: {
        rule_of_40: Factor;
        rnd_intensity: Factor;
        scalability: Factor;
        peg_ratio: Factor;
        roic: Factor;
    };
}

export function FutureLeaderScore({ data }: { data: ScoreData | null }) {
    if (!data) return (
        <Card className="h-full">
            <CardHeader>
               <CardTitle className="flex items-center gap-2">
                    <Trophy className="h-5 w-5 text-muted-foreground" />
                    Future Leader Score
                </CardTitle>
                <CardDescription>AI-driven growth ranking</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                    Data unavailable
                </div>
            </CardContent>
        </Card>
    );

    const factors = [
        data.factors.rule_of_40,
        data.factors.rnd_intensity,
        data.factors.scalability,
        data.factors.peg_ratio,
        data.factors.roic
    ];

    const getScoreColor = (score: number) => {
        if (score >= 8) return "text-green-500";
        if (score >= 5) return "text-yellow-500";
        return "text-red-500";
    };

    return (
        <Card className="h-full">
            <CardHeader className="pb-2 pt-6 px-6">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Trophy className="h-5 w-5 text-amber-400" />
                            Future Leader Score
                        </CardTitle>
                    </div>
                    <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold font-mono">
                            {data.total_score.toFixed(1)}
                        </span>
                        <span className="text-sm text-muted-foreground">/10</span>
                    </div>
                </div>
                <div className="relative w-full h-2 bg-secondary rounded-full overflow-hidden mt-4">
                    <div 
                        className={cn("h-full transition-all duration-500", 
                            data.total_score >= 8 ? "bg-green-500" : data.total_score >= 5 ? "bg-yellow-500" : "bg-red-500"
                        )}
                        style={{ width: `${(data.total_score / 10) * 100}%` }}
                    />
                </div>
            </CardHeader>
            <CardContent className="px-6 pb-6 pt-2">
                <Table>
                    <TableBody>
                        {factors.map((factor, i) => (
                            <TableRow key={i} className="hover:bg-muted/50 border-b-0">
                                <TableCell className="py-1 font-medium text-sm pl-0">
                                    <div className="flex items-center gap-2">
                                        {factor.pass ? 
                                            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0"/> : 
                                            <XCircle className="h-4 w-4 text-red-400 shrink-0"/>
                                        }
                                        {factor.label}
                                    </div>
                                </TableCell>
                                <TableCell className="py-1 text-right text-sm">
                                    {factor.value}
                                    {factor.label.includes("Ratio") ? "" : factor.label.includes("Scalability") ? "" : "%"}
                                </TableCell>
                                <TableCell className="py-1 text-right text-sm text-muted-foreground pr-0">
                                    {factor.score}/{factor.max}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
}
