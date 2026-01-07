"use client";

import { Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { SenateTracker } from "@/components/dashboard/senate-tracker";
import { Loader2 } from "lucide-react";

export default function SenatePage() {
    return (
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <SenateTracker />
            </DashboardLayout>
        </Suspense>
    );
}
