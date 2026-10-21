import { useId, useState } from 'react'
import { baseUrl, localAuth, supabase, NOTA_PROTOTIPO } from '../api/client'
import { ErrorMessage, Field } from '../components/Shared'
import { IconEye, IconEyeOff, IconLoader, IconPin } from '../components/Icons'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [user, setUser] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const idPassword = useId()
  async function login(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      if (localAuth) {
        const res = await fetch(baseUrl.replace(/\/api\/v1$/, '') + '/auth/local/sesion', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ usuario: user, password }),
        })
        const session = await res.json()
        if (!res.ok) throw new Error(session.mensaje || 'No se pudo iniciar sesión')
        sessionStorage.setItem('poscosegran-session', JSON.stringify(session))
      } else {
        if (!supabase) throw new Error('Configura Supabase o prepara el entorno local siguiendo el README.')
        const result = await supabase.auth.signInWithPassword({ email: user, password })
        if (result.error) throw result.error
      }
      onLogin()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <div className="login-split">
    <section className="login-brand on-dark">
      <div className="actions" style={{ gap: 12 }}><div className="brand-mark"><IconPin size={22} /></div><strong style={{ letterSpacing: '.05em' }}>POSCOSEGRAN</strong></div>
      <div className="stack" style={{ gap: 18, maxWidth: 520 }}>
        <p className="eyebrow">Gestión poscosecha · maíz chulpi</p>
        <h1>El cuidado del grano empieza con información.</h1>
        <p>Evalúa tus unidades de almacenamiento con un sistema difuso Mamdani y conserva un seguimiento explicable de cada decisión.</p>
      </div>
      <div className="login-stats">
        <div><strong>23</strong><span>reglas difusas</span></div>
        <div><strong>7</strong><span>decisiones posibles</span></div>
        <div><strong>52</strong><span>reglas documentales</span></div>
      </div>
    </section>
    <div className="login-form">
      <form onSubmit={login} className="login" style={{ margin: 0, padding: 0 }}>
        <div className="stack" style={{ gap: 6 }}>
          <h2>Iniciar sesión</h2>
          <p className="muted" style={{ margin: 0, fontSize: 14 }}>{localAuth ? 'Usa la cuenta que te asignó el equipo del proyecto.' : 'Ingresa con tu correo registrado.'}</p>
        </div>
        <Field label={localAuth ? 'Usuario local' : 'Correo electrónico'}>
          <input value={user} onChange={e => setUser(e.target.value)} required autoComplete="username" type={localAuth ? 'text' : 'email'} placeholder={localAuth ? (import.meta.env.DEV ? 'testeo' : '') : 'tu@correo.com'} />
        </Field>
        <div className="field"><label htmlFor={idPassword}>Contraseña</label>
          <div className="input-group">
            <input id={idPassword} type={visible ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
            <button type="button" className="icon-btn" style={{ border: 0, minHeight: 40 }} aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'} aria-pressed={visible} onClick={() => setVisible(v => !v)}>{visible ? <IconEyeOff size={18} /> : <IconEye size={18} />}</button>
          </div>
        </div>
        <ErrorMessage error={error} />
        <button className="primary" disabled={busy} style={{ minHeight: 48 }}>{busy ? <><IconLoader size={16} className="spin" />Ingresando…</> : 'Entrar'}</button>
        <p className="nota-prototipo" style={{ margin: 0 }}>{NOTA_PROTOTIPO}</p>
      </form>
    </div>
  </div>
}
