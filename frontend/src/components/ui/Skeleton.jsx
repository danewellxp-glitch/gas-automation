export function Skeleton({ className = '', as: Tag = 'div', ...rest }) {
  return (
    <Tag
      className={`bg-slate-200/70 rounded animate-pulse motion-reduce:animate-none ${className}`}
      aria-hidden="true"
      {...rest}
    />
  )
}

export function SkeletonOverlay({ active, label = 'Atualizando...', children }) {
  return (
    <div className="relative">
      <div className={active ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
        {children}
      </div>
      {active && (
        <div
          role="status"
          aria-live="polite"
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/95 border border-slate-200 shadow-sm text-xs font-medium text-slate-700">
            <span className="w-3 h-3 rounded-full border-2 border-slate-300 border-t-primary-500 animate-spin motion-reduce:animate-none" />
            {label}
          </span>
        </div>
      )}
    </div>
  )
}

export function VasilhameCardSkeleton() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <Skeleton className="h-5 w-12 mb-2" />
      <Skeleton className="h-3 w-24 mb-4" />
      <div className="space-y-2">
        {[0, 1, 2].map(i => (
          <div key={i} className="flex justify-between items-center">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-4 w-8" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function TableRowSkeleton({ columns = 5 }) {
  return (
    <tr className="border-b border-slate-100">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-3 px-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

export default Skeleton
