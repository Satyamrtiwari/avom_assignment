import React from 'react'

interface CircularGaugeProps {
  score: number // 0 to 100
  size?: number
  strokeWidth?: number
  label?: string
}

export const CircularGauge: React.FC<CircularGaugeProps> = ({
  score,
  size = 120,
  strokeWidth = 9,
  label = "OVERALL MATCH"
}) => {
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius
  const clampedScore = Math.min(100, Math.max(0, score))
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference

  // Palette 2 Dynamic Tone
  const getScoreColor = (val: number) => {
    if (val >= 80) return "#4F46E5" // Royal Indigo (High Match)
    if (val >= 60) return "#6366F1" // Indigo-500 (Moderate Match)
    if (val >= 40) return "#0284C7" // Sky-600
    return "#94A3B8" // Slate-400 (Low Match)
  }

  const color = getScoreColor(clampedScore)

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90"
        >
          {/* Background track circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset 0.8s ease-out, stroke 0.4s ease"
            }}
          />
        </svg>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-extrabold text-slate-900 tracking-tight leading-none">
            {clampedScore.toFixed(1)}%
          </span>
          <span className="text-[9px] font-bold text-slate-400 tracking-wider uppercase mt-1">
            {label}
          </span>
        </div>
      </div>
    </div>
  )
}
