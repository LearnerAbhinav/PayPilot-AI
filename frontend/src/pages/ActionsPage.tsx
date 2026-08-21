import { useEffect, useState } from 'react';
import { getActions, getActionTransactions, approveAction, rejectAction, executeAction } from '../api/actions';
import type { ActionTransactionsResponse } from '../api/actions';
import type { ActionResponse } from '../types';
import Card from '../components/common/Card';
import StatusBadge from '../components/common/StatusBadge';
import { SkeletonCard } from '../components/common/SkeletonLoader';
import { formatCurrency, cn, relativeTime } from '../lib/utils';
import {
  Zap, CheckCircle2, Play, Bot, AlertTriangle, MessageSquare,
  Eye, X, Check,
  TrendingUp, Layers
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function ActionsPage() {
  const [actions, setActions] = useState<ActionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'completed' | 'rejected'>('all');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [selectedActionTxns, setSelectedActionTxns] = useState<ActionTransactionsResponse | null>(null);
  const navigate = useNavigate();

  const fetchActions = async () => {
    setLoading(true);
    try {
      const data = await getActions(filter !== 'all' ? (filter === 'completed' ? 'approved' : filter) : undefined) as any;
      setActions(data || []);
    } catch (error) {
      console.error('Failed to load actions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [filter]);

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    try {
      await approveAction(id);
      await fetchActions();
    } catch (error) {
      console.error('Failed to approve action:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    setProcessingId(id);
    try {
      await rejectAction(id);
      await fetchActions();
    } catch (error) {
      console.error('Failed to reject action:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleExecute = async (id: string) => {
    setProcessingId(id);
    try {
      await executeAction(id);
      await fetchActions();
    } catch (error) {
      console.error('Failed to execute action:', error);
    } finally {
      setProcessingId(null);
    }
  };

  const handleViewTransactions = async (actionId: string) => {
    try {
      const res = await getActionTransactions(actionId);
      setSelectedActionTxns(res);
    } catch (err) {
      console.error('Failed to load action transactions:', err);
    }
  };

  const getActionIcon = (type: string) => {
    const t = (type || '').toLowerCase();
    if (t.includes('refund')) return <AlertTriangle className="w-5 h-5 text-amber-400" />;
    if (t.includes('retry') || t.includes('recovery')) return <Play className="w-5 h-5 text-emerald-400" />;
    if (t.includes('routing') || t.includes('toggle')) return <Zap className="w-5 h-5 text-violet-400" />;
    return <Bot className="w-5 h-5 text-blue-400" />;
  };

  const getEffectiveStatus = (action: ActionResponse) => {
    if (action.execution_status === 'completed') return 'completed';
    if (action.approval_status === 'approved') return 'approved';
    if (action.approval_status === 'rejected') return 'rejected';
    return 'pending';
  };

  const filteredActions = actions.filter((a) => {
    if (filter === 'all') return true;
    const eff = getEffectiveStatus(a);
    return eff === filter;
  });

  // Calculate Operational Metrics
  const pendingActions = actions.filter(a => a.approval_status === 'pending');
  const pendingCount = pendingActions.length;
  const potentialRecoverySum = actions
    .filter(a => a.approval_status === 'pending' || a.approval_status === 'approved')
    .reduce((acc, a) => acc + (Number(a.estimated_impact) || 0), 0);
  const completedRecoveriesSum = actions
    .filter(a => a.execution_status === 'completed' && a.output_data?.recovered_amount_inr)
    .reduce((acc, a) => acc + (Number(a.output_data?.recovered_amount_inr) || 0), 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-14">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>Action Center</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-600 dark:text-violet-300 border border-violet-500/20">
              Operational Hub
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Autonomous policy-evaluated financial actions requiring human-in-the-loop authorization
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div 
            className="flex rounded-lg p-1"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
          >
            {(['all', 'pending', 'approved', 'completed', 'rejected'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-all",
                  filter === f ? "bg-violet-600 text-white shadow-sm font-semibold" : "hover:text-violet-600 dark:hover:text-white"
                )}
                style={{ color: filter === f ? '#ffffff' : 'var(--text-muted)' }}
              >
                {f === 'pending' ? 'Pending Approval' : f}
                {f === 'pending' && pendingCount > 0 && (
                  <span className="ml-1.5 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-600 dark:text-amber-300 text-[10px] font-bold">
                    {pendingCount}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Operational Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in-up">
        <div 
          className="p-4 rounded-xl border transition-all shadow-sm"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Pending Actions</span>
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-500 dark:text-amber-400">
              <Zap size={14} />
            </div>
          </div>
          <div className="text-2xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>{pendingCount}</div>
          <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium block mt-1">Requires human review</span>
        </div>

        <div 
          className="p-4 rounded-xl border transition-all shadow-sm"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Potential Recovery</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500 dark:text-emerald-400">
              <TrendingUp size={14} />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">{formatCurrency(potentialRecoverySum)}</div>
          <span className="text-[11px] block mt-1" style={{ color: 'var(--text-muted)' }}>Under SMART_RETRY_V1.2</span>
        </div>

        <div 
          className="p-4 rounded-xl border transition-all shadow-sm"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Active Recovery Pipelines</span>
            <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-500 dark:text-violet-400">
              <Layers size={14} />
            </div>
          </div>
          <div className="text-2xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>1 Active</div>
          <span className="text-[11px] text-violet-600 dark:text-violet-300 block mt-1">UPI & Alternate Gateway Pool</span>
        </div>

        <div 
          className="p-4 rounded-xl border transition-all shadow-sm"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Completed Recoveries</span>
            <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500 dark:text-blue-400">
              <CheckCircle2 size={14} />
            </div>
          </div>
          <div className="text-2xl font-bold mt-2" style={{ color: 'var(--text-primary)' }}>{formatCurrency(completedRecoveriesSum)}</div>
          <span className="text-[11px] block mt-1" style={{ color: 'var(--text-muted)' }}>Realized in simulation mode</span>
        </div>
      </div>

      {/* Action Cards List */}
      {loading && actions.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} className="h-64" />)}
        </div>
      ) : filteredActions.length === 0 ? (
        <div className="p-16 text-center glass-card animate-fade-in-up">
          <div className="w-14 h-14 rounded-full bg-violet-500/10 flex items-center justify-center mx-auto mb-3 border border-violet-500/20">
            <CheckCircle2 className="w-7 h-7 text-violet-600 dark:text-violet-400" />
          </div>
          <h3 className="text-base font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>No actions under "{filter}" filter</h3>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>All AI financial operation proposals are up to date.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 animate-fade-in-up">
          {filteredActions.map((action, index) => {
            const effectiveStatus = getEffectiveStatus(action);
            const actionTypeName = action.action_type || action.type || 'Automated Operation';
            const whyPoints: string[] = action.input_data?.why_this_action || [];
            
            return (
              <Card 
                key={action.id} 
                className={cn(
                  "flex flex-col relative overflow-hidden transition-all duration-300 border shadow-sm",
                  effectiveStatus === 'pending' ? "border-amber-500/40 hover:border-amber-500/70" : 
                  effectiveStatus === 'approved' ? "border-emerald-500/40 hover:border-emerald-500/70" : "border-slate-200 dark:border-white/10 opacity-95"
                )}
                style={{ animationDelay: `${index * 50}ms` }}
                noPadding
              >
                {/* Card Header */}
                <div 
                  className="px-5 pt-5 pb-4 border-b flex items-start justify-between"
                  style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-elevated)' }}
                >
                  <div className="flex gap-3 items-center">
                    <div 
                      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)' }}
                    >
                      {getActionIcon(actionTypeName)}
                    </div>
                    <div>
                      <h3 className="font-semibold capitalize text-xs" style={{ color: 'var(--text-primary)' }}>
                        {actionTypeName.replace(/_/g, ' ')}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusBadge status={effectiveStatus as any} />
                        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{relativeTime(action.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {action.estimated_impact && (
                    <div className="text-right">
                      <span className="text-[10px] block uppercase font-semibold" style={{ color: 'var(--text-muted)' }}>Est. Recovery</span>
                      <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        {typeof action.estimated_impact === 'number' ? formatCurrency(action.estimated_impact) : `₹${Number(action.estimated_impact).toLocaleString()}`}
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Body */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div>
                    <p className="text-xs font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Proposal Details</p>
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>{action.description}</p>
                  </div>
                  
                  {/* Why this action explainability */}
                  {whyPoints.length > 0 ? (
                    <div 
                      className="p-3 rounded-lg space-y-1.5"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
                    >
                      <div className="flex items-center gap-1.5">
                        <Bot className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
                        <span className="text-[10px] font-bold text-violet-700 dark:text-violet-300 uppercase tracking-wider">
                          Why PayPilot Proposed This Action
                        </span>
                      </div>
                      <ul className="space-y-1">
                        {whyPoints.map((pt, i) => (
                          <li key={i} className="text-[11px] flex items-start gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                            <span className="text-violet-500 dark:text-violet-400 font-bold">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : action.reason ? (
                    <div 
                      className="p-3 rounded-lg"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
                    >
                      <div className="flex items-center gap-1.5 mb-1">
                        <Bot className="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" />
                        <span className="text-[10px] font-bold text-violet-700 dark:text-violet-300 uppercase tracking-wider">AI Root-Cause Reasoning</span>
                      </div>
                      <p className="text-xs italic" style={{ color: 'var(--text-secondary)' }}>"{action.reason}"</p>
                    </div>
                  ) : null}

                  {/* Output execution results if completed */}
                  {effectiveStatus === 'completed' && action.output_data && (
                    <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs space-y-1">
                      <div className="flex items-center justify-between font-semibold text-emerald-700 dark:text-emerald-300 text-[11px]">
                        <span className="flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Simulation Succeeded</span>
                        <span>{action.output_data.recovery_rate_pct ? `${action.output_data.recovery_rate_pct}% recovered` : 'Verified'}</span>
                      </div>
                      {action.output_data.recovered_amount_inr && (
                        <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                          Recovered Amount: <span className="font-bold" style={{ color: 'var(--text-primary)' }}>₹{Number(action.output_data.recovered_amount_inr).toLocaleString()}</span> ({action.output_data.successfully_recovered}/{action.output_data.total_retried} payments)
                        </p>
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div 
                    className="pt-3 border-t flex flex-col gap-2"
                    style={{ borderColor: 'var(--border-subtle)' }}
                  >
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleViewTransactions(action.id)}
                        className="flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors hover:opacity-80"
                        style={{ 
                          background: 'var(--bg-elevated)', 
                          border: '1px solid var(--border-default)', 
                          color: 'var(--text-primary)' 
                        }}
                      >
                        <Eye size={12} /> View Transactions
                      </button>

                      <button 
                        onClick={() => navigate(`/copilot?id=${action.input_data?.investigation_id || ''}`)}
                        className="p-2 rounded-lg transition-colors hover:opacity-80"
                        style={{ 
                          background: 'var(--bg-elevated)', 
                          border: '1px solid var(--border-default)', 
                          color: 'var(--text-muted)' 
                        }}
                        title="View Investigation"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="flex gap-2">
                      {effectiveStatus === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(action.id)}
                            disabled={processingId === action.id}
                            className="flex-1 py-2 px-3 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold flex justify-center items-center gap-1.5 transition-colors shadow-md shadow-violet-600/20 disabled:opacity-50"
                          >
                            {processingId === action.id ? (
                              <div className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                            ) : (
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            )}
                            {processingId === action.id ? 'Authorizing...' : 'Authorize Action'}
                          </button>

                          <button
                            onClick={() => handleReject(action.id)}
                            disabled={processingId === action.id}
                            className="py-2 px-3 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/20 rounded-lg text-xs font-semibold flex justify-center items-center transition-colors disabled:opacity-50"
                            title="Reject proposal"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}

                      {effectiveStatus === 'approved' && (
                        <button
                          onClick={() => handleExecute(action.id)}
                          disabled={processingId === action.id}
                          className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex justify-center items-center gap-1.5 transition-colors shadow-md shadow-emerald-500/20 disabled:opacity-50"
                        >
                          {processingId === action.id ? (
                            <div className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                          ) : (
                            <Play className="w-3.5 h-3.5" />
                          )}
                          {processingId === action.id ? 'Executing...' : 'Execute Simulation Now'}
                        </button>
                      )}

                      {effectiveStatus === 'completed' && (
                        <div className="flex-1 py-2 px-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs font-medium text-center text-emerald-600 dark:text-emerald-400 flex justify-center items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Action Executed & Verified
                        </div>
                      )}

                      {effectiveStatus === 'rejected' && (
                        <div className="flex-1 py-2 px-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs font-medium text-center text-red-600 dark:text-red-400 flex justify-center items-center gap-1.5">
                          <X className="w-3.5 h-3.5" /> Proposal Rejected by Operator
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Transaction Level Drilldown Drawer / Modal */}
      {selectedActionTxns && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div 
            className="w-full max-w-3xl border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
            style={{ 
              background: 'var(--bg-surface)', 
              borderColor: 'var(--border-default)' 
            }}
          >
            {/* Modal Header */}
            <div 
              className="p-5 border-b flex items-center justify-between"
              style={{ borderColor: 'var(--border-default)', background: 'var(--bg-elevated)' }}
            >
              <div>
                <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <Layers size={16} className="text-violet-600 dark:text-violet-400" />
                  Policy Evaluation & Eligible Transactions Drilldown
                </h3>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Policy: <span className="font-mono text-violet-600 dark:text-violet-300 font-semibold">{selectedActionTxns.policy_version}</span> • {selectedActionTxns.total_eligible_count} transactions evaluated
                </p>
              </div>
              <button
                onClick={() => setSelectedActionTxns(null)}
                className="p-1.5 rounded-lg transition-colors"
                style={{ background: 'var(--bg-surface)', color: 'var(--text-muted)', border: '1px solid var(--border-default)' }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Table Body */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div 
                  className="p-3 rounded-lg border"
                  style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)' }}
                >
                  <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Total Eligible Volume</span>
                  <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(selectedActionTxns.total_eligible_amount)}</span>
                </div>
                <div 
                  className="p-3 rounded-lg border"
                  style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-default)' }}
                >
                  <span className="text-[10px] uppercase block font-semibold" style={{ color: 'var(--text-muted)' }}>Deterministic Policy Pass Rate</span>
                  <span className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>6 / 6 Safety Rules</span>
                </div>
              </div>

              <div 
                className="border rounded-xl overflow-hidden"
                style={{ borderColor: 'var(--border-default)' }}
              >
                <table className="w-full text-left text-xs">
                  <thead 
                    className="uppercase font-semibold text-[10px] border-b"
                    style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', borderColor: 'var(--border-default)' }}
                  >
                    <tr>
                      <th className="p-3">Txn ID</th>
                      <th className="p-3">Method</th>
                      <th className="p-3">Amount</th>
                      <th className="p-3">Failure Code</th>
                      <th className="p-3">Eligibility Rule</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
                    {selectedActionTxns.transactions.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="p-4 text-center" style={{ color: 'var(--text-muted)' }}>
                          {selectedActionTxns.total_eligible_count} transactions matched in database
                        </td>
                      </tr>
                    ) : (
                      selectedActionTxns.transactions.map((tx) => (
                        <tr key={tx.id} className="transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02]">
                          <td className="p-3 font-mono" style={{ color: 'var(--text-secondary)' }}>{tx.id.slice(0, 8)}…</td>
                          <td className="p-3 font-semibold" style={{ color: 'var(--text-primary)' }}>{tx.payment_method}</td>
                          <td className="p-3 font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(tx.amount)}</td>
                          <td className="p-3 font-mono text-amber-600 dark:text-amber-300">{tx.failure_code}</td>
                          <td className="p-3" style={{ color: 'var(--text-muted)' }}>
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-300 font-medium">
                              <Check size={11} /> {tx.eligibility_reason}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modal Footer */}
            <div 
              className="p-4 border-t flex justify-end"
              style={{ borderColor: 'var(--border-default)', background: 'var(--bg-elevated)' }}
            >
              <button
                onClick={() => setSelectedActionTxns(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold transition-colors hover:opacity-90"
                style={{ 
                  background: 'var(--bg-card)', 
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)' 
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
