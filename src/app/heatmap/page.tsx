import React, { Suspense } from 'react';
import SnpHeatmap from '@/components/heatmap/SnpHeatmap';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Loader2 } from 'lucide-react';

export default function HeatmapPage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-12"><Loader2 className="animate-spin"/></div>}>
            <DashboardLayout>
                <div className="p-6">
                    <h1 className="text-3xl font-bold mb-6">Market Heatmap</h1>
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg h-[800px] p-4">
                        <SnpHeatmap />
                    </div>
                </div>
            </DashboardLayout>
        </Suspense>
    );
}
