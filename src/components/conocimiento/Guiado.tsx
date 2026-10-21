import { useId, useState } from 'react'
import { decision, nombre } from '../../api/client'
import Panel from '../Shared'
import { IconChart, IconCurve, IconFunnel, IconShieldCheck, IconThermo } from '../Icons'
import { COLOR_NIVEL, NIVELES, grado, numero, ventana, type Condicion, type Modelo } from './difuso'

const COLOR_DECISION: Record<string, string> = {
  AUTORIZAR_ALMACENAMIENTO: '#2E7D32', AUTORIZAR_CON_MONITOREO: '#5E8F35', CORREGIR_Y_REEVALUAR: '#C48924',
  SIN_CONCLUSION_AUTOMATICA: '#0B5785', BLOQUEAR_INGRESO: '#C2410C', RETIRAR_LOTE: '#A1271D', CUARENTENA: '#5C1410',
}
const CORTO: Record<string, string> = {
  AUTORIZAR_ALMACENAMIENTO: 'Autorizar', AUTORIZAR_CON_MONITOREO: 'Con monitoreo', CORREGIR_Y_REEVALUAR: 'Corregir',
  SIN_CONCLUSION_AUTOMATICA: 'Sin conclusión', BLOQUEAR_INGRESO: 'Bloquear', RETIRAR_LOTE: 'Retirar', CUARENTENA: 'Cuar.',
}
const PRIORIDADES = [
  { titulo: 'Alerta sanitaria o cuarentena', texto: 'Si existe, siempre gana: separar y solicitar evaluación técnica.', reglas: 'MF01', color: '#5C1410' },
  { titulo: 'Condición de suspensión', texto: 'Según la fase: bloquea el ingreso, retira el lote o queda sin conclusión.', reglas: 'MF02–MF04', color: '#A1271D' },
  { titulo: 'Hallazgo que requiere corrección', texto: 'Corregir y volver a evaluar.', reglas: 'MF05', color: '#8A4300' },
  { titulo: 'Faltan datos o evidencia', texto: 'Sin conclusión automática: nunca se asume un valor favorable.', reglas: 'MF06–MF07', color: '#0B5785' },
  { titulo: 'Con plan de seguimiento vigente', texto: 'Conservación baja autoriza, media autoriza con monitoreo y alta pide corregir.', reglas: 'MF08–MF11', color: '#2A5A42' },
  { titulo: 'Sin plan registrado', texto: 'Solo autoriza si la conservación es plenamente baja y sin motivos de seguimiento.', reglas: 'MF12–MF14', color: '#2E7D32' },
]
const tonoSeveridad: Record<string, string> = { bajo: 'ok', medio: 'warn', alto: 'crit' }

function enPalabras(c: Condicion, nombreDe: (id: string) => string): string {
  if (c.entrada) return `${nombreDe(c.entrada)} en nivel ${c.conjunto}`
  const partes = (c.todos ?? c.alguno ?? []).map(h => enPalabras(h, nombreDe))
  if (partes.length === 1) return partes[0]
  return (c.todos ? 'A la vez: ' : 'Basta una: ') + partes.join(c.todos ? ' y ' : ' o ').replace(/^./, s => s.toLowerCase())
}

