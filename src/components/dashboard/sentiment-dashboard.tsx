"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Heart, TrendingUp, AlertTriangle, HelpCircle, MessageSquare, Youtube, Newspaper } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// Reuse similar structure to other dashboards
interface SentimentData {
    ticker: string;
    query: string;
    analysis: {
        nss: number;
        distribution: {
            positive: number;
            neutral: number;
            negative: number;
            total: number;
        };
        emotions: Record<string, number>;
        keywords: { text: string; value: number }[];
    };
    recent_posts: {
        id: string;
        title: string;
        text: string;
        score: number;
        url: string;
        sentiment_label?: string;
        created_utc: number;
        subreddit: string;
        author: string;
        source?: "news" | "youtube" | "reddit"; 
        comments?: string[];
    }[];
}

export function SentimentDashboard({ data, isLoading }: { data: SentimentData | null; isLoading: boolean }) {
    if (isLoading) {
        return (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                 {[1, 2, 3].map((i) => (
                    <Card key={i} className="h-[200px] animate-pulse bg-muted/20" />
                ))}
            </div>
        );
    }

    if (!data) return null;

    const { nss, distribution, emotions, keywords } = data.analysis;

    // Helper for color
    const getNssColor = (score: number) => {
        if (score >= 20) return "text-green-500";
        if (score >= -5) return "text-yellow-500";
        return "text-red-500";
    };

    const getNssBg = (score: number) => {
        if (score >= 20) return "bg-green-500";
        if (score >= -5) return "bg-yellow-500";
        return "bg-red-500";
    };

    return (
        <div className="space-y-6">
            {/* Top Row: Key Metrics */}
            <div className="grid gap-6 md:grid-cols-3">
                {/* NSS Score Card */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Net Sentiment Score (NSS)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline gap-2">
                            <span className={cn("text-4xl font-bold", getNssColor(nss))}>
                                {nss > 0 ? "+" : ""}{nss.toFixed(1)}%
                            </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            % Positive - % Negative
                        </p>
                        <div className="mt-4 h-2 w-full bg-secondary rounded-full overflow-hidden">
                            <div 
                                className={cn("h-full transition-all", getNssBg(nss))}
                                style={{ width: `${Math.min(100, Math.max(0, (nss + 100) / 2))}%` }} 
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Volume & Distribution */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Volume & Split</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{distribution.total} <span className="text-sm font-normal text-muted-foreground">items</span></div>
                        <div className="flex gap-2 mt-4 text-xs">
                            <div className="flex flex-col items-center">
                                <span className="font-bold text-green-500">{distribution.positive}</span>
                                <span className="text-muted-foreground">Pos</span>
                            </div>
                            <div className="h-8 w-px bg-border mx-2"></div>
                             <div className="flex flex-col items-center">
                                <span className="font-bold text-gray-500">{distribution.neutral}</span>
                                <span className="text-muted-foreground">Neu</span>
                            </div>
                            <div className="h-8 w-px bg-border mx-2"></div>
                             <div className="flex flex-col items-center">
                                <span className="font-bold text-red-500">{distribution.negative}</span>
                                <span className="text-muted-foreground">Neg</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Top Emotions */}
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Top Emotions</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {Object.entries(emotions)
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 3)
                                .map(([emotion, count]) => (
                                <div key={emotion} className="flex justify-between items-center text-sm">
                                    <span className="font-medium">{emotion}</span>
                                    <Badge variant="secondary">{count}</Badge>
                                </div>
                            ))}
                            {Object.keys(emotions).length === 0 && <span className="text-sm text-muted-foreground">No strong emotions detected</span>}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Middle Row: Keywords & Recent Posts */}
            <div className="grid gap-6 md:grid-cols-3">
                {/* Keywords Cloud (List for MVP) */}
                <Card className="md:col-span-1">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" /> Trending Topics
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            {keywords.map((kw) => (
                                <Badge key={kw.text} variant="outline" className="text-sm py-1 px-3 cursor-default hover:bg-secondary">
                                    {kw.text} <span className="ml-1 opacity-50 text-[10px]">{kw.value}</span>
                                </Badge>
                            ))}
                            {keywords.length === 0 && <span className="text-muted-foreground">No trending keywords</span>}
                        </div>
                    </CardContent>
                </Card>

                {/* Recent Verbatims */}
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Newspaper className="h-4 w-4" /> 
                            Recent News & Videos
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="max-h-[500px] overflow-y-auto pr-2">
                        <div className="space-y-4">
                            {data.recent_posts.map((post) => (
                                <div key={post.id} className="border rounded-lg p-3 hover:bg-muted/30 transition-colors">
                                    <div className="flex justify-between items-start mb-1">
                                         <div className="flex items-center gap-2">
                                             {post.source === 'youtube' ? <Youtube className="h-4 w-4 text-red-500" /> : <Newspaper className="h-4 w-4 text-blue-500" />}
                                             <a href={post.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-sm hover:underline text-primary line-clamp-1">
                                                {post.title}
                                             </a>
                                         </div>
                                         <Badge 
                                            variant={post.sentiment_label === 'Positive' ? 'default' : post.sentiment_label === 'Negative' ? 'destructive' : 'secondary'} 
                                            className={cn("ml-2 text-[10px] uppercase h-5", post.sentiment_label === 'Positive' && "bg-green-600 hover:bg-green-700")}
                                        >
                                            {post.sentiment_label || "Neutral"}
                                         </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground line-clamp-2 mb-2 ml-6">
                                        {post.text}
                                    </p>
                                    <div className="flex items-center justify-between text-[10px] text-muted-foreground/70 ml-6">
                                        <span>{post.author} • {post.source === 'youtube' ? 'YouTube' : post.subreddit}</span>
                                        {post.source !== 'news' && <span>{post.score} views</span>}
                                    </div>
                                    {/* Render Comments if available */}
                                    {post.comments && post.comments.length > 0 && (
                                        <div className="mt-3 ml-6 p-3 bg-secondary/30 rounded-md text-xs">
                                            <div className="flex items-center gap-1 mb-2 text-muted-foreground font-medium">
                                                <MessageSquare className="h-3 w-3" /> Top Comments
                                            </div>
                                            <ul className="space-y-2">
                                                {post.comments.slice(0, 3).map((comment, idx) => (
                                                    <li key={idx} className="pl-2 border-l-2 border-primary/20 italic text-muted-foreground line-clamp-2">
                                                        "{comment}"
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
