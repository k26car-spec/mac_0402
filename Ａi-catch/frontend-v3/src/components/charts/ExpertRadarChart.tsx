'use client';

import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { ExpertSignal } from '@/types/analysis';

interface ExpertRadarChartProps {
    signals: ExpertSignal[];
}

export function ExpertRadarChart({ signals }: ExpertRadarChartProps) {
    // 轉換數據格式
    const chartData = signals.map(signal => ({
        name: signal.name,
        score: signal.score * 100, // 轉換為 0-100 分數
        fullMark: 100,
    }));

    return (
        <div className="w-full h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={chartData}>
                    <PolarGrid stroke="#e5e7eb" />

                    <PolarAngleAxis
                        dataKey="name"
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        tickLine={false}
                    />

                    <PolarRadiusAxis
                        angle={90}
                        domain={[0, 100]}
                        tick={{ fill: '#6b7280', fontSize: 10 }}
                        tickCount={5}
                    />

                    <Radar
                        name="專家評分"
                        dataKey="score"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.6}
                        dot={{ r: 4, fill: '#3b82f6' }}
                    />

                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'white',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '8px 12px',
                        }}
                        formatter={(value: number) => [`${value.toFixed(1)} 分`, '評分']}
                    />

                    <Legend
                        wrapperStyle={{ paddingTop: '20px' }}
                        iconType="circle"
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    );
}
