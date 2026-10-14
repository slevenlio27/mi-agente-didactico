import { useState } from 'react'

/** Muestra el enlace de un solo uso que el administrador debe enviar al docente. */
export default function ResetLinkDialog({ data, onClose }) {
  const [copiado, setCopiado] = useState(false)
  if (!data) return null
  const vence = new Date(data.expires_at.endsWith('Z') ? data.expires_at : data.expires_at + 'Z')
    .toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' })

  const copiar = async () => {
    try { await navigator.clipboard.writeText(data.link) }
    catch { document.getElementById('reset-link-input')?.select(); document.execCommand?.('copy') }
    setCopiado(true); setTimeout(() => setCopiado(false), 2500)
  }

  const asunto = encodeURIComponent('Enlace para restablecer tu contraseña')
  const cuerpo = encodeURIComponent(
    `Hola:\n\nPara elegir una contraseña nueva, abre este enlace:\n\n${data.link}\n\n` +
    `Sirve una sola vez y vence el ${vence}.\n\nSi no pediste cambiar tu contraseña, ignora este mensaje.`)

  return (
    <div className="modal-overlay open" role="dialog" aria-modal="true" aria-labelledby="reset-link-title"
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-head">
          <h3 id="reset-link-title">Enlace para restablecer la contraseña</h3>
          <button aria-label="Cerrar" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <p className="hint">Envíaselo a <strong>{data.email}</strong>. Sirve <strong>una sola vez</strong> y vence el <strong>{vence}</strong>. Generar otro enlace anula este.</p>
          <div className="reset-link-row">
            <input id="reset-link-input" readOnly value={data.link} onFocus={(e) => e.target.select()} aria-label="Enlace para restablecer la contraseña" />
            <button className="btn btn-primary btn-sm" onClick={copiar}>{copiado ? '¡Copiado!' : 'Copiar'}</button>
          </div>
          <a className="btn btn-ghost btn-sm reset-mail" href={`mailto:${data.email}?subject=${asunto}&body=${cuerpo}`}>Enviar por correo</a>
          <p className="reset-warning">Quien tenga este enlace puede cambiar la contraseña de esa cuenta: compártelo solo con el docente.</p>
        </div>
      </div>
    </div>
  )
}
