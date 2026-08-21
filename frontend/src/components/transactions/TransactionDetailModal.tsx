import { X, ExternalLink, RefreshCw, AlertTriangle, MessageSquare } from 'lucide-react';
import { cn, formatCurrency, formatDateTime } from '../../lib/utils';
import StatusBadge from '../common/StatusBadge';

interface TransactionDetailModalProps {
  transaction: Record<string, unknown> | null;
  isOpen: boolean;
  onClose: () => void;
  onAskCopilot: (txId: string) => void;
}

export default function TransactionDetailModal({
  transaction,
  isOpen,
  onClose,
  onAskCopilot,
}: TransactionDetailModalProps) {
  if (!isOpen || !transaction) return null;

  const isFailed = transaction.status === 'failed';
  const txId = String(transaction.id);

  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="slide-over">
        <div className="sticky top-0 z-10 flex items-center justify-between p-5" style={{ background: 'rgba(14,14,26,0.9)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Transaction Details</h2>
            <StatusBadge status={String(transaction.status)} />
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md transition-colors hover:bg-white/5"
            style={{ color: 'var(--text-muted)' }}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-6">
          {/* Header Info */}
          <div className="text-center pb-6" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <p className="text-sm uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>Amount</p>
            <p className="text-4xl font-bold tracking-tight mb-2" style={{ color: 'var(--text-primary)' }}>
              {formatCurrency(Number(transaction.amount))}
            </p>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {String(transaction.description || 'Payment')}
            </p>
          </div>

          {/* Failure Banner */}
          {isFailed && (
            <div className="flex items-start gap-3 p-4 rounded-xl" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
              <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-red-400 mb-1">Payment Failed</h3>
                <p className="text-sm text-red-300/80 mb-2">
                  {String(transaction.failure_reason || 'Unknown error occurred during processing.')}
                </p>
                <code className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                  {String(transaction.failure_code || 'ERROR_UNKNOWN')}
                </code>
              </div>
            </div>
          )}

          {/* Details Grid */}
          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Payment Details</h3>
            <div className="glass-card-static rounded-xl overflow-hidden">
              <div className="grid grid-cols-2 gap-px bg-white/5">
                {[
                  { label: 'Transaction ID', value: txId.slice(0, 12) + '...', mono: true },
                  { label: 'Date & Time', value: formatDateTime(String(transaction.created_at)) },
                  { label: 'Payment Method', value: String(transaction.payment_method || '—').toUpperCase() },
                  { label: 'Gateway', value: String(transaction.payment_gateway || 'Razorpay') },
                  { label: 'Customer', value: 'guest@example.com' },
                  { label: 'Currency', value: String(transaction.currency || 'INR') },
                ].map((item, i) => (
                  <div key={i} className="p-3" style={{ background: 'var(--bg-surface)' }}>
                    <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{item.label}</p>
                    <p className={cn("text-sm", item.mono && "font-mono text-xs")} style={{ color: 'var(--text-primary)' }}>
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Actions</h3>
            <div className="flex flex-col gap-2">
              <button 
                onClick={() => { onClose(); onAskCopilot(txId); }}
                className="w-full flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-white/5 group"
                style={{ border: '1px solid var(--border-default)' }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center bg-violet-500/10 text-violet-400 group-hover:bg-violet-500/20">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Ask Copilot</p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Analyze this transaction with AI</p>
                  </div>
                </div>
                <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-violet-400" />
              </button>
              
              {isFailed && (
                <button className="w-full flex items-center justify-between p-3 rounded-lg transition-colors hover:bg-white/5 group" style={{ border: '1px solid var(--border-default)' }}>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20">
                      <RefreshCw className="w-4 h-4" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Retry Payment</p>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Send a payment link to customer</p>
                    </div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-slate-500 group-hover:text-emerald-400" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
