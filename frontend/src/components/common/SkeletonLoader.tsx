import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton", className)} />
  );
}

export function SkeletonText({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton skeleton-text", className)} />
  );
}

export function SkeletonTitle({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton skeleton-title", className)} />
  );
}

export function SkeletonAvatar({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton skeleton-avatar", className)} />
  );
}

export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton skeleton-card", className)} />
  );
}

export function SkeletonChart({ className }: SkeletonProps) {
  return (
    <div className={cn("skeleton skeleton-chart", className)} />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full space-y-4 py-4">
      <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.1)] pb-4 px-4">
        <SkeletonTitle className="w-1/4 h-4" />
        <SkeletonTitle className="w-1/4 h-4" />
        <SkeletonTitle className="w-1/4 h-4" />
        <SkeletonTitle className="w-1/4 h-4" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center justify-between px-4">
          <SkeletonText className="w-1/4" />
          <SkeletonText className="w-1/4" />
          <SkeletonText className="w-1/4" />
          <SkeletonText className="w-1/4" />
        </div>
      ))}
    </div>
  );
}
