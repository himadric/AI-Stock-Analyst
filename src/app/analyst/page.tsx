"use client";

import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { AgentChat } from "@/components/dashboard/agent-chat";

export default function AnalystPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin" /></div>}>
            <DashboardLayout>
                <AgentChat />
            </DashboardLayout>
        </Suspense>
    );
}
