export default function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div className="relative w-10 h-10">
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: '2px solid rgba(255,255,255,0.06)',
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: '2px solid transparent',
            borderTopColor: '#7c3aed',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <div
          className="absolute inset-1 rounded-full"
          style={{
            border: '2px solid transparent',
            borderTopColor: 'rgba(124, 58, 237, 0.3)',
            animation: 'spin 1.2s linear infinite reverse',
          }}
        />
      </div>
      <p className="text-xs font-medium animate-pulse" style={{ color: 'var(--text-muted)' }}>
        Loading data...
      </p>
    </div>
  );
}
