import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, LayoutDashboard, CreditCard, BarChart3, TrendingDown, AlertTriangle, Bot, Zap, FileText } from 'lucide-react';
import { cn } from '../../lib/utils';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const commands = [
    { id: 'dashboard', name: 'Go to Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { id: 'transactions', name: 'View Transactions', icon: CreditCard, path: '/transactions' },
    { id: 'analytics', name: 'View Analytics', icon: BarChart3, path: '/analytics' },
    { id: 'cashflow', name: 'Cash Flow Forecast', icon: TrendingDown, path: '/cashflow' },
    { id: 'anomalies', name: 'Run Anomaly Scan', icon: AlertTriangle, path: '/anomalies' },
    { id: 'copilot', name: 'Ask AI Copilot', icon: Bot, path: '/copilot' },
    { id: 'actions', name: 'Review Actions', icon: Zap, path: '/actions' },
    { id: 'audit', name: 'Audit Log', icon: FileText, path: '/audit' },
  ];

  const filteredCommands = commands.filter((cmd) =>
    cmd.name.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % filteredCommands.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[activeIndex]) {
          handleSelect(filteredCommands[activeIndex].path);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activeIndex, filteredCommands, onClose]);

  const handleSelect = (path: string) => {
    navigate(path);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="command-overlay" onClick={onClose}>
      <div 
        className="command-palette" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center px-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <Search className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
          <input
            ref={inputRef}
            type="text"
            className="command-input border-none!"
            placeholder="Type a command or search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="max-h-80 overflow-y-auto py-2">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No results found for "{search}"
            </div>
          ) : (
            filteredCommands.map((cmd, index) => (
              <div
                key={cmd.id}
                className={cn('command-item', index === activeIndex && 'active')}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => handleSelect(cmd.path)}
              >
                <cmd.icon className="w-4 h-4" />
                <span>{cmd.name}</span>
                {index === activeIndex && <span className="kbd">Enter</span>}
              </div>
            ))
          )}
        </div>
        <div className="px-4 py-3 text-xs flex justify-between" style={{ borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.2)' }}>
          <span style={{ color: 'var(--text-muted)' }}>Use ↑↓ to navigate</span>
          <span style={{ color: 'var(--text-muted)' }}>ESC to close</span>
        </div>
      </div>
    </div>
  );
}
