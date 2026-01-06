"use client";

import { Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { VanguardTracker } from "@/components/dashboard/vanguard-tracker";
import { Loader2 } from "lucide-react";

export default function VanguardPage() {
    return (
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <VanguardTracker />
            </DashboardLayout>
        </Suspense>
    );
}
