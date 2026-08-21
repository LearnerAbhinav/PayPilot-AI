import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatCurrencyFull(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-IN').format(value);
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'captured':
      return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
    case 'failed':
      return 'bg-red-500/10 text-red-400 border border-red-500/20';
    case 'pending':
      return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
    case 'refunded':
      return 'bg-orange-500/10 text-orange-400 border border-orange-500/20';
    case 'authorized':
      return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    default:
      return 'bg-white/5 text-slate-400 border border-white/10';
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500/10 text-red-400 border border-red-500/20';
    case 'warning':
      return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
    case 'info':
      return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    default:
      return 'bg-white/5 text-slate-400 border border-white/10';
  }
}

export function truncateId(id: string, length = 8): string {
  return id.slice(0, length) + '...';
}

export function relativeTime(dateString: string): string {
  const now = new Date();
  const date = new Date(dateString);
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return formatDate(dateString);
}
