import React from 'react';
import type { ChartPayload } from '../hooks/useSSE';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  CartesianGrid, Area, AreaChart
} from 'recharts';

/** Curated 10-color palette for chart segments */
const COLORS = [
  '#00ff88', '#00ccff', '#ff6b9d', '#ffd93d', '#c084fc',
  '#ff8042', '#0088fe', '#00c49f', '#ff4466', '#8b5cf6'
];

/** Formats currency values with ₹ symbol */
const formatCurrency = (value: number) => {
  if (value >= 1000) {
    return `₹${(value / 1000).toFixed(1)}K`;
  }
  return `₹${value.toFixed(0)}`;
};

/** Custom glassmorphic tooltip */
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="px-3 py-2 rounded-lg glass-accent shadow-lg">
      <p className="text-xs text-gray-400 mb-1">{label || payload[0]?.name}</p>
      <p className="text-sm font-semibold" style={{ color: '#00ff88' }}>
        ₹{Number(payload[0]?.value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </p>
    </div>
  );
};

export const ChartRenderer: React.FC<{ payload: ChartPayload }> = ({ payload }) => {
  const { chart_type, title, data, summary } = payload;

  return (
    <div className="w-full flex flex-col items-center animate-fade-in-up">
      {/* Chart Title */}
      <h2 className="text-xl font-semibold mb-6 gradient-text tracking-tight">{title}</h2>

      {/* Chart Area */}
      <div className="w-full h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          {chart_type === 'bar' ? (
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis 
                dataKey="name" 
                stroke="#55556a" 
                fontSize={12} 
                tickLine={false} 
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis 
                stroke="#55556a" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false}
                tickFormatter={formatCurrency}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,255,136,0.05)' }} />
              <defs>
                <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00ff88" stopOpacity={1} />
                  <stop offset="100%" stopColor="#00cc6a" stopOpacity={0.8} />
                </linearGradient>
              </defs>
              <Bar 
                dataKey="value" 
                fill="url(#barGradient)" 
                radius={[6, 6, 0, 0]} 
                animationDuration={800}
                animationEasing="ease-out"
              />
            </BarChart>

          ) : chart_type === 'line' ? (
            <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00ff88" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#00ff88" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis 
                dataKey="name" 
                stroke="#55556a" 
                fontSize={12} 
                tickLine={false} 
                axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
              />
              <YAxis 
                stroke="#55556a" 
                fontSize={12} 
                tickLine={false} 
                axisLine={false}
                tickFormatter={formatCurrency}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#00ff88" 
                strokeWidth={2.5}
                fill="url(#lineGradient)"
                animationDuration={1000}
                dot={{ r: 4, fill: '#00ff88', strokeWidth: 0 }}
                activeDot={{ r: 6, fill: '#00ff88', stroke: '#0a0a0f', strokeWidth: 2 }}
              />
            </AreaChart>

          ) : (
            /* Pie Chart */
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={140}
                innerRadius={60}
                fill="#8884d8"
                dataKey="value"
                paddingAngle={2}
                animationDuration={800}
                animationEasing="ease-out"
                label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
              >
                {data.map((_entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={COLORS[index % COLORS.length]}
                    stroke="transparent"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }}
                iconType="circle"
                iconSize={8}
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Claude's Insight Card */}
      {summary && (
        <div className="mt-6 w-full p-4 rounded-xl glass-accent animate-fade-in" 
             style={{ animationDelay: '0.3s', animationFillMode: 'both' }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-[#00ff88] animate-pulse-glow"></div>
            <p className="text-xs font-semibold tracking-wider uppercase" style={{ color: '#00ff88' }}>
              Claude's Insight
            </p>
          </div>
          <p className="text-sm leading-relaxed" style={{ color: '#c0c0d0' }}>
            {summary}
          </p>
        </div>
      )}
    </div>
  );
};
