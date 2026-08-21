import { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CreditCard,
  BarChart3,
  TrendingDown,
  AlertTriangle,
  Bot,
  Zap,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Search
} from 'lucide-react';
import { cn } from '../../lib/utils';
import CommandPalette from './CommandPalette';
import NotificationCenter from './NotificationCenter';
import type { Notification } from './NotificationCenter';

import { getAnomalies } from '../../api/anomalies';
import { getActions } from '../../api/actions';
import { getInvestigations } from '../../api/investigations';

interface BadgesState {
  anomalies?: string;
  actions?: string;
  investigations?: string;
}

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase();
}

interface SidebarContentProps {
  onNavClick?: () => void;
  userName: string;
  userEmail: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
  badges: BadgesState;
}

function getNavItems(badges: BadgesState) {
  return [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/transactions', label: 'Transactions', icon: CreditCard },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/cashflow', label: 'Cash Flow', icon: TrendingDown },
    { to: '/anomalies', label: 'Anomalies', icon: AlertTriangle, badge: badges.anomalies },
    { to: '/copilot', label: 'AI Copilot', icon: Bot, badge: badges.investigations },
    { to: '/actions', label: 'Actions', icon: Zap, badge: badges.actions },
    { to: '/audit', label: 'Audit Log', icon: FileText },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];
}

