import { useEffect, useState } from 'react';
import { getTransactions } from '../api/transactions';
import type { Transaction, TransactionListResponse, TransactionFilters } from '../types';
import Card from '../components/common/Card';
import StatusBadge from '../components/common/StatusBadge';
import { formatCurrency, formatDateTime } from '../lib/utils';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import TransactionDetailModal from '../components/transactions/TransactionDetailModal';
import { Search, Download, Filter, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function TransactionsPage() {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<TransactionFilters>({ page: 1, page_size: 10 });
  const [searchQuery, setSearchQuery] = useState('');
  
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTransactions = async () => {
      setLoading(true);
      try {
        const response = await getTransactions(filters);
        setData(response);
      } catch (error) {
        console.error('Failed to load transactions:', error);
      } finally {
        setLoading(false);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      fetchTransactions();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [filters]);

  const handleFilterChange = (key: keyof TransactionFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    // In a real app, we'd pass this to the API. For this demo, we'll just update local state
    // and rely on the backend if it supports a 'search' param, or filter locally if not.
  };

  const exportCSV = () => {
    if (!data) return;
    const headers = ['ID', 'Date', 'Amount', 'Status', 'Method', 'Customer'];
    const rows = data.items.map(tx => [
      tx.id,
      new Date(tx.created_at).toISOString(),
      tx.amount,
      tx.status,
      tx.payment_method,
      tx.customer_email
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(e => e.join(','))].join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `transactions_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Transactions</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>Manage and view all your payments</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search ID, email..." 
              value={searchQuery}
              onChange={handleSearch}
              className="dark-input pl-9 w-48 sm:w-64"
            />
          </div>
          
          <button 
            onClick={exportCSV}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-lg text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </div>

      <Card noPadding className="animate-fade-in-up delay-50">
        <div className="p-4 border-b border-white/10 flex flex-wrap gap-4 items-center bg-white/5">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">Filters:</span>
          </div>
          
          <select
            className="dark-input text-sm py-1.5 w-auto"
            value={filters.status || ''}
            onChange={(e) => handleFilterChange('status', e.target.value || undefined)}
          >
            <option value="">All Statuses</option>
            <option value="captured">Captured</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
            <option value="refunded">Refunded</option>
          </select>

          <select
            className="dark-input text-sm py-1.5 w-auto"
            value={filters.payment_method || ''}
            onChange={(e) => handleFilterChange('payment_method', e.target.value || undefined)}
          >
            <option value="">All Methods</option>
            <option value="upi">UPI</option>
            <option value="card">Card</option>
            <option value="netbanking">Netbanking</option>
          </select>
          
          <div className="flex items-center gap-2 ml-auto">
            <Calendar className="w-4 h-4 text-slate-400" />
            <select className="dark-input text-sm py-1.5 w-auto">
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="all">All Time</option>
            </select>
          </div>
        </div>

        {loading ? (
          <TableSkeleton rows={8} />
        ) : !data || data.items.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
              <Search className="w-6 h-6 text-slate-500" />
            </div>
            <p className="text-slate-300 font-medium">No transactions found</p>
            <p className="text-slate-500 text-sm mt-1">Try adjusting your filters or search query.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full dark-table">
                <thead>
                  <tr>
                    <th>Transaction ID</th>
                    <th>Date & Time</th>
                    <th>Customer</th>
                    <th>Method</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items
                    .filter(tx => 
                      !searchQuery || 
                      tx.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
                      (tx.customer_email || '').toLowerCase().includes(searchQuery.toLowerCase())
                    )
                    .map((tx) => (
                    <tr key={tx.id} onClick={() => setSelectedTx(tx)} className="group">
                      <td className="font-mono text-xs text-slate-400 group-hover:text-violet-400 transition-colors">
                        {tx.id.slice(0, 12)}...
                      </td>
                      <td>{formatDateTime(tx.created_at)}</td>
                      <td>
                        <div className="flex flex-col">
                          <span className="font-medium">{tx.customer_name}</span>
                          <span className="text-xs text-slate-500">{tx.customer_email}</span>
                        </div>
                      </td>
                      <td className="uppercase text-xs font-semibold text-slate-400">{tx.payment_method}</td>
                      <td className="font-bold">{formatCurrency(tx.amount)}</td>
                      <td>
                        <StatusBadge status={tx.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-white/10 flex items-center justify-between">
              <p className="text-xs text-slate-500">
                Showing page {data.page} of {data.total_pages} ({data.total} total)
              </p>
              <div className="flex gap-2">
                <button
                  className="p-1.5 rounded bg-white/5 hover:bg-white/10 disabled:opacity-50 transition-colors"
                  disabled={data.page === 1}
                  onClick={() => handleFilterChange('page', data.page - 1)}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  className="p-1.5 rounded bg-white/5 hover:bg-white/10 disabled:opacity-50 transition-colors"
                  disabled={data.page === data.total_pages}
                  onClick={() => handleFilterChange('page', data.page + 1)}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </Card>
      
      <TransactionDetailModal 
        isOpen={!!selectedTx} 
        transaction={selectedTx as any} 
        onClose={() => setSelectedTx(null)} 
        onAskCopilot={(id) => navigate(`/copilot?tx=${id}`)}
      />
    </div>
  );
}
