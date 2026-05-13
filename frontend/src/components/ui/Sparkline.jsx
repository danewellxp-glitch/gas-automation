import { useMemo } from 'react'

export default function Sparkline({
  data = [],
  color = '#059669',
  width = 100,
  height = 24,
  strokeWidth = 1.5,
  animate = true,
}) {
  const path = useMemo(() => {
    if (!data.length) return ''
    const max = Math.max(...data)
    const min = Math.min(...data)
    const range = max - min || 1
    const pad = 2
    const stepX = (width - pad * 2) / (data.length - 1 || 1)
    return data
      .map((v, i) => {
        const x = pad + i * stepX
        const y = pad + (height - pad * 2) * (1 - (v - min) / range)
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
      })
      .join(' ')
  }, [data, width, height])

  if (!data.length) return null

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={
          animate
            ? {
                strokeDasharray: 300,
                strokeDashoffset: 300,
                animation: 'draw-line 1200ms ease-out forwards 200ms',
              }
            : undefined
        }
      />
    </svg>
  )
}