function SidebarContent({ onNavClick, userName, userEmail, collapsed, onToggleCollapse, badges }: SidebarContentProps) {
  const navItems = getNavItems(badges);

  return (
    <div className="flex flex-col h-full relative">
      {/* Toggle button - hidden on mobile */}
      <button 
        onClick={onToggleCollapse}
        className="hidden lg:flex absolute -right-3 top-6 w-6 h-6 rounded-full bg-[var(--bg-elevated)] border border-[var(--border-default)] items-center justify-center text-[var(--text-muted)] hover:text-white transition-colors z-10"
      >
        {collapsed ? <PanelLeftOpen className="w-3.5 h-3.5" /> : <PanelLeftClose className="w-3.5 h-3.5" />}
      </button>

      {/* Logo */}
      <div className={cn("px-5 py-5 transition-all duration-300", collapsed ? "px-2 text-center" : "")} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div className={cn("flex items-center gap-3", collapsed ? "justify-center" : "")}>
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 animate-pulse-glow"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
          >
            <Zap className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <div className="animate-fade-in">
              <span className="text-sm font-bold tracking-tight gradient-text">PayPilot AI</span>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="live-dot">
                  <span className="status-dot captured" />
                </span>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Live</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto overflow-x-hidden">
        {navItems.map((item, idx) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavClick}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group relative',
                isActive
                  ? 'nav-active'
                  : 'nav-inactive text-slate-400',
                collapsed ? 'justify-center px-0' : ''
              )
            }
            style={{ animationDelay: `${idx * 30}ms` }}
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn('w-4 h-4 flex-shrink-0 transition-colors', isActive ? 'text-violet-400' : 'text-slate-500 group-hover:text-slate-300')} />
                {!collapsed && (
                  <>
                    <span className="animate-fade-in truncate">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-violet-500/20 text-violet-300 text-[10px] font-bold border border-violet-500/30">
                        {item.badge}
                      </span>
                    )}
                    {isActive && !item.badge && <ChevronRight className="w-3 h-3 ml-auto text-violet-400 opacity-60" />}
                  </>
                )}
                {collapsed && item.badge && (
                  <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-violet-500" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className={cn("p-3 transition-all", collapsed ? "px-1" : "")} style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <div
          className={cn("flex items-center gap-3 py-2.5 rounded-lg transition-colors cursor-default", collapsed ? "justify-center px-0" : "px-3")}
          style={{ background: 'rgba(255,255,255,0.03)' }}
        >
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-white text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
            title={collapsed ? userName : undefined}
          >
            {getInitials(userName)}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0 animate-fade-in">
              <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{userName}</p>
              <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{userEmail}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [time, setTime] = useState(new Date());
  
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [badges, setBadges] = useState<BadgesState>({});
  
  const [userName, setUserName] = useState(localStorage.getItem('paypilot_user_name') || 'User');
  const [userEmail, setUserEmail] = useState(localStorage.getItem('paypilot_user_email') || 'user@paypilot.ai');

  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const loadBadges = async () => {
      try {
        const [anomRes, actRes, invRes] = await Promise.all([
          getAnomalies().catch(() => ({ unresolved_count: 0, items: [] })),
          getActions('pending').catch(() => []),
          getInvestigations().catch(() => []),
        ]);
        const anomCount = (anomRes as any)?.unresolved_count || (anomRes as any)?.items?.length || 0;
        const actCount = (actRes as any)?.length || 0;
        const activeInvs = (invRes as any)?.filter((i: any) => i.status === 'ANALYZING' || i.status === 'ACTION_PROPOSED')?.length || 0;
        setBadges({
          anomalies: anomCount > 0 ? String(anomCount) : undefined,
          actions: actCount > 0 ? String(actCount) : undefined,
          investigations: activeInvs > 0 ? String(activeInvs) : undefined,
        });
      } catch { /* silent */ }
    };
    loadBadges();
    const interval = setInterval(loadBadges, 15000);
    return () => clearInterval(interval);
  }, []);

  // Mock notifications
  const [notifications, setNotifications] = useState<Notification[]>([
    { id: '1', type: 'alert', title: 'Payment Anomaly', message: 'Unusual spike in failed transactions detected on HDFC Netbanking.', time: new Date(Date.now() - 1000 * 60 * 5).toISOString(), read: false },
    { id: '2', type: 'action', title: 'Action Required', message: 'AI Copilot generated a recovery plan for 12 failed payments.', time: new Date(Date.now() - 1000 * 60 * 45).toISOString(), read: false },
    { id: '3', type: 'insight', title: 'Cash Flow Forecast', message: 'Your projected balance for next week is healthy.', time: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), read: true },
    { id: '4', type: 'success', title: 'Recovery Successful', message: 'Successfully recovered ₹14,500 from failed payments yesterday.', time: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), read: true },
  ]);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    
    // Command palette shortcut
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette((prev) => !prev);
      }
    };
    
    // Listen for user updates
    const handleUserUpdate = () => {
      setUserName(localStorage.getItem('paypilot_user_name') || 'User');
      setUserEmail(localStorage.getItem('paypilot_user_email') || 'user@paypilot.ai');
    };

    // Listen for dispatched test/real notifications
    const handleNewNotification = (e: any) => {
      if (e.detail) {
        setNotifications((prev) => [e.detail, ...prev]);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('user-updated', handleUserUpdate);
    window.addEventListener('new-notification', handleNewNotification);
    
    return () => {
      clearInterval(t);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('user-updated', handleUserUpdate);
      window.removeEventListener('new-notification', handleNewNotification);
    };
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const navItems = getNavItems(badges);
  const currentPage = navItems.find((item) => location.pathname.startsWith(item.to))?.label || 'PayPilot AI';
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="min-h-screen mesh-bg">
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:flex lg:flex-col sidebar-bg transition-all duration-300",
          sidebarCollapsed ? "w-[4.5rem]" : "w-56"
        )}
      >
        <SidebarContent 
          userName={userName} 
          userEmail={userEmail} 
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          badges={badges}
        />
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div
            className="fixed inset-0"
            style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
            onClick={() => setSidebarOpen(false)}
          />
          <aside
            className="fixed inset-y-0 left-0 z-50 w-56 flex flex-col sidebar-bg animate-slide-in-left"
          >
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
                  <Zap className="w-3.5 h-3.5 text-white" />
                </div>
                <span className="text-sm font-bold gradient-text">PayPilot AI</span>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg transition-colors hover:bg-white/5"
                style={{ color: 'var(--text-muted)' }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <SidebarContent
              onNavClick={() => setSidebarOpen(false)}
              userName={userName}
              userEmail={userEmail}
              collapsed={false}
              onToggleCollapse={() => {}}
              badges={badges}
            />
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className={cn("transition-all duration-300", sidebarCollapsed ? "lg:ml-[4.5rem]" : "lg:ml-56")}>
        {/* Top header */}
        <header
          className="sticky top-0 z-40 flex items-center justify-between px-5 h-14"
          style={{
            background: 'rgba(7, 7, 13, 0.85)',
            backdropFilter: 'blur(20px)',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-lg transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              <Menu className="w-5 h-5" />
            </button>
            
            <div className="hidden lg:flex items-center gap-2">
              <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {currentPage}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-3">
            {/* Command Palette trigger */}
            <button
              onClick={() => setShowCommandPalette(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors hover:bg-white/5"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)' }}
            >
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400">Search</span>
              <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-400 font-mono">Ctrl+K</kbd>
            </button>

            {/* Live clock */}
            <span
              className="hidden sm:block text-xs font-mono tabular-nums px-2"
              style={{ color: 'var(--text-muted)' }}
            >
              {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>

            {/* Notification bell */}
            <button
              onClick={() => setShowNotifications(true)}
              className="relative p-2 rounded-lg transition-colors hover:bg-white/5"
              style={{ color: 'var(--text-muted)' }}
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span
                  className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full border border-[var(--bg-base)]"
                  style={{ background: '#ef4444' }}
                />
              )}
            </button>

            {/* User + logout */}
            <div className="flex items-center gap-2 ml-1" style={{ borderLeft: '1px solid var(--border-subtle)', paddingLeft: '12px' }}>
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
                title={userName}
              >
                {getInitials(userName)}
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors hover:bg-white/5 text-slate-400 hover:text-slate-200"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>

        <main className="p-5 lg:p-6 overflow-x-hidden min-h-[calc(100vh-3.5rem)] relative">
          <div className="page-enter" key={location.pathname}>
            {children}
          </div>
        </main>
      </div>

      <CommandPalette 
        isOpen={showCommandPalette} 
        onClose={() => setShowCommandPalette(false)} 
      />
      
      <NotificationCenter 
        isOpen={showNotifications} 
        onClose={() => setShowNotifications(false)}
        notifications={notifications}
        onMarkAsRead={(id) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))}
        onClearAll={() => setNotifications([])}
      />
    </div>
  );
}
