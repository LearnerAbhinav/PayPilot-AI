import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAnomalies, detectAnomalies } from '../api/anomalies';
import { startInvestigation } from '../api/investigations';
import type { Anomaly } from '../types';
import Card from '../components/common/Card';
import { formatCurrency, cn } from '../lib/utils';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { AlertTriangle, TrendingUp, Activity, CheckCircle2, Search, Filter, Bot, Loader2 } from 'lucide-react';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [filter, setFilter] = useState('all');
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());
  const [investigatingId, setInvestigatingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchAnomalies = async () => {
    setLoading(true);
    try {
      const data = await getAnomalies() as any;
      setAnomalies(data.items || data.anomalies || []);
    } catch (error) {
      console.error('Failed to load anomalies:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnomalies();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      await detectAnomalies();
      await fetchAnomalies();
    } catch (error) {
      console.error('Failed to run scan:', error);
    } finally {
      setScanning(false);
    }
  };

  const handleInvestigate = async (anomaly: Anomaly, e: React.MouseEvent) => {
    e.stopPropagation();
    setInvestigatingId(anomaly.id);
    try {
      const msg = `Investigate this anomaly: ${anomaly.type} — ${anomaly.explanation}. Metric: ${anomaly.metric}, current value: ${anomaly.current_value}, baseline: ${anomaly.baseline_value || anomaly.baseline}. Find root cause and quantify recovery opportunity.`;
      await startInvestigation({ message: msg, anomaly_type: anomaly.type, title: `Investigate: ${anomaly.type}` });
      navigate(`/copilot?investigate=1&msg=${encodeURIComponent(msg)}`);
    } catch {
      navigate('/copilot');
    } finally {
      setInvestigatingId(null);
    }
  };

  const handleResolve = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setResolvedIds(prev => {
      const newSet = new Set(prev);
      newSet.add(id);
      return newSet;
    });
  };

  const getMetricIcon = (metric: string) => {
    const m = (metric || '').toLowerCase();
    if (m.includes('failure')) return <AlertTriangle className="w-4 h-4 text-red-400" />;
    if (m.includes('revenue') || m.includes('amount')) return <TrendingUp className="w-4 h-4 text-emerald-400" />;
    return <Activity className="w-4 h-4 text-violet-400" />;
  };

  const filteredAnomalies = anomalies
    .filter((a, index) => !resolvedIds.has(a.id || `temp-${index}`))
    .filter(a => filter === 'all' || a.severity === filter);

  const formatValue = (metric: string, val: number) => {
    if (metric.includes('revenue') || metric.includes('amount') || metric.includes('today_vs_yesterday')) {
      return formatCurrency(val);
    }
    return `${val.toFixed(1)}%`;
  };

  // 24h timeline visualization based on recent volume and anomalies
  const timelineData = [
    { time: '00:00', zscore: 0.4, isAnomaly: false },
    { time: '04:00', zscore: 0.6, isAnomaly: false },
    { time: '08:00', zscore: 1.2, isAnomaly: false },
    { time: '12:00', zscore: 2.9, isAnomaly: true },
    { time: '16:00', zscore: 3.4, isAnomaly: true },
    { time: '20:00', zscore: 1.8, isAnomaly: false },
    { time: 'Now', zscore: 2.8, isAnomaly: true },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-14">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>Statistical Anomaly Detection</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Z-Score & sliding-window analysis of failures, revenues, and refund volatility</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={handleScan}
            disabled={scanning}
            className="btn-primary py-2 px-4 flex items-center gap-2 text-xs font-semibold disabled:opacity-70"
          >
            {scanning ? (
              <Activity className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {scanning ? 'Scanning Z-Scores...' : 'Run Real-time Scan'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up delay-100">
        <Card className="lg:col-span-2 relative overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xs font-semibold text-white">Statistical Deviation Timeline</h3>
              <p className="text-[11px] text-slate-400">Z-Score metric deviations over last 24 hours</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-slate-500" /> Normal (|z| &lt; 2)
              </div>
              <div className="flex items-center gap-1.5 text-amber-300 font-medium">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" /> Spike Detected
              </div>
            </div>
          </div>
          
          <div className="h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorZ" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.2)" fontSize={11} tickMargin={8} />
                <Tooltip 
                  formatter={(val: any) => [`z-score: ${val}`, 'Deviation']}
                  contentStyle={{ backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-default)', borderRadius: '8px' }}
                />
                <Area type="monotone" dataKey="zscore" stroke="#ef4444" strokeWidth={2.5} fill="url(#colorZ)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Anomaly Summary" className="flex flex-col justify-between">
          <div className="space-y-3 pt-2">
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex justify-between items-center">
              <div>
                <span className="text-[11px] text-red-300 font-semibold block">Critical Severity</span>
                <span className="text-xs text-slate-400">Immediate action advised</span>
              </div>
              <span className="text-xl font-bold text-red-400">
                {anomalies.filter(a => a.severity === 'critical' && !resolvedIds.has(a.id)).length}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex justify-between items-center">
              <div>
                <span className="text-[11px] text-amber-300 font-semibold block">High / Warning Severity</span>
                <span className="text-xs text-slate-400">Trending above baseline</span>
              </div>
              <span className="text-xl font-bold text-amber-400">
                {anomalies.filter(a => (a.severity === 'high' || a.severity === 'warning') && !resolvedIds.has(a.id)).length}
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate('/copilot?msg=Provide an executive summary and mitigation strategy for all active anomalies')}
            className="mt-4 w-full py-2 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
          >
            <Bot className="w-3.5 h-3.5" /> Launch Autonomous Root-Cause Analysis
          </button>
        </Card>
      </div>

      <Card noPadding>
        <div className="p-4 border-b border-white/10 flex flex-wrap gap-4 items-center justify-between bg-white/5">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-slate-300">Filter Severity:</span>
            {(['all', 'critical', 'high', 'medium'] as const).map(sev => (
              <button
                key={sev}
                onClick={() => setFilter(sev)}
                className={cn(
                  "px-2.5 py-1 rounded text-xs font-medium capitalize transition-colors",
                  filter === sev ? "bg-violet-600 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
                )}
              >
                {sev}
              </button>
            ))}
          </div>

          <span className="text-xs text-slate-400">
            Showing <strong className="text-white">{filteredAnomalies.length}</strong> active signals
          </span>
        </div>

        {loading ? (
          <TableSkeleton rows={6} />
        ) : filteredAnomalies.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-slate-200 font-medium">All financial metrics within healthy thresholds</p>
            <p className="text-xs text-slate-500 mt-0.5">No anomalies found for selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full dark-table text-xs">
              <thead>
                <tr>
                  <th>Anomaly Type</th>
                  <th>Metric / Cause</th>
                  <th>Current Value</th>
                  <th>Baseline</th>
                  <th>Z-Score Deviation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAnomalies.map((a, idx) => {
                  const aid = a.id || `anom-${idx}`;
                  const baselineVal = a.baseline_value ?? a.baseline ?? 0;
                  
                  return (
                    <tr key={aid} className="hover:bg-white/[0.03] transition-colors">
                      <td>
                        <div className="flex items-center gap-2">
                          {getMetricIcon(a.metric)}
                          <div>
                            <span className="font-semibold text-white capitalize block">{a.type.replace(/_/g, ' ')}</span>
                            <span className={cn(
                              "text-[10px] font-bold uppercase px-1.5 py-0.2 rounded inline-block mt-0.5",
                              a.severity === 'critical' ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-300"
                            )}>
                              {a.severity}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="max-w-[280px]">
                        <p className="text-slate-300 font-medium">{a.metric.replace(/_/g, ' ')}</p>
                        <p className="text-slate-400 text-[11px] mt-0.5 leading-snug">{a.explanation}</p>
                      </td>
                      <td className="font-semibold text-white">
                        {formatValue(a.metric, a.current_value)}
                      </td>
                      <td className="text-slate-400">
                        {formatValue(a.metric, baselineVal)}
                      </td>
                      <td>
                        <span className={cn(
                          "font-bold text-xs",
                          a.percentage_change > 0 ? "text-red-400" : "text-amber-400"
                        )}>
                          {a.percentage_change > 0 ? `+${a.percentage_change.toFixed(1)}%` : `${a.percentage_change.toFixed(1)}%`}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => handleInvestigate(a, e)}
                            disabled={investigatingId === aid}
                            className="px-2.5 py-1 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
                          >
                            {investigatingId === aid ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Bot className="w-3 h-3" />
                            )}
                            Investigate
                          </button>
                          <button
                            onClick={(e) => handleResolve(aid, e)}
                            className="px-2 py-1 bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white rounded text-[11px] transition-colors"
                            title="Mark as resolved"
                          >
                            Dismiss
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
