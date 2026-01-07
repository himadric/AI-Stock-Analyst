"use client";

import { Suspense } from "react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { HouseTracker } from "@/components/dashboard/house-tracker";
import { Loader2 } from "lucide-react";

export default function HousePage() {
    return (
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <HouseTracker />
            </DashboardLayout>
        </Suspense>
    );
}
