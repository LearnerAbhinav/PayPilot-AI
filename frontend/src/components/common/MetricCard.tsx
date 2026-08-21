import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  change?: number;
  changeLabel?: string;
  accent?: 'violet' | 'green' | 'red' | 'amber' | 'cyan';
  delay?: number;
  sparklineData?: any[];
}

export default function MetricCard({
  icon,
  label,
  value,
  change,
  changeLabel,
  accent = 'violet',
  delay = 0,
  sparklineData,
}: MetricCardProps) {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;

  const accentBorder = {
    violet: 'card-accent-violet',
    green: 'card-accent-green',
    red: 'card-accent-red',
    amber: 'card-accent-amber',
    cyan: 'card-accent-cyan',
  }[accent];

  const accentIcon = {
    violet: 'bg-violet-500/10 text-violet-400 group-hover:bg-violet-500/20 group-hover:shadow-[0_0_15px_rgba(124,58,237,0.3)]',
    green: 'bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 group-hover:shadow-[0_0_15px_rgba(16,185,129,0.3)]',
    red: 'bg-red-500/10 text-red-400 group-hover:bg-red-500/20 group-hover:shadow-[0_0_15px_rgba(239,68,68,0.3)]',
    amber: 'bg-amber-500/10 text-amber-400 group-hover:bg-amber-500/20 group-hover:shadow-[0_0_15px_rgba(245,158,11,0.3)]',
    cyan: 'bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)]',
  }[accent];

  const chartColor = {
    violet: '#7c3aed',
    green: '#10b981',
    red: '#ef4444',
    amber: '#f59e0b',
    cyan: '#06b6d4',
  }[accent];

  return (
    <div
      className={cn('glass-card p-5 transition-all duration-300 hover:border-white/[0.14] animate-fade-in-up group relative overflow-hidden', accentBorder)}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Background glow on hover */}
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
        style={{ 
          background: `radial-gradient(circle at top right, ${chartColor}, transparent 70%)` 
        }}
      />
      
      <div className="flex items-start justify-between gap-3 relative z-10">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider transition-colors" style={{ color: 'var(--text-muted)' }}>
            {label}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight group-hover:scale-[1.02] origin-left transition-transform" style={{ color: 'var(--text-primary)' }}>
            {value}
          </p>
          
          <div className="flex items-center justify-between mt-3">
            {change !== undefined && (
              <div className="flex items-center gap-1.5" title={change !== 0 ? `${change > 0 ? '+' : ''}${change.toFixed(2)}% vs last period` : 'No change'}>
                <span
                  className={cn(
                    'inline-flex items-center gap-1 text-xs font-semibold px-1.5 py-0.5 rounded transition-colors',
                    isPositive && 'bg-emerald-500/10 text-emerald-500 font-bold',
                    isNegative && 'bg-red-500/10 text-red-500 font-bold',
                    !isPositive && !isNegative && 'bg-white/5 text-slate-400'
                  )}
                >
                  {isPositive ? <TrendingUp className="w-3 h-3" /> : isNegative ? <TrendingDown className="w-3 h-3" /> : null}
                  {change > 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
                {changeLabel && (
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {changeLabel}
                  </span>
                )}
              </div>
            )}

            {sparklineData && sparklineData.length > 0 && (
              <div className="w-16 h-8 ml-auto opacity-70 group-hover:opacity-100 transition-opacity">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sparklineData}>
                    <defs>
                      <linearGradient id={`color-${accent}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartColor} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={chartColor} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke={chartColor} 
                      fill={`url(#color-${accent})`} 
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
        <div className={cn('p-2.5 rounded-lg flex-shrink-0 transition-all duration-300', accentIcon)}>
          {icon}
        </div>
      </div>
    </div>
  );
}
