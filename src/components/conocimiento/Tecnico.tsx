import { Fragment, type ReactNode } from 'react'
import { nombre } from '../../api/client'
import Panel from '../Shared'
import { useToast } from '../Toast'
import { IconCopy } from '../Icons'
import { agregar, evaluar, forma, formula, grado, lista, numero, type Modelo } from './difuso'

const OPERADORES: Record<string, { simbolo: string; titulo: string; formula: string }> = {
  AND: { simbolo: '∧', titulo: 'AND · T-norma', formula: 'μ(A∧B) = min(μA, μB)' },
  OR: { simbolo: '∨', titulo: 'OR · S-norma', formula: 'μ(A∨B) = max(μA, μB)' },
  implicacion: { simbolo: '→', titulo: 'Implicación Mamdani', formula: 'μR(z) = min(α, μC(z))' },
  agregacion: { simbolo: '⋃', titulo: 'Agregación', formula: 'μ(z) = maxᵢ μRᵢ(z)' },
  defuzzificacion: { simbolo: 'z*', titulo: 'Centroide exacto', formula: 'z* = ∫z·μ(z)dz / ∫μ(z)dz' },
}
const PALABRAS = /\b(SISTEMA|ENTRADA|SALIDA|REGLA|SI|ENTONCES|ES|OPERADORES|APLICA_SI|CLASIFICACION)\b/
const TOKEN = /(#.*$)|("[^"]*")|\b(trapmf|trimf|min|max|centroide_exacto)\b|\b(SISTEMA|ENTRADA|SALIDA|REGLA|SI|ENTONCES|ES|OPERADORES|APLICA_SI|CLASIFICACION)\b|(-?\d+(?:\.\d+)?)/g

/** Resaltado mínimo del lenguaje FIS mostrado; el texto copiado es el plano. */
function resaltar(linea: string): ReactNode[] {
  const out: ReactNode[] = []
  let ultimo = 0
  for (const m of linea.matchAll(TOKEN)) {
    if (m.index! > ultimo) out.push(linea.slice(ultimo, m.index))
    const cls = m[1] ? 'tk-com' : m[2] ? 'tk-str' : m[3] ? 'tk-fn' : m[4] ? 'tk-kw' : 'tk-num'
    out.push(<span key={m.index} className={cls}>{m[0]}</span>)
    ultimo = m.index! + m[0].length
  }
  if (ultimo < linea.length) out.push(linea.slice(ultimo))
  return out
}

function Codigo({ archivo, texto }: { archivo: string; texto: string }) {
  const avisar = useToast()
  async function copiar() {
    try { await navigator.clipboard.writeText(texto); avisar('Código copiado', archivo) }
    catch { avisar('No se pudo copiar', 'Selecciona el texto y cópialo manualmente.', 'error') }
  }
  return <div className="code-block">
    <header><span>{archivo}</span><button type="button" onClick={() => void copiar()}><IconCopy size={14} />Copiar</button></header>
    <pre tabIndex={0} aria-label={`Definición ${archivo}`}>{texto.split('\n').map((l, i) => <Fragment key={i}>{PALABRAS.test(l) || /[#"\d]/.test(l) ? resaltar(l) : l}{'\n'}</Fragment>)}</pre>
  </div>
}

function fisConservacion(m: Modelo) {
  const n = m.modulos[0], op = m.operadores
  const ancho = Math.max(...Object.keys(n.entradas).map(k => k.length))
  const lineas = [
    `# ${n.nombre}${n.origenes ? ` (${n.origenes.join(' · ')})` : ''}`,
    `SISTEMA ${n.id} : ${m.tipo}`,
    `  OPERADORES AND=${op.AND?.toLowerCase()}  OR=${op.OR?.toLowerCase()}  IMPL=${op.implicacion?.toLowerCase()}  AGREG=${op.agregacion?.toLowerCase()}  DEFUZZ=${op.defuzzificacion?.toLowerCase()}`,
    '',
  ]
  for (const [id, e] of Object.entries(n.entradas)) {
    lineas.push(`ENTRADA ${id.padEnd(ancho)} ∈ [${lista(e.dominio)}] "${e.unidad}"${e.referencia !== undefined ? `   # ref. ${e.referencia}` : ''}${e.aplica_si ? `  APLICA_SI ${e.aplica_si.contexto} = ${e.aplica_si.igual}` : ''}`)
    for (const [c, p] of Object.entries(e.conjuntos)) lineas.push(`  ${c.padEnd(5)} = ${forma(p)}(${lista(p)})`)
  }
  lineas.push('', 'SALIDA severidad ∈ [0, 100]')
  for (const [c, p] of Object.entries(m.salidas)) lineas.push(`  ${c.padEnd(5)} = ${forma(p)}(${lista(p)})`)
  lineas.push('')
  for (const r of n.reglas) lineas.push(`REGLA ${r.id}${r.aplica_si ? ` [${r.aplica_si.igual.toLowerCase()}]` : ''}: SI ${formula(r.si)} ENTONCES severidad ES ${r.entonces}`)
  return lineas.join('\n')
}

function fisDecision(m: Modelo) {
  const f = m.decision!
  const lineas: string[] = ['# Capa final: antecedentes derivados o de contexto, pertenencia 0/1 salvo la conservación']
  for (const [id, e] of Object.entries(f.entradas)) {
    if (Array.isArray(e.conjuntos)) lineas.push(`ENTRADA ${id} ∈ {${e.conjuntos.join(', ')}}   # ${e.nombre}`)
    else if (e.conjuntos) lineas.push(`ENTRADA ${id} ← ${e.modulo ?? 'capa 1'}   ${Object.entries(e.conjuntos).map(([c, p]) => `${c}=${forma(p)}(${lista(p)})`).join('  ')}`)
    else if (e.certeza_conjunto) lineas.push(`ENTRADA ${id} ← certeza(${e.modulo} ES ${e.certeza_conjunto})   # ${e.nombre}`)
    else lineas.push(`ENTRADA ${id} ∈ {presente, ausente}   # ${e.nombre}`)
  }
  lineas.push('')
  for (const r of f.reglas) lineas.push(`REGLA ${r.id}: SI ${formula(r.si, id => id, true)} ENTONCES ${r.entonces}`)
  lineas.push('', 'SALIDA decision ∈ [0, 100]   # codifica acciones; no es escala física ni probabilidad')
  for (const [c, p] of Object.entries(f.salidas)) lineas.push(`  ${c} = ${forma(p)}(${lista(p)})`)
  lineas.push(`CLASIFICACION ${f.clasificacion.map(c => `z* < ${c.hasta} → ${c.decision}`).join(' · ')}`)
  return lineas.join('\n')
}

/** Ejemplo resuelto con las curvas de la base activa: hermético, sin HR del almacén. */
function Ejemplo({ modelo }: { modelo: Modelo }) {
  const n = modelo.modulos[0]
  const entrada: Record<string, number> = { humedad_grano: 13.2, temperatura_grano: 18, granos_defectuosos: 2.5 }
  if (!Object.keys(entrada).every(k => n.entradas[k])) return null
  const mu = (id: string, c: string) => entrada[id] === undefined ? 0 : grado(entrada[id], n.entradas[id].conjuntos[c] ?? [0, 0, 0])
  const reglas = n.reglas.filter(r => !r.aplica_si || r.aplica_si.igual === 'HERMETICO').map(r => ({ id: r.id, entonces: r.entonces, alfa: evaluar(r.si, mu) }))
  const alfas: Record<string, number> = {}
  for (const r of reglas) alfas[r.entonces] = Math.max(alfas[r.entonces] ?? 0, r.alfa)
  const { curva, centroide } = agregar(modelo.salidas, alfas)
  const conservacion = modelo.decision?.entradas.conservacion?.conjuntos
  const muCons = centroide !== null && conservacion && !Array.isArray(conservacion) ? Object.entries(conservacion).map(([c, p]) => [c, grado(centroide, p)] as const) : []
  const nivelesEntrada = Object.entries(entrada).flatMap(([id, v]) => Object.entries(n.entradas[id].conjuntos).map(([c, p]) => ({ id, c, g: grado(v, p) })).filter(x => x.g > 0))
  const px = (z: number) => 40 + z * 5.6, py = (m: number) => 150 - m * 130
  return <Panel title="Ejemplo resuelto paso a paso">
    <p className="muted" style={{ marginTop: -8 }}>Almacenamiento hermético · humedad 13,2 % b.h. · temperatura 18 °C · defectuosos 2,5 % masa (la HR del almacén no aplica). Calculado con las curvas de la base activa.</p>
    <div className="worked">
      <div><span className="eyebrow">1 · Fuzzificación</span><code>{nivelesEntrada.map(x => `μ${x.c}(${n.entradas[x.id].nombre}) = ${numero(x.g)}`).join('\n')}</code></div>
      <div><span className="eyebrow">2 · Activación α</span><code>{reglas.filter(r => r.alfa > 0 || ['D02', 'D07'].includes(r.id)).map(r => `α${r.id} = ${numero(r.alfa)} → ${r.entonces}`).join('\n')}</code></div>
      <div><span className="eyebrow">3 · Agregación y centroide</span><code>{`μ(z) = max(${Object.entries(alfas).filter(([, v]) => v > 0).map(([k, v]) => `min(${numero(v)}, ${k})`).join(', ')})\nz* ≈ ${centroide === null ? 'sin área' : numero(centroide, 1)}`}</code></div>
      <div className="highlight"><span className="eyebrow">4 · Entrada a la capa 2</span><code>{`conservación(${centroide === null ? '—' : numero(centroide, 1)}):\n${muCons.filter(([, g]) => g > 0).map(([c, g]) => `  ${c} = ${numero(g)}`).join('\n')}`}</code></div>
    </div>
    <svg viewBox="0 0 640 180" role="img" aria-label={`Conjunto de salida agregado; centroide ${centroide === null ? 'no definido' : numero(centroide, 1)}`} style={{ width: '100%', maxWidth: 760, height: 'auto', marginTop: 16 }}>
      <path d="M40 20V150H600" fill="none" stroke="#C9C2B4" strokeWidth="1.5" />
      {Object.entries(modelo.salidas).map(([c, p]) => <polyline key={c} points={Array.from({ length: 101 }, (_, i) => `${px(i)},${py(grado(i, p))}`).join(' ')} fill="none" stroke={c === 'bajo' ? '#2E7D32' : c === 'medio' ? '#C48924' : '#B3261E'} strokeWidth="1.5" strokeDasharray="4 4" />)}
      <polygon points={`${px(0)},150 ${curva.filter((_, i) => i % 10 === 0).map(([z, m]) => `${px(z).toFixed(1)},${py(m).toFixed(1)}`).join(' ')} ${px(100)},150`} fill="#E5A93C" fillOpacity=".28" stroke="#C48924" strokeWidth="2" />
      {centroide !== null && <><line x1={px(centroide)} x2={px(centroide)} y1="14" y2="150" stroke="#1B3B2B" strokeWidth="2.5" /><text x={px(centroide) + 8} y="30" fontSize="13" fontWeight="700" fill="#1B3B2B">z* ≈ {numero(centroide, 1)}</text></>}
      <text x="40" y="170" fontSize="12" fill="#5F5A51">0</text><text x="600" y="170" fontSize="12" fill="#5F5A51" textAnchor="end">100 · severidad</text>
    </svg>
  </Panel>
}

export default function Tecnico({ modelo }: { modelo: Modelo }) {
  return <div className="stack">
    <Panel title="Operadores del sistema">
      <div className="op-grid">{Object.entries(modelo.operadores).map(([k, v]) => { const o = OPERADORES[k]; return o && <div className="op-card" key={k}>
        <span className="simbolo" aria-hidden="true">{o.simbolo}</span><strong>{o.titulo} · {nombre(v).toLowerCase()}</strong><code>{o.formula}</code>
      </div> })}</div>
    </Panel>
    <Panel title="Capa 1 · Conservación">
      <p className="muted" style={{ marginTop: -8 }}>{Object.keys(modelo.modulos[0].entradas).length} variables lingüísticas · {modelo.modulos[0].reglas.length} reglas · salida severidad [0, 100].</p>
      <Codigo archivo="conservacion.fis" texto={fisConservacion(modelo)} />
    </Panel>
    {modelo.decision && <Panel title="Capa 2 · Decisión final">
      <p className="muted" style={{ marginTop: -8 }}>{Object.keys(modelo.decision.entradas).length} antecedentes · {modelo.decision.reglas.length} reglas · {Object.keys(modelo.decision.salidas).length} salidas codificadas. Las acciones críticas son mutuamente excluyentes por sus antecedentes.</p>
      <Codigo archivo="decision.fis" texto={fisDecision(modelo)} />
    </Panel>}
    <Ejemplo modelo={modelo} />
  </div>
}
