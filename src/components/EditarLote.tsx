import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { request, type Schema } from '../api/client'
import { ErrorMessage, Field } from './Shared'
import { useToast } from './Toast'

/** Corrige el código de un lote. La variedad y el uso final son fijos en este prototipo. */
export default function EditarLote({ lote }: { lote: Schema['Lote'] }) {
  const qc = useQueryClient(), avisar = useToast()
  const [editando, setEditando] = useState(false)
  const [codigo, setCodigo] = useState(lote.codigo)
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null)
  if (!editando) return <button className="btn-sm" onClick={() => { setCodigo(lote.codigo); setError(null); setEditando(true) }}>Editar lote</button>
  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      await request<Schema['Lote']>(`/lotes/${lote.id}`, {
        method: 'PATCH', headers: { 'If-Match': `"${lote.revision}"` },
        body: JSON.stringify({ codigo: codigo.trim(), variedad: lote.variedad, uso_final: lote.uso_final }),
      })
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['almacenes-lotes'] }),
        qc.invalidateQueries({ queryKey: ['inicio'] }),
      ])
      setEditando(false)
      avisar('Lote actualizado', `Nuevo código: ${codigo.trim()}`)
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const sinCambios = codigo.trim() === lote.codigo
  return <form className="stack compact" onSubmit={e => void guardar(e)}>
    <Field label={`Código del lote ${lote.codigo}`}><input required maxLength={80} value={codigo} onChange={e => setCodigo(e.target.value)} autoFocus /></Field>
    <ErrorMessage error={error} />
    <div className="actions">
      <button className="primary" disabled={busy || sinCambios || !codigo.trim()}>{busy ? 'Guardando…' : 'Guardar código'}</button>
      <button type="button" disabled={busy} onClick={() => setEditando(false)}>Cancelar</button>
    </div>
  </form>
}
