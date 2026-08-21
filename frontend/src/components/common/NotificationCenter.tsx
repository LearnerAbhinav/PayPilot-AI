import { X, AlertTriangle, Zap, Info, CheckCircle2 } from 'lucide-react';
import { cn, relativeTime } from '../../lib/utils';

export interface Notification {
  id: string;
  type: 'alert' | 'action' | 'insight' | 'success';
  title: string;
  message: string;
  time: string;
  read: boolean;
}

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onClearAll: () => void;
}

export default function NotificationCenter({
  isOpen,
  onClose,
  notifications,
  onMarkAsRead,
  onClearAll,
}: NotificationCenterProps) {
  if (!isOpen) return null;

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: string) => {
    switch (type) {
      case 'alert':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'action':
        return <Zap className="w-4 h-4 text-amber-400" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'insight':
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getBg = (type: string) => {
    switch (type) {
      case 'alert':
        return 'bg-red-500/10';
      case 'action':
        return 'bg-amber-500/10';
      case 'success':
        return 'bg-emerald-500/10';
      case 'insight':
      default:
        return 'bg-blue-500/10';
    }
  };

  return (
    <>
      <div className="modal-backdrop" onClick={onClose} />
      <div className="notification-panel">
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Notifications</h2>
            {unreadCount > 0 && (
              <span className="nav-badge bg-violet-500 text-white">
                {unreadCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {notifications.length > 0 && (
              <button
                onClick={onClearAll}
                className="text-xs font-medium transition-colors hover:text-white"
                style={{ color: 'var(--text-muted)' }}
              >
                Clear all
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-md transition-colors hover:bg-white/5"
              style={{ color: 'var(--text-muted)' }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-6 text-center">
              <div className="w-12 h-12 rounded-full flex items-center justify-center mb-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <CheckCircle2 className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
              </div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>All caught up!</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>You have no new notifications.</p>
            </div>
          ) : (
            <div className="flex flex-col">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={cn('notification-item flex gap-3', !notif.read && 'unread')}
                  onClick={() => onMarkAsRead(notif.id)}
                >
                  <div className={cn('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1', getBg(notif.type))}>
                    {getIcon(notif.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <p className={cn('text-sm font-medium', notif.read ? 'text-slate-300' : 'text-white')}>
                        {notif.title}
                      </p>
                      <span className="text-[10px] flex-shrink-0 whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
                        {relativeTime(notif.time)}
                      </span>
                    </div>
                    <p className="text-xs line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                      {notif.message}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
