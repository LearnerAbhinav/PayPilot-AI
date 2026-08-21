import React, { useEffect, useState } from 'react';
import { getMetrics, getRevenueTrend, getPaymentMethodBreakdown } from '../api/analytics';
import type { MetricSummary, RevenueTrendPoint, PaymentMethodBreakdown } from '../types';
import Card from '../components/common/Card';
import MetricCard from '../components/common/MetricCard';
import { SkeletonCard, SkeletonChart } from '../components/common/SkeletonLoader';
import { formatCurrency, cn } from '../lib/utils';
import {
  IndianRupee,
  Activity,
  AlertTriangle,
  TrendingUp,
  Download,
  Calendar,
} from 'lucide-react';
import {
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ComposedChart,
  Line
} from 'recharts';

// Mock heatmap data
const generateHeatmapData = () => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const hours = ['00', '04', '08', '12', '16', '20'];
  return days.flatMap((day, dIdx) => 
    hours.map((hour, hIdx) => ({
      day,
      hour,
      value: Math.floor(Math.random() * 100) + (dIdx > 4 ? 20 : 50) + (hIdx > 1 && hIdx < 5 ? 40 : 0)
    }))
  );
};

// Mock funnel data
const funnelData = [
  { stage: 'Checkout Initiated', count: 12500, dropoff: 0 },
  { stage: 'Payment Authorized', count: 9800, dropoff: 21.6 },
  { stage: 'Payment Captured', count: 9100, dropoff: 7.1 },
  { stage: 'Settled to Bank', count: 9050, dropoff: 0.5 },
];

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [trend, setTrend] = useState<RevenueTrendPoint[]>([]);
  const [methods, setMethods] = useState<PaymentMethodBreakdown[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);
  const [compareMode, setCompareMode] = useState(false);
  const [heatmapData] = useState(generateHeatmapData());

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [metricsData, trendData, methodsData] = await Promise.all([
          getMetrics(period),
          getRevenueTrend(period),
          getPaymentMethodBreakdown(period),
        ]);
        const m: any = metricsData;
        const formattedMetrics = [
          { label: 'Total Revenue', value: m.total_revenue, change: 0, change_label: 'vs last period' },
          { label: 'Transactions', value: m.total_count, change: 0, change_label: 'vs last period' },
          { label: 'Success Rate', value: m.success_rate, change: 0, change_label: 'vs last period' },
          { label: 'Avg Value', value: m.avg_transaction_value, change: 0, change_label: 'vs last period' }
        ];
        const methodsArr = methodsData as any[];
        const totalMethodsCount = methodsArr.reduce((acc, m) => acc + m.count, 0);
        const methodsWithPercentage = methodsArr.map(m => ({
          ...m,
          percentage: totalMethodsCount > 0 ? (m.count / totalMethodsCount) * 100 : 0
        }));

        setMetrics(formattedMetrics as any);
        setTrend(trendData as any);
        setMethods(methodsWithPercentage as any);
      } catch (error) {
        console.error('Failed to load analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);

  const COLORS = ['#7c3aed', '#10b981', '#ef4444', '#f59e0b', '#06b6d4'];

  const getHeatmapColor = (value: number) => {
    if (value < 30) return 'rgba(124, 58, 237, 0.1)';
    if (value < 60) return 'rgba(124, 58, 237, 0.3)';
    if (value < 90) return 'rgba(124, 58, 237, 0.6)';
    return 'rgba(124, 58, 237, 1)';
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex justify-between items-end mb-6">
          <div className="h-8 w-48 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart className="h-[400px]" />
          <SkeletonChart className="h-[400px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>Analytics Deep Dive</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Advanced insights into your payment performance</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div 
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)' }}
          >
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Compare</span>
            <div 
              className={cn("w-8 h-4 rounded-full relative cursor-pointer transition-colors", compareMode ? "bg-violet-600" : "bg-slate-300 dark:bg-white/20")}
              onClick={() => setCompareMode(!compareMode)}
            >
              <div className={cn("absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform shadow-sm", compareMode ? "left-4.5" : "left-0.5")} />
            </div>
          </div>
          
          <div 
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)' }}
          >
            <Calendar className="w-4 h-4 text-violet-600 dark:text-violet-400" />
            <select
              className="bg-transparent text-sm font-medium outline-none cursor-pointer"
              style={{ color: 'var(--text-primary)' }}
              value={period}
              onChange={(e) => setPeriod(Number(e.target.value))}
            >
              <option value={7} style={{ background: 'var(--bg-card)', color: 'var(--text-primary)' }}>Last 7 days</option>
              <option value={30} style={{ background: 'var(--bg-card)', color: 'var(--text-primary)' }}>Last 30 days</option>
              <option value={90} style={{ background: 'var(--bg-card)', color: 'var(--text-primary)' }}>Last 90 days</option>
            </select>
          </div>
          
          <button 
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-semibold transition-all border shadow-sm hover:opacity-80"
            style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
          >
            <Download className="w-4 h-4" /> <span className="hidden sm:inline">Export PDF</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        {metrics.map((metric, index) => {
          const icons = [IndianRupee, Activity, AlertTriangle, TrendingUp];
          const accents = ['violet', 'cyan', 'red', 'green'];
          const Icon = icons[index % icons.length];
          return (
            <MetricCard
              key={metric.label}
              label={metric.label}
              value={
                metric.label.toLowerCase().includes('revenue') || metric.label.toLowerCase().includes('value')
                  ? formatCurrency(metric.value)
                  : metric.label.toLowerCase().includes('rate')
                  ? `${metric.value.toFixed(1)}%`
                  : metric.value.toLocaleString()
              }
              change={compareMode ? metric.change : undefined}
              changeLabel={compareMode ? metric.change_label : undefined}
              icon={<Icon className="w-5 h-5" />}
              accent={accents[index % accents.length] as any}
              delay={index * 50}
            />
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Revenue vs Transactions" subtitle="Volume correlation over time" className="animate-fade-in-up delay-200">
          <div className="h-[300px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenueAnalytics" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(val) => new Date(val).getDate().toString()}
                  stroke="rgba(255,255,255,0.2)"
                  fontSize={12}
                />
                <YAxis 
                  yAxisId="left"
                  tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                  stroke="rgba(255,255,255,0.2)"
                  fontSize={12}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  stroke="rgba(255,255,255,0.2)"
                  fontSize={12}
                />
                <Tooltip 
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
                />
                <Area 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="revenue" 
                  stroke="#7c3aed" 
                  fillOpacity={1} 
                  fill="url(#colorRevenueAnalytics)" 
                />
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="transactions" 
                  stroke="#06b6d4" 
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Payment Funnel" subtitle="Conversion drop-off analysis" className="animate-fade-in-up delay-300">
          <div className="h-[300px] w-full mt-4 flex flex-col justify-center px-4">
            {funnelData.map((stage) => {
              const maxCount = funnelData[0].count;
              const width = `${(stage.count / maxCount) * 100}%`;
              return (
                <div key={stage.stage} className="relative mb-6 last:mb-0">
                  <div className="flex justify-between items-end mb-1">
                    <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{stage.stage}</span>
                    <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{stage.count.toLocaleString()}</span>
                  </div>
                  <div 
                    className="h-6 rounded-r-full overflow-hidden w-full relative"
                    style={{ background: 'var(--bg-elevated)' }}
                  >
                    <div 
                      className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-violet-600 via-indigo-600 to-purple-500 rounded-r-full transition-all duration-1000 shadow-sm"
                      style={{ width }}
                    >
                      <div className="absolute inset-0 bg-white/15 animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                    </div>
                  </div>
                  {stage.dropoff > 0 && (
                    <div className="absolute -bottom-5 right-0 text-[10px] text-red-600 dark:text-red-400 font-semibold">
                      -{stage.dropoff}% drop
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Transaction Heatmap" subtitle="Volume by day and hour" className="lg:col-span-2 animate-fade-in-up delay-400">
          <div className="mt-4 overflow-x-auto">
            <div className="min-w-[500px]">
              <div className="grid grid-cols-7 gap-1">
                <div className="col-span-1" />
                {['00h', '04h', '08h', '12h', '16h', '20h'].map(h => (
                  <div key={h} className="text-center text-xs text-slate-400">{h}</div>
                ))}
                
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
                  <React.Fragment key={day}>
                    <div className="text-xs text-slate-400 flex items-center">{day}</div>
                    {['00', '04', '08', '12', '16', '20'].map(hour => {
                      const data = heatmapData.find(d => d.day === day && d.hour === hour);
                      return (
                        <div 
                          key={`${day}-${hour}`}
                          className="h-10 rounded-sm transition-transform hover:scale-110 cursor-pointer"
                          style={{ backgroundColor: getHeatmapColor(data?.value || 0) }}
                          title={`${day} ${hour}:00 - ${data?.value || 0} txns`}
                        />
                      )
                    })}
                  </React.Fragment>
                ))}
              </div>
              <div className="flex items-center justify-end gap-2 mt-4 text-xs text-slate-400">
                <span>Low</span>
                <div className="w-24 h-2 rounded bg-gradient-to-r from-violet-500/10 to-violet-600" />
                <span>High</span>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Payment Methods" subtitle="Distribution by volume" className="animate-fade-in-up delay-500">
          <div className="h-[250px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={methods} layout="vertical" margin={{ top: 0, right: 30, left: 20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" hide />
                <YAxis 
                  dataKey="method" 
                  type="category" 
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(value: any) => [`${value}%`, 'Share']}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
                />
                <Bar dataKey="percentage" radius={[0, 4, 4, 0]}>
                  {methods.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
