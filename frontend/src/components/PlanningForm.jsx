import { useState } from 'react'

const TIPOS = { programa: 'Programa o sílabo', rubrica: 'Rúbrica', lectura: 'Lectura o material', examen: 'Examen o evaluación', plan: 'Plan de clase', otro: 'Documento' }

// Valor inicial de cada campo: la sugerencia de la IA (tomada del perfil o del documento)
function inicial(q) {
  const s = q.sugerencia || ''
  if (q.tipo === 'multiple') return []
  if (q.tipo === 'opcion') return q.opciones.includes(s) ? s : (q.requerida ? q.opciones[0] : '')
  if (q.tipo === 'numero') return /^\d+(\.\d+)?$/.test(s) ? s : ''
  return s
}

/** Análisis de un archivo + formulario para generar el plan de clase o la secuencia didáctica. */
export default function PlanningForm({ form, onSubmit, disabled }) {
  const [valores, setValores] = useState(() => Object.fromEntries(form.preguntas.map((q) => [q.id, inicial(q)])))
  const set = (id, v) => setValores((x) => ({ ...x, [id]: v }))
  const toggle = (id, op) => setValores((x) => ({ ...x, [id]: x[id].includes(op) ? x[id].filter((o) => o !== op) : [...x[id], op] }))

  const enviar = (e) => {
    e.preventDefault()
    const answers = {}
    form.preguntas.forEach((q) => {
      const v = valores[q.id]
      if (v === '' || (Array.isArray(v) && v.length === 0)) return
      answers[q.id] = q.tipo === 'numero' ? Number(v) : v
    })
    onSubmit(form.id, answers)
  }

  return (
    <div className="plan-card">
      <div className="plan-head">
        <span className="plan-badge">{TIPOS[form.tipo_documento] || 'Documento'}</span>
        <strong>{form.titulo || form.file_name}</strong>
      </div>
      <p className="plan-summary">{form.resumen}</p>
      {form.hallazgos.length > 0 && (
        <details className="plan-details" open>
          <summary>Lo que encontré</summary>
          <ul>{form.hallazgos.map((h, i) => <li key={i}><strong>{h.etiqueta}:</strong> {h.detalle}</li>)}</ul>
        </details>
      )}
      {form.faltantes.length > 0 && (
        <div className="plan-missing">
          <strong>Falta para planificar:</strong>
          <ul>{form.faltantes.map((f, i) => <li key={i}>{f}</li>)}</ul>
        </div>
      )}

      {form.enviado ? (
        <div className="plan-sent">
          <strong>✓ Formulario enviado</strong>
          <ul>
            {form.preguntas.filter((q) => form.respuestas && q.id in form.respuestas).map((q) => (
              <li key={q.id}>{q.pregunta} <em>{[].concat(form.respuestas[q.id]).join(', ')}</em></li>
            ))}
          </ul>
        </div>
      ) : (
        <form className="plan-form" onSubmit={enviar}>
          <p className="plan-form-title">Completa estos datos para generar tu planificación</p>
          {form.preguntas.map((q) => (
            <fieldset key={q.id} className="plan-field">
              <legend>{q.pregunta}{q.requerida && <span aria-hidden="true"> *</span>}</legend>
              {q.tipo === 'opcion' && (
                <div className="plan-options" role="radiogroup">
                  {q.opciones.map((op) => (
                    <label key={op} className={`plan-chip ${valores[q.id] === op ? 'on' : ''}`}>
                      <input type="radio" name={`${form.id}-${q.id}`} value={op} checked={valores[q.id] === op}
                        onChange={() => set(q.id, op)} required={q.requerida} />{op}
                    </label>
                  ))}
                </div>
              )}
              {q.tipo === 'multiple' && (
                <div className="plan-options">
                  {q.opciones.map((op) => (
                    <label key={op} className={`plan-chip ${valores[q.id].includes(op) ? 'on' : ''}`}>
                      <input type="checkbox" checked={valores[q.id].includes(op)} onChange={() => toggle(q.id, op)} />{op}
                    </label>
                  ))}
                </div>
              )}
              {q.tipo === 'numero' && (
                <input type="number" min="0" max="1000" inputMode="numeric" value={valores[q.id]}
                  onChange={(e) => set(q.id, e.target.value)} aria-label={q.pregunta} />
              )}
              {q.tipo === 'texto' && (
                <textarea rows={2} maxLength={500} value={valores[q.id]} onChange={(e) => set(q.id, e.target.value)} aria-label={q.pregunta} />
              )}
            </fieldset>
          ))}
          <button type="submit" className="btn btn-primary plan-submit" disabled={disabled}>
            {disabled ? 'Generando…' : 'Generar planificación'}
          </button>
        </form>
      )}
    </div>
  )
}
