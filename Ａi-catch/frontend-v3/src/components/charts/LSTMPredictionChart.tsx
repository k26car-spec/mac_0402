'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import type { LSTMPrediction, PredictionHistory } from '@/types/lstm';
import { formatPrice } from '@/lib/utils';

interface LSTMPredictionChartProps {
    data: LSTMPrediction;
    history?: PredictionHistory[];
}

export function LSTMPredictionChart({ data, history }: LSTMPredictionChartProps) {
    // 构建图表数据
    const chartData = [
        // 历史数据点（如果有）
        ...(history || []).map((item) => ({
            date: item.date,
            actual: item.actual,
            type: 'history',
        })),

        // 当前价格点
        {
            date: '今天',
            actual: data.currentPrice,
            predicted: data.currentPrice,
            type: 'current',
        },

        // 预测数据点
        {
            date: '+1天',
            predicted: data.predictions.day1,
            type: 'prediction',
        },
        {
            date: '+3天',
            predicted: data.predictions.day3,
            type: 'prediction',
        },
        {
            date: '+5天',
            predicted: data.predictions.day5,
            type: 'prediction',
        },
    ];

    return (
        <div className="w-full h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={chartData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

                    <XAxis
                        dataKey="date"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                    />

                    <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={(value) => formatPrice(value, 0)}
                    />

                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'white',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '12px',
                        }}
                        formatter={(value: number) => [formatPrice(value, 2), '']}
                    />

                    <Legend
                        wrapperStyle={{ paddingTop: '20px' }}
                    />

                    {/* 实际价格线 */}
                    <Area
                        type="monotone"
                        dataKey="actual"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorActual)"
                        name="实际价格"
                        dot={{ r: 4, fill: '#3b82f6' }}
                    />

                    {/* 预测价格线 */}
                    <Area
                        type="monotone"
                        dataKey="predicted"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        fillOpacity={1}
                        fill="url(#colorPredicted)"
                        name="预测价格"
                        dot={{ r: 4, fill: '#f59e0b' }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
