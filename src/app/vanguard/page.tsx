"use client";

import DashboardLayout from "@/components/layout/dashboard-layout";
import { VanguardTracker } from "@/components/dashboard/vanguard-tracker";

export default function VanguardPage() {
    return (
        <DashboardLayout>
            <VanguardTracker />
        </DashboardLayout>
    );
}
