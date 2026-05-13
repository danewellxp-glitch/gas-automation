export default function SkeletonRow({ cols = 6 }) {
  return (
    <tr className="border-b border-gray-100">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-3">
          <div
            className="h-4 rounded bg-gray-100 animate-pulse"
            style={{ width: `${60 + (i * 7) % 30}%` }}
          />
        </td>
      ))}
    </tr>
  )
}
