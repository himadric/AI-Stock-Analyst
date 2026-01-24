"use client";

import { Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { VanguardTracker } from "@/components/dashboard/vanguard-tracker";
import { MunroTracker } from "@/components/dashboard/munro-tracker";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2 } from "lucide-react";

export default function InstitutionalPage() {
    return (
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <div className="container mx-auto py-6 space-y-8">
                    <div className="flex flex-col gap-2">
                        <h1 className="text-3xl font-bold tracking-tight">Institutional Trackers</h1>
                        <p className="text-muted-foreground">
                            Track major portfolio moves by top institutional investors based on 13F filings.
                        </p>
                    </div>

                    <Tabs defaultValue="vanguard" className="w-full">
                        <TabsList className="grid w-full grid-cols-2 max-w-[400px]">
                            <TabsTrigger value="vanguard">Vanguard</TabsTrigger>
                            <TabsTrigger value="munro">Munro Partners</TabsTrigger>
                        </TabsList>
                        
                        <div className="mt-6">
                            <TabsContent value="vanguard">
                                <VanguardTracker />
                            </TabsContent>
                            <TabsContent value="munro">
                                <MunroTracker />
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>
            </DashboardLayout>
        </Suspense>
    );
}
