import { useState, useEffect } from 'react'

export default function AnimatedNumber({ value, format }) {
    const [displayValue, setDisplayValue] = useState(0)

    useEffect(() => {
        let start = 0
        const end = parseFloat(value) || 0
        if (start === end) {
            setDisplayValue(end)
            return
        }

        const duration = 1000
        const frameDuration = 1000 / 60
        const totalFrames = Math.round(duration / frameDuration)
        let frame = 0

        const timer = setInterval(() => {
            frame++
            const progress = frame / totalFrames
            // Easing function (easeOutQuad)
            const easeProgress = progress * (2 - progress)

            const current = start + (end - start) * easeProgress

            if (frame === totalFrames) {
                setDisplayValue(end)
                clearInterval(timer)
            } else {
                setDisplayValue(current)
            }
        }, frameDuration)

        return () => clearInterval(timer)
    }, [value])

    return <span>{format ? format(displayValue) : Math.round(displayValue)}</span>
}
