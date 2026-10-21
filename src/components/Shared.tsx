import { cloneElement, isValidElement, useEffect, useId, useRef, type CSSProperties, type ReactNode, type ReactElement } from 'react'
import { ApiError, nombre, tonoEstado, type Tono } from '../api/client'
import { IconAlert, IconArrowLeft } from './Icons'

export default function Panel({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return <section className="panel">
    {title && (actions ? <div className="page-heading" style={{ marginBottom: 16 }}><h2 style={{ margin: 0 }}>{title}</h2><div className="actions">{actions}</div></div> : <h2>{title}</h2>)}
    {children}
  </section>
}

export function ErrorMessage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (!error) return null
  return <div role="alert" className="message error"><IconAlert size={20} />
    <div><strong>{error instanceof Error ? error.message : String(error)}</strong>
      {error instanceof ApiError && error.status === 409 && <span>Actualiza las revisiones y revisa la captura antes de reenviar.</span>}
      {error instanceof ApiError && error.status === 401 && <span>Vuelve a iniciar sesión desde el botón de la cabecera.</span>}
      {error instanceof ApiError && error.requestId && <small>Referencia: {error.requestId}</small>}
    </div>
    {onRetry && <button className="btn-sm" onClick={onRetry}>Reintentar</button>}
  </div>
}

/** Etiqueta asociada al control hijo; `hint` y `error` se enlazan con aria-describedby. */
export function Field({ label, children, hint, error }: { label: string; children: ReactNode; hint?: string; error?: string }) {
  const id = useId()
  const descripcion = error ? `${id}-error` : hint ? `${id}-hint` : undefined
  const extra: Record<string, unknown> = { id }
  if (descripcion) extra['aria-describedby'] = descripcion
  if (error) extra['aria-invalid'] = true
  return <div className="field"><label htmlFor={id}>{label}</label>
    {isValidElement(children) ? cloneElement(children as ReactElement<Record<string, unknown>>, extra) : children}
    {error ? <span id={descripcion} className="field-error"><IconAlert size={14} />{error}</span> : hint && <span id={descripcion} className="field-hint">{hint}</span>}
  </div>
}

/* Skeletons: aria-busy en el contenedor y texto oculto; nunca role=status. */
export function Skeleton({ width, height, className = '', style }: { width?: number | string; height?: number | string; className?: string; style?: CSSProperties }) {
  return <div className={`sk ${className}`} style={{ width, height, ...style }} aria-hidden="true" />
}
export function SkeletonTable({ rows = 4, cols = 4 }: { rows?: number; cols?: number }) {
  const anchos = ['80%', '55%', '65%', '45%', '70%', '60%']
  return <div className="sk-table" aria-hidden="true">
    <div className="sk-row head" style={{ '--cols': cols } as CSSProperties}>{Array.from({ length: cols }, (_, c) => <Skeleton key={c} className="sk-line" width={anchos[c % anchos.length]} height={10} />)}</div>
    {Array.from({ length: rows }, (_, r) => <div className="sk-row" key={r} style={{ '--cols': cols } as CSSProperties}>
      {Array.from({ length: cols }, (_, c) => c === cols - 1 ? <Skeleton key={c} className="sk-btn" width="70%" /> : c === 2 ? <Skeleton key={c} className="sk-pill" width={anchos[(r + c) % anchos.length]} /> : <Skeleton key={c} className="sk-line" width={anchos[(r + c) % anchos.length]} height={13} />)}
    </div>)}
  </div>
}
export function SkeletonPanel({ lines = 3, table }: { lines?: number; table?: { rows?: number; cols?: number } }) {
  return <section className="panel stack compact" aria-hidden="true" style={{ marginTop: 0 }}>
    <Skeleton className="sk-line" width={220} height={16} />
    {table ? <SkeletonTable {...table} /> : Array.from({ length: lines }, (_, i) => <Skeleton key={i} className="sk-line" width={`${90 - i * 12}%`} />)}
  </section>
}
export function SkeletonPage({ metrics = false, label = 'Cargando…' }: { metrics?: boolean; label?: string }) {
  return <div className="stack" aria-busy="true">
    <span className="sr-only">{label}</span>
    <div className="page-heading" aria-hidden="true">
      <div><Skeleton className="sk-line" width={160} height={10} /><Skeleton className="sk-title" /><Skeleton className="sk-line" width={300} /></div>
      <Skeleton className="sk-btn" width={168} height={44} />
    </div>
    {metrics && <div className="metrics" aria-hidden="true">{[0, 1, 2].map(i => <div className="panel metric-card" key={i}><Skeleton className="sk-circle" width={44} height={44} style={{ borderRadius: 12 }} /><div style={{ flex: 1, gap: 8 }}><Skeleton className="sk-line" width="70%" height={10} /><Skeleton className="sk-line" width="30%" height={24} /></div></div>)}</div>}
    <SkeletonPanel table={{ rows: 4, cols: 5 }} />
  </div>
}

export function Empty({ children, title, icon, action }: { children: ReactNode; title?: string; icon?: ReactNode; action?: ReactNode }) {
  if (!title && !icon && !action) return <p className="empty">{children}</p>
  return <div className="empty-state">{icon && <div className="empty-icon">{icon}</div>}{title && <strong>{title}</strong>}<p>{children}</p>{action}</div>
}

export function Badge({ estado, tono, children }: { estado?: string | null; tono?: Tono; children?: ReactNode }) {
  return <span className={`badge dot ${tono ?? tonoEstado(estado)}`}>{children ?? (estado ? nombre(estado) : 'Sin definir')}</span>
}

/** Confirmación modal con <dialog> nativo: atrapa el foco y se cierra con Esc. */
export function ConfirmDialog({ open, title, children, confirmLabel, danger, busy, onConfirm, onCancel }: {
  open: boolean; title: string; children: ReactNode; confirmLabel: string; danger?: boolean; busy?: boolean; onConfirm: () => void; onCancel: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  const titulo = useId()
  return <dialog ref={ref} className="dialog" aria-labelledby={titulo} onCancel={e => { e.preventDefault(); onCancel() }}>
    <h2 id={titulo}>{title}</h2>
    <div className="stack compact" style={{ marginTop: 0 }}>{children}</div>
    <div className="actions end" style={{ marginTop: 20 }}>
      <button type="button" onClick={onCancel} disabled={busy}>Cancelar</button>
      <button type="button" className={`primary${danger ? ' btn-danger' : ''}`} onClick={onConfirm} disabled={busy}>{busy ? 'Procesando…' : confirmLabel}</button>
    </div>
  </dialog>
}

export function PageHeader({ eyebrow, title, description, actions, back }: {
  eyebrow?: ReactNode; title: string; description?: ReactNode; actions?: ReactNode; back?: { label: string; onClick: () => void }
}) {
  return <div className="page-heading"><div>
    {back && <button className="back-link" onClick={back.onClick}><IconArrowLeft size={16} strokeWidth={2.4} />{back.label}</button>}
    {eyebrow && <p className="eyebrow">{eyebrow}</p>}
    <h1>{title}</h1>
    {description && <p className="muted">{description}</p>}
  </div>{actions && <div className="actions">{actions}</div>}</div>
}
