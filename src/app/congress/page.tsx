"use client";

import { Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { CongressTracker } from "@/components/dashboard/congress-tracker";
import { Loader2 } from "lucide-react";

export default function CongressPage() {
    return (
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <CongressTracker />
            </DashboardLayout>
        </Suspense>
    );
}
