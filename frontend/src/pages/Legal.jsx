import { useEffect } from 'react'

export default function Legal() {
  useEffect(() => {
    if (window.location.hash) {
      const el = document.querySelector(window.location.hash)
      if (el) setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }, [])

  return (
    <section className="page-section legal-page">
      <div className="wrap" style={{ maxWidth: 780 }}>
        <div className="eyebrow">Información legal</div>
        <h1 style={{ fontSize: 'clamp(1.8rem,3vw,2.4rem)' }}>Privacidad, términos y cookies</h1>
        <p style={{ color: 'var(--muted)', marginTop: 14 }}>
          Última actualización: {new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}
        </p>

        <nav className="legal-toc">
          <a href="#privacidad">Política de privacidad</a>
          <a href="#terminos">Términos y condiciones</a>
          <a href="#cookies">Política de cookies</a>
        </nav>

        <article id="privacidad" className="legal-section">
          <h2>Política de privacidad</h2>
          <p>Esta plataforma es una herramienta de apoyo docente. Esta página explica, en términos concretos, qué datos guarda y para qué.</p>

          <h3>Qué información recopilamos</h3>
          <ul>
            <li><strong>Datos de cuenta:</strong> correo electrónico, nombre (si lo indicas), y una versión cifrada (hash) de tu contraseña — nunca la contraseña en texto plano. Si te registras con Google, guardamos el identificador que Google nos entrega, no tu contraseña de Google.</li>
            <li><strong>Conversaciones con el asistente:</strong> el contenido de tus mensajes y las respuestas de la IA, asociadas a tu cuenta, para que puedas retomarlas después.</li>
            <li><strong>Archivos que subas:</strong> se guardan en el servidor, asociados a tu cuenta.</li>
            <li><strong>Perfil docente (opcional):</strong> materia, nivel de tus estudiantes, duración de tus clases y estilo preferido, para adaptar las respuestas del asistente.</li>
            <li><strong>Agenda:</strong> los eventos que registres en tu horario semanal.</li>
            <li><strong>Clave de API propia (opcional):</strong> si pegas tu propia clave de OpenAI, Gemini o Claude en Preferencias, se guarda cifrada en el servidor para usarla en tus conversaciones. Nunca se muestra de nuevo en pantalla una vez guardada. Las consultas hechas con tu clave usan la cuota y la facturación de tu propia cuenta del proveedor.</li>
            <li><strong>Visitas anónimas:</strong> registramos qué páginas se visitan (sin IP ni identificador de navegador) para entender el uso general del sitio.</li>
          </ul>

          <h3>Con quién se comparte</h3>
          <p>
            Cuando conversas con el asistente, el contenido de esa conversación —incluidos los archivos que adjuntes y tu perfil docente, si lo completaste— se envía al proveedor de IA que elegiste
            (OpenAI, Google Gemini o Anthropic/Claude) para generar la respuesta, según sus propias políticas de
            privacidad. Si inicias sesión con Google, Google procesa esa autenticación según su propia política.
            Si quien administra el sitio activa el registro de solicitudes en su proyecto de Google AI
            Studio, Google conserva además una copia de las conversaciones con Gemini durante el plazo
            configurado (55 días como máximo), visible para quien administra ese proyecto.
            No vendemos ni compartimos tus datos con terceros para publicidad.
          </p>

          <h3>Cómo protegemos tus datos</h3>
          <p>
            Las contraseñas se guardan cifradas (bcrypt), nunca en texto plano. La sesión viaja en una cookie que
            JavaScript no puede leer (HttpOnly), lo que reduce el riesgo de robo de sesión. Las claves de API del
            servidor y las que pegues tú se guardan solo en el servidor, nunca en tu navegador.
          </p>

          <h3>Tus derechos</h3>
          <p>
            Puedes pedir la eliminación de tu cuenta y de todos los datos asociados (conversaciones, archivos,
            agenda) escribiendo a quien administre esta instancia del sitio. Al eliminar tu cuenta, se elimina todo
            lo anterior de forma permanente.
          </p>
        </article>

        <article id="terminos" className="legal-section">
          <h2>Términos y condiciones</h2>
          <p>Al usar este sitio, aceptas lo siguiente:</p>
          <ul>
            <li>Esta herramienta es un apoyo para la planificación docente, no un sustituto del criterio profesional del profesor. Las respuestas de la IA pueden contener errores y deben revisarse antes de usarse en clase.</li>
            <li>Eres responsable del contenido que subas o escribas: no subas datos personales de estudiantes (nombres, calificaciones, fotos) ni material con derechos de autor que no tengas permiso de usar.</li>
            <li>No está permitido usar el asistente para generar contenido dañino, ilegal, o que viole las políticas de uso de los proveedores de IA conectados (OpenAI, Google, Anthropic).</li>
            <li>Si usas tu propia clave de API, los costos de esas consultas corren por tu cuenta ante el proveedor correspondiente.</li>
            <li>El servicio se ofrece "tal cual", sin garantía de disponibilidad continua. Quien administra esta instancia puede suspender o eliminar cuentas que incumplan estos términos.</li>
          </ul>
        </article>

        <article id="cookies" className="legal-section">
          <h2>Política de cookies</h2>
          <p>Usamos la cantidad mínima de almacenamiento necesaria para que el sitio funcione:</p>
          <table className="legal-table">
            <thead>
              <tr><th>Nombre</th><th>Tipo</th><th>Para qué</th><th>Duración</th></tr>
            </thead>
            <tbody>
              <tr><td><code>access_token</code></td><td>Cookie (HttpOnly)</td><td>Mantener tu sesión iniciada</td><td>Hasta que cierres sesión o expire</td></tr>
              <tr><td><code>agente_didactico_theme</code></td><td>Almacenamiento local del navegador</td><td>Recordar si prefieres modo claro u oscuro</td><td>Hasta que lo borres</td></tr>
              <tr><td><code>agente_didactico_materia</code></td><td>Almacenamiento local del navegador</td><td>Recordar la materia/color que elegiste</td><td>Hasta que lo borres</td></tr>
              <tr><td><code>agente_didactico_default_provider</code></td><td>Almacenamiento local del navegador</td><td>Recordar tu IA preferida por defecto</td><td>Hasta que lo borres</td></tr>
            </tbody>
          </table>
          <p style={{ marginTop: 14 }}>
            No usamos cookies de publicidad ni de rastreo entre sitios. La cookie de sesión es estrictamente
            necesaria para que el inicio de sesión funcione y no se puede desactivar sin dejar de poder usar tu
            cuenta. Puedes borrar el almacenamiento local del navegador en cualquier momento desde la configuración
            de tu navegador, sin que eso cierre tu sesión.
          </p>
        </article>
      </div>
    </section>
  )
}
