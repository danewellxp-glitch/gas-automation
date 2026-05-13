import { useEffect, useRef, useState } from 'react'

export function useCountUp(target, opts = {}) {
  const { duration = 1000, startFrom = 0 } = opts
  const numericTarget = Number(target) || 0
  const [val, setVal] = useState(startFrom)
  const prev = useRef(startFrom)
  const rafRef = useRef(null)

  useEffect(() => {
    const from = prev.current
    const to = numericTarget
    if (from === to) return

    if (duration <= 0) {
      setVal(to)
      prev.current = to
      return
    }

    const start = performance.now()
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      const current = from + (to - from) * eased
      setVal(current)
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step)
      } else {
        prev.current = to
      }
    }
    rafRef.current = requestAnimationFrame(step)
    return () => rafRef.current && cancelAnimationFrame(rafRef.current)
  }, [numericTarget, duration])

  return val
}
