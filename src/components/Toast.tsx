import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'
import { IconAlert, IconCheck, IconX } from './Icons'

type Aviso = { id: number; titulo: string; detalle?: string; tipo: 'ok' | 'error' }
type Avisar = (titulo: string, detalle?: string, tipo?: Aviso['tipo']) => void
const Contexto = createContext<Avisar>(() => {})

/** Avisos efímeros de éxito. Se anuncian con aria-live y se cierran solos a los 4 s. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const siguiente = useRef(0)
  const cerrar = useCallback((id: number) => setAvisos(a => a.filter(x => x.id !== id)), [])
  const avisar = useCallback<Avisar>((titulo, detalle, tipo = 'ok') => {
    const id = ++siguiente.current
    setAvisos(a => [...a.slice(-2), { id, titulo, detalle, tipo }])
    window.setTimeout(() => cerrar(id), 4000)
  }, [cerrar])
  return <Contexto.Provider value={avisar}>
    {children}
    <div className="toast-region" aria-live="polite" aria-atomic="false">
      {avisos.map(a => <div key={a.id} className={`toast${a.tipo === 'error' ? ' error' : ''}`}>
        {a.tipo === 'error' ? <IconAlert size={20} /> : <IconCheck size={20} strokeWidth={2.5} style={{ color: '#E5A93C' }} />}
        <div><strong>{a.titulo}</strong>{a.detalle && <span>{a.detalle}</span>}</div>
        <button aria-label="Cerrar aviso" onClick={() => cerrar(a.id)}><IconX size={16} strokeWidth={2.4} /></button>
      </div>)}
    </div>
  </Contexto.Provider>
}

export const useToast = () => useContext(Contexto)
