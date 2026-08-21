import { getStatusColor } from '../../lib/utils';
import { cn } from '../../lib/utils';

interface StatusBadgeProps {
  status: string;
}

const statusLabels: Record<string, string> = {
  captured: 'Captured',
  failed: 'Failed',
  pending: 'Pending',
  refunded: 'Refunded',
  authorized: 'Authorized',
  processed: 'Processed',
  resolved: 'Resolved',
  open: 'Open',
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        getStatusColor(status)
      )}
    >
      <span className={cn('status-dot', status)} />
      {statusLabels[status] ?? status}
    </span>
  );
}
