/**
 * Gráfico de barras simple en SVG puro — sin librerías externas, para no
 * sumar peso al bundle ni arriesgar problemas de compatibilidad con React 19.
 */
export default function BarChart({ data, labelKey, valueKey, height = 160 }) {
  const max = Math.max(1, ...data.map((d) => d[valueKey]))
  const barWidth = 100 / data.length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" style={{ width: '100%', height, overflow: 'visible' }}>
        {data.map((d, i) => {
          const barHeight = (d[valueKey] / max) * (height - 24)
          const x = i * barWidth
          return (
            <g key={i}>
              <rect
                x={x + barWidth * 0.15}
                y={height - 20 - barHeight}
                width={barWidth * 0.7}
                height={barHeight}
                rx={2}
                fill="var(--accent)"
                opacity={0.85}
              />
              <text
                x={x + barWidth * 0.5}
                y={height - 20 - barHeight - 4}
                textAnchor="middle"
                fontSize="4.2"
                fill="var(--fg)"
                fontFamily="var(--font-mono)"
              >
                {d[valueKey]}
              </text>
            </g>
          )
        })}
      </svg>
      <div style={{ display: 'flex' }}>
        {data.map((d, i) => (
          <div key={i} style={{ width: `${barWidth}%`, textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--muted)' }}>
            {d[labelKey]}
          </div>
        ))}
      </div>
    </div>
  )
}