export default function Guiado({ modelo }: { modelo: Modelo }) {
  const nucleo = modelo.modulos[0]
  const ids = Object.keys(nucleo.entradas)
  const [variable, setVariable] = useState(ids[0])
  const [valores, setValores] = useState<Record<string, number>>(() => Object.fromEntries(ids.map(id => {
    const e = nucleo.entradas[id], [a, b] = ventana(e)
    return [id, e.referencia !== undefined ? e.referencia + (b - a) * 0.04 : (a + b) / 2]
  })))
  const idRango = useId()
  const e = nucleo.entradas[variable]
  const [a, b] = ventana(e)
  const x = valores[variable]
  const px = (v: number) => 40 + ((v - a) / (b - a)) * 525
  const curva = (p: number[]) => Array.from({ length: 121 }, (_, i) => { const v = a + ((b - a) * i) / 120; return `${px(v).toFixed(1)},${(170 - grado(v, p) * 150).toFixed(1)}` }).join(' ')
  const mu = Object.fromEntries(NIVELES.map(n => [n, e.conjuntos[n] ? grado(x, e.conjuntos[n]) : 0])) as Record<string, number>
  const activos = NIVELES.filter(n => mu[n] > 0.001).sort((p, q) => mu[q] - mu[p])
  const decimales = b - a < 10 ? 2 : 1
  const texto = `${numero(x, decimales)} ${e.unidad}`
  const frase = activos.length === 1 ? `${e.nombre} de ${texto} es completamente «${activos[0]}».`
    : `${e.nombre} de ${texto} es ${activos.map(n => `«${n}» en ${numero(mu[n])}`).join(' y ')}.`
  const final = modelo.decision
  const nombreDe = (id: string) => nucleo.entradas[id]?.nombre ?? id
  const paso = Number(((b - a) / 200).toPrecision(1))

  return <div className="stack">
    <Panel title="Cómo piensa el sistema, en cinco pasos">
      <p className="muted" style={{ marginTop: -8 }}>En lugar de un “sí o no” rígido, cada dato pertenece en parte a varios niveles a la vez. Cada paso se ilumina en orden.</p>
      <div className="pipeline" aria-label="Flujo de inferencia">
        {[
          { Icono: IconThermo, titulo: '1 · Mediciones', texto: `${ids.length} entradas (${ids.filter(id => !nucleo.entradas[id].aplica_si || nucleo.entradas[id].aplica_si?.igual === 'HERMETICO').length} en hermético)` },
          { Icono: IconCurve, titulo: '2 · Fuzzificación', texto: 'cuánto es bajo, medio o alto' },
          { Icono: IconFunnel, titulo: `3 · ${nucleo.reglas.length} reglas ${nucleo.reglas[0]?.id}–${nucleo.reglas[nucleo.reglas.length - 1]?.id}`, texto: 'Y = mínimo · O = máximo' },
          { Icono: IconChart, titulo: '4 · Conservación', texto: 'severidad 0–100 por centroide' },
          { Icono: IconShieldCheck, titulo: '5 · Decisión', texto: `${final?.reglas.length ?? 0} reglas MF · ${final?.clasificacion.length ?? 0} acciones`, final: true },
        ].map((s, i, todos) => <div key={s.titulo} style={{ display: 'contents' }}>
          <div className={`pipeline-step${s.final ? ' final' : ''}`} style={{ animationDelay: `${i * 1.2}s` }}><s.Icono size={24} /><b>{s.titulo}</b><span>{s.texto}</span></div>
          {i < todos.length - 1 && <div className="pipeline-arrow" aria-hidden="true"><svg width="36" height="12" viewBox="0 0 36 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 6h28" /><path d="M26 2l6 4-6 4" style={{ strokeDasharray: 'none', animation: 'none' }} /></svg></div>}
        </div>)}
      </div>
    </Panel>

    <Panel title="Explora una medición">
      <p className="muted" style={{ marginTop: -8 }}>Mueve el control y mira cómo cambia el grado de pertenencia (μ) a cada nivel.</p>
      <div className="chip-group" role="group" aria-label="Medición" style={{ marginBottom: 20 }}>
        {ids.map(id => <button key={id} aria-pressed={id === variable} onClick={() => setVariable(id)}>{nucleo.entradas[id].nombre}</button>)}
      </div>
      <div className="explorer">
        <div className="stack compact" style={{ marginTop: 0 }}>
          <svg viewBox="0 0 600 200" role="img" aria-label={`Funciones de pertenencia de ${e.nombre}; valor actual ${texto}`}>
            <path d="M40 20V170H565" fill="none" stroke="#C9C2B4" strokeWidth="1.5" />
            {NIVELES.filter(n => e.conjuntos[n]).map(n => <polyline key={n} points={curva(e.conjuntos[n])} fill="none" stroke={COLOR_NIVEL[n]} strokeWidth="3" strokeLinejoin="round" strokeDasharray={n === 'medio' ? '8 5' : undefined} />)}
            <line x1={px(x)} x2={px(x)} y1="14" y2="170" stroke="#1B3B2B" strokeWidth="2" />
            <circle cx={px(x)} cy="14" r="5" fill="#1B3B2B" />
            <text x="40" y="190" fontSize="12" fill="#5F5A51">{numero(a, decimales)} {e.unidad}</text>
            <text x="565" y="190" fontSize="12" fill="#5F5A51" textAnchor="end">{numero(b, decimales)} {e.unidad}</text>
            <text x="30" y="26" fontSize="12" fill="#5F5A51" textAnchor="end">1</text>
            <text x="30" y="172" fontSize="12" fill="#5F5A51" textAnchor="end">0</text>
          </svg>
          <div className="field"><label htmlFor={idRango}>{e.nombre}: <span className="mono">{texto}</span></label>
            <input id={idRango} type="range" min={a} max={b} step={paso} value={x} onChange={ev => setValores(v => ({ ...v, [variable]: Number(ev.target.value) }))} aria-valuetext={texto} />
          </div>
          <div className="legend">{NIVELES.map(n => <span key={n}><i style={{ background: n === 'medio' ? 'transparent' : COLOR_NIVEL[n], borderTop: n === 'medio' ? `3px dashed ${COLOR_NIVEL[n]}` : undefined }} />{n.replace(/^./, s => s.toUpperCase())}</span>)}</div>
        </div>
        <div className="stack compact" style={{ marginTop: 0, gap: 14 }}>
          <div className="explorer-reading" aria-live="polite"><span className="eyebrow" style={{ color: 'var(--color-forest-mid)' }}>Lectura en palabras</span><p>{frase}</p></div>
          {NIVELES.map(n => <div className="mu-bar" key={n}>
            <div><strong>{n.replace(/^./, s => s.toUpperCase())}</strong><span className="mono">μ = {numero(mu[n])}</span></div>
            <div className="mu-track"><div style={{ width: `${Math.round(mu[n] * 100)}%`, background: COLOR_NIVEL[n] }} /></div>
          </div>)}
          <p className="muted" style={{ margin: 0, fontSize: 13 }}>{e.referencia !== undefined && `Cerca de la referencia (${e.referencia} ${e.unidad}) el dato es a la vez un poco de dos niveles: así el sistema no cambia de decisión por una décima.`}{e.aplica_si && ` Solo aplica en almacenamiento ${nombre(e.aplica_si.igual).toLowerCase()}.`}</p>
        </div>
      </div>
    </Panel>

    <Panel title={`Las ${nucleo.reglas.length} reglas de conservación, en palabras`}>
      <p className="muted" style={{ marginTop: -8 }}>“A la vez” exige que se cumplan todas (toma el menor grado); “Basta una” toma el mayor.</p>
      <div className="rule-grid">{nucleo.reglas.map(r => <article className="rule-card" key={r.id}>
        <header><span className="badge code">{r.id}</span><span>{r.aplica_si ? nombre(r.aplica_si.igual) : 'Ambas modalidades'}</span></header>
        <p>{enPalabras(r.si, nombreDe)}.</p>
        <div className="actions" style={{ fontSize: 13 }}><span className="muted">Severidad</span><span className={`badge ${tonoSeveridad[r.entonces] ?? ''}`}>{r.entonces}</span></div>
      </article>)}</div>
    </Panel>

    {final && <Panel title="De la conservación a la decisión">
      <p className="muted" style={{ marginTop: -8 }}>La capa final revisa primero las alertas críticas. Solo si no hay ninguna, la severidad de conservación decide.</p>
      <ol className="priority-list">{PRIORIDADES.map((p, i) => <li key={p.reglas}>
        <span className="priority-n" style={{ background: p.color }}>{i + 1}</span>
        <div><strong>{p.titulo}</strong><span>{p.texto}</span></div>
        <span className="badge code">{p.reglas}</span>
      </li>)}</ol>
      <div className="stack compact">
        <strong style={{ fontSize: 13 }}>Escala de acciones de la salida final (0–100)</strong>
        <div className="scale-bar" role="img" aria-label={final.clasificacion.map(c => `${decision(c.decision)} hasta ${Math.min(c.hasta, 100)}`).join('; ')}>
          {final.clasificacion.map((c, i) => { const desde = i ? final.clasificacion[i - 1].hasta : 0, hasta = Math.min(c.hasta, 100)
            return <div key={c.decision} style={{ width: `${hasta - desde}%`, background: COLOR_DECISION[c.decision] ?? '#5F5A51', color: c.decision === 'CORREGIR_Y_REEVALUAR' ? '#1B3B2B' : '#fff' }} title={decision(c.decision)}>{CORTO[c.decision] ?? c.decision}</div> })}
        </div>
        <div className="scale-ticks" aria-hidden="true"><span style={{ left: 0 }}>0</span>{final.clasificacion.slice(0, -1).map(c => <span key={c.decision} style={{ left: `${c.hasta}%` }}>{String(c.hasta).replace('.', ',')}</span>)}<span style={{ left: '100%' }}>100</span></div>
        <p className="muted" style={{ margin: 0, fontSize: 13 }}>El centroide codifica acciones, no probabilidades de inocuidad ni una escala física.</p>
      </div>
    </Panel>}
  </div>
}
