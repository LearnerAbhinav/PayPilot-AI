import { cn } from '../../lib/utils';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  action?: React.ReactNode;
  noPadding?: boolean;
  style?: React.CSSProperties;
}

export default function Card({ children, title, subtitle, className, action, noPadding, style }: CardProps) {
  return (
    <div className={cn('glass-card', noPadding ? '' : '', className)} style={style}>
      {(title || action) && (
        <div className={cn('flex items-center justify-between', noPadding ? 'px-5 pt-5 pb-4' : 'px-5 pt-5 pb-4')}>
          <div>
            {title && (
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={cn(noPadding ? '' : (!title && !action) ? 'p-5' : 'px-5 pb-5')}>
        {children}
      </div>
    </div>
  );
}
