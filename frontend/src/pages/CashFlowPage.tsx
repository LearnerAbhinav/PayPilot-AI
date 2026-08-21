import { useEffect, useState } from 'react';
import { getCashFlowForecast } from '../api/forecast';
import type { CashFlowForecast } from '../types';
import Card from '../components/common/Card';
import MetricCard from '../components/common/MetricCard';
import { SkeletonCard, SkeletonChart } from '../components/common/SkeletonLoader';
import { formatCurrency, cn } from '../lib/utils';
import { IndianRupee, TrendingDown, TrendingUp, AlertTriangle, ShieldCheck, Download, Activity } from 'lucide-react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function CashFlowPage() {
  const [data, setData] = useState<CashFlowForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [scenario, setScenario] = useState<'expected' | 'optimistic' | 'pessimistic'>('expected');
  const [days, setDays] = useState(14);
  const [alertThreshold, setAlertThreshold] = useState(100000); // 1 Lakh threshold

  useEffect(() => {
    const fetchForecast = async () => {
      setLoading(true);
      try {
        const result = await getCashFlowForecast(days) as any;
        setData(result);
      } catch (error) {
        console.error('Failed to load forecast:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchForecast();
  }, [days]);

  // Transform data based on selected scenario
  const getChartData = () => {
    if (!data) return [];
    
    // We only have future predictions from backend in daily_predictions
    const predictions = (data as any).daily_predictions || [];
    
    return predictions.map((point: any) => {
      let predictedValue = point.predicted_balance;
      
      if (predictedValue !== null && predictedValue !== undefined) {
        if (scenario === 'optimistic') {
          predictedValue = predictedValue + (predictedValue * 0.15); // +15%
        } else if (scenario === 'pessimistic') {
          predictedValue = Math.max(0, predictedValue - (predictedValue * 0.20)); // -20%
        }
      }
      
      return {
        date: new Date(point.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
        fullDate: point.date,
        actual: null,
        predicted: predictedValue,
        // Confidence interval only for expected scenario
        lowerBound: scenario === 'expected' ? predictedValue * 0.9 : null,
        upperBound: scenario === 'expected' ? predictedValue * 1.1 : null,
        threshold: alertThreshold
      };
    });
  };

  const isLowBalanceAlert = data && getChartData().some((p: any) => p.predicted !== null && p.predicted < alertThreshold);
  
  // Calculate totals from predictions
  const predictions = data ? (data as any).daily_predictions || [] : [];
  const totalInflow = predictions.reduce((acc: number, p: any) => acc + (p.predicted_inflow || 0), 0);
  const totalOutflow = predictions.reduce((acc: number, p: any) => acc + (p.predicted_outflow || 0), 0);
  const riskLevel = data ? (data as any).overall_risk_level || 'low' : 'low';

  if (loading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex justify-between items-end mb-6">
          <div className="h-8 w-48 bg-white/10 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
        </div>
        <Card><SkeletonChart className="h-[400px]" /></Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>Cash Flow Intelligence</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Predictive liquidity analysis & forecasting</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
            {[7, 14, 30].map(d => (
              <button 
                key={d}
                onClick={() => setDays(d)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  days === d ? "bg-white/10 text-white shadow-sm" : "text-slate-400 hover:text-white"
                )}
              >
                {d}D
              </button>
            ))}
          </div>
          
          <button className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-lg text-sm font-medium transition-colors">
            <Download className="w-4 h-4" /> <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {isLowBalanceAlert && (
        <div className="animate-fade-in-up delay-50 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-4 shadow-[0_0_20px_rgba(239,68,68,0.15)]">
          <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5 text-red-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-red-400">Low Balance Risk Detected</h3>
            <p className="text-sm text-red-300/80 mt-1 mb-3 max-w-2xl">
              Based on the current forecast, your cash balance is projected to fall below the minimum threshold of {formatCurrency(alertThreshold)} within the next {days} days.
            </p>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors">
                View Risk Assessment
              </button>
              <button className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-lg text-sm font-medium transition-colors">
                Adjust Threshold
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 animate-fade-in-up delay-100">
        <MetricCard
          label="Current Balance"
          value={formatCurrency(data.current_balance)}
          icon={<IndianRupee className="w-5 h-5" />}
          accent="violet"
        />
        <MetricCard
          label="Projected Inflow"
          value={formatCurrency(totalInflow)}
          icon={<TrendingUp className="w-5 h-5" />}
          accent="green"
        />
        <MetricCard
          label="Projected Outflow"
          value={formatCurrency(totalOutflow)}
          icon={<TrendingDown className="w-5 h-5" />}
          accent="red"
        />
      </div>

      <Card className="animate-fade-in-up delay-200 p-0 overflow-hidden relative">
        {/* Scenario Tabs */}
        <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <h3 className="text-base font-semibold text-white">Cash Balance Projection</h3>
            <div className="flex items-center gap-1 bg-black/20 rounded-lg p-1 border border-white/5">
              {[
                { id: 'optimistic', label: 'Optimistic' },
                { id: 'expected', label: 'Expected' },
                { id: 'pessimistic', label: 'Pessimistic' },
              ].map(s => (
                <button
                  key={s.id}
                  onClick={() => setScenario(s.id as any)}
                  className={cn(
                    "px-4 py-1.5 rounded-md text-xs font-medium transition-all relative",
                    scenario === s.id 
                      ? "bg-violet-600 text-white shadow-lg shadow-violet-600/20" 
                      : "text-slate-400 hover:text-white"
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Risk Level:</span>
            <span className={cn(
              "px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5",
              riskLevel === 'high' || riskLevel === 'critical' ? 'bg-red-500/20 text-red-400' :
              riskLevel === 'medium' ? 'bg-amber-500/20 text-amber-400' :
              'bg-emerald-500/20 text-emerald-400'
            )}>
              {(riskLevel === 'high' || riskLevel === 'critical') && <AlertTriangle className="w-3 h-3" />}
              {riskLevel === 'medium' && <Activity className="w-3 h-3" />}
              {riskLevel === 'low' && <ShieldCheck className="w-3 h-3" />}
              {riskLevel}
            </span>
          </div>
        </div>

        <div className="h-[450px] w-full p-6">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={getChartData()} margin={{ top: 20, right: 20, left: 20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="date" 
                stroke="rgba(255,255,255,0.3)"
                fontSize={12}
                tickMargin={12}
              />
              <YAxis 
                tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                stroke="rgba(255,255,255,0.3)"
                fontSize={12}
                domain={['dataMin - 50000', 'dataMax + 50000']}
              />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px' }}
                formatter={(value: any, name: any) => [formatCurrency(Number(value || 0)), name === 'actual' ? 'Actual Balance' : name === 'predicted' ? 'Forecasted Balance' : String(name || '')]}
                labelStyle={{ color: 'var(--text-secondary)' }}
              />
              
              {/* Threshold line */}
              <Line 
                type="step" 
                dataKey="threshold" 
                stroke="#ef4444" 
                strokeWidth={1} 
                strokeDasharray="5 5" 
                dot={false}
                activeDot={false}
                name="Alert Threshold"
              />

              {/* Confidence Interval (only in expected scenario) */}
              {scenario === 'expected' && (
                <Area 
                  type="monotone" 
                  dataKey="upperBound" 
                  stroke="none" 
                  fill="rgba(6, 182, 212, 0.05)" 
                  activeDot={false}
                />
              )}
              {scenario === 'expected' && (
                <Area 
                  type="monotone" 
                  dataKey="lowerBound" 
                  stroke="none" 
                  fill="var(--bg-card)" 
                  activeDot={false}
                />
              )}

              {/* Actual Data Line */}
              <Area 
                type="monotone" 
                dataKey="actual" 
                stroke="#7c3aed" 
                strokeWidth={3}
                fill="url(#colorActual)" 
                connectNulls
              />
              
              {/* Predicted Data Line */}
              <Area 
                type="monotone" 
                dataKey="predicted" 
                stroke={scenario === 'optimistic' ? '#10b981' : scenario === 'pessimistic' ? '#f59e0b' : '#06b6d4'} 
                strokeWidth={3}
                strokeDasharray="6 6"
                fill="url(#colorPredicted)" 
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in-up delay-300">
        <Card title="Forecast Assumptions" subtitle="Variables powering the AI model">
          <div className="space-y-4 mt-4">
            {data.assumptions.map((assumption, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/10 transition-colors hover:bg-white/10">
                <div className="w-6 h-6 rounded-full bg-violet-500/20 text-violet-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-bold">{idx + 1}</span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">{assumption}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Threshold Settings" subtitle="Configure alert triggers">
          <div className="mt-4 space-y-6">
            <div>
              <div className="flex justify-between items-end mb-2">
                <label className="text-sm font-medium text-slate-300">Minimum Balance Alert</label>
                <span className="text-lg font-bold text-white">{formatCurrency(alertThreshold)}</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="500000" 
                step="10000"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-violet-500"
              />
              <div className="flex justify-between mt-2 text-xs text-slate-500">
                <span>₹0</span>
                <span>₹5,00,000</span>
              </div>
            </div>
            
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <h4 className="text-sm font-semibold text-blue-400 mb-1">Why set a threshold?</h4>
              <p className="text-xs text-blue-300/80 leading-relaxed">
                PayPilot AI will notify you immediately if forecasted cash flow dips below this amount, giving you time to delay vendor payments or expedite receivables.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
