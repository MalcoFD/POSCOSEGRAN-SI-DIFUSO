import { useState } from 'react'
import Panel from './Shared'
import DecisionMamdani from './DecisionMamdani'

type Antecedente = { entrada?: string; conjunto?: string; todos?: Antecedente[]; alguno?: Antecedente[] }
type Regla = { id: string; alfa: number; consecuente: string; puntos_salida: number[]; antecedente?: Antecedente; estado?: string }
type Modulo = {
  id: string; nombre: string; origen: string; unidad: string; estado: string; valor: number | null
  pertenencias: Record<string, number>; reglas: Regla[]; centroide: number | null; area: number | null
  curva: number[][]; solicitud: string | null; conjuntos: Record<string, number[]>; dominio: number[]
  fundamento_transicion: string
  entradas?: Record<string, Modulo>
}
type Informe = { tipo: string; version: string; nota: string; modulos: Modulo[] }
const colores: Record<string,string> = { bajo: '#2E7D32', medio: '#A56A0E', alto: '#C23C32' }
const numero = (n: number) => n.toLocaleString('es-PE', { maximumFractionDigits: 3 })

function condicion(n: Antecedente, entradas: Record<string, Modulo>): string {
  if (n.entrada) return `${entradas[n.entrada]?.nombre ?? n.entrada}: severidad ${n.conjunto}`
  return `(${(n.todos ?? n.alguno ?? []).map(h => condicion(h, entradas)).join(n.todos ? ' Y ' : ' O ')})`
}

function grado(x: number, puntos: number[]) {
  const [a,b,c,d] = puntos.length === 3 ? [puntos[0],puntos[1],puntos[1],puntos[2]] : puntos
  if (x < a || x > d) return 0
  if (x >= b && x <= c) return 1
  return x < b ? (x-a)/(b-a) : (d-x)/(d-c)
}

function Curvas({ modulo }: { modulo: Modulo }) {
  const conjuntos = Object.entries(modulo.conjuntos)
  const interiores = conjuntos.flatMap(([,p]) => p).filter(x => x > modulo.dominio[0] && x < modulo.dominio[1])
  const a = Math.min(...interiores), b = Math.max(...interiores), margen = Math.max((b-a)*.4,.01)
  const inicio = Math.max(modulo.dominio[0], Math.min(a-margen, modulo.valor ?? a))
  const fin = Math.min(modulo.dominio[1], Math.max(b+margen, modulo.valor ?? b))
  const px = (x:number) => 40+(x-inicio)/(fin-inicio)*520
  const xs = [...new Set([inicio,fin,...interiores])].sort((x,y)=>x-y)
  return <svg viewBox="0 0 600 180" role="img" aria-label={`Funciones de pertenencia de ${modulo.nombre}; los grados exactos se muestran en la tabla`}>
    <path d="M40 15V145H565" fill="none" stroke="currentColor" opacity=".35" />
    {conjuntos.map(([nombre,p]) => <polyline key={nombre} points={xs.map(x=>`${px(x)},${145-grado(x,p)*120}`).join(' ')} fill="none" stroke={colores[nombre]} strokeWidth="2.5" />)}
    {modulo.valor !== null && <line x1={px(modulo.valor)} x2={px(modulo.valor)} y1="15" y2="145" stroke="#1B3B2B" strokeDasharray="5 4" />}
    <text x="40" y="168" fontSize="12">{numero(inicio)} {modulo.unidad}</text><text x="560" y="168" textAnchor="end" fontSize="12">{numero(fin)} {modulo.unidad}</text>
    <text x="15" y="28" fontSize="12">1</text><text x="15" y="145" fontSize="12">0</text>
  </svg>
}

export default function InferenciaDifusa({ informe }: { informe: Record<string, unknown> | null | undefined }) {
  const [seleccion, setSeleccion] = useState('')
  const [entradaSeleccionada, setEntradaSeleccionada] = useState('')
  if (!informe) return null
  const datos = informe as unknown as Informe
  const calculados = datos.modulos.filter(m => m.estado === 'CALCULADO')
  const modulo = calculados.find(m => m.id === seleccion) ?? calculados.find(m => m.solicitud) ?? calculados[0]
  const nucleo = datos.modulos.find(m => m.entradas)
  const entradas = Object.values(nucleo?.entradas ?? {})
  const medicion = entradas.find(e => e.id === entradaSeleccionada && e.estado === 'CALCULADO') ?? entradas.find(e => e.estado === 'CALCULADO') ?? modulo
  return <>{informe.decision && <DecisionMamdani informe={informe.decision as Record<string,unknown>}/>}<Panel title="Cómo evaluó el sistema difuso">
    <div className="stack">
      <p>Mamdani · AND mínimo · OR máximo · agregación máximo · centroide. {datos.nota}</p>
      <div className="metrics"><div><span>Modelo</span><strong>Mamdani tipo 1</strong></div><div><span>{nucleo ? 'Entradas aplicables' : 'Módulos calculados'}</span><strong>{nucleo ? entradas.filter(e => e.estado !== 'NO_APLICA').length : `${calculados.length} de ${datos.modulos.length}`}</strong></div>{nucleo && <div><span>Reglas conjuntas</span><strong>{nucleo.reglas.length} · una salida de severidad</strong></div>}</div>
      {nucleo && <><p>Las mediciones se evalúan juntas. La autorización también exige cumplir las restricciones y completar la evidencia necesaria.</p><div className="table-scroll"><table><thead><tr><th>Entrada principal</th><th>Medición</th><th>Estado</th></tr></thead><tbody>{entradas.map(e => <tr key={e.id}><td>{e.nombre}</td><td>{e.valor === null ? 'Sin medición' : `${numero(e.valor)} ${e.unidad}`}</td><td>{e.estado.replaceAll('_', ' ').toLowerCase()}</td></tr>)}</tbody></table></div></>}
      {!modulo ? <p>No hay mediciones suficientes para calcular los módulos difusos. Los hallazgos y restricciones conocidos conservan su efecto.</p> : <>
        {nucleo ? <label className="field">Explorar una entrada del núcleo<select value={medicion.id} onChange={e => setEntradaSeleccionada(e.target.value)}>{entradas.filter(e => e.estado === 'CALCULADO').map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}</select></label> : <label className="field">Explorar una medición<select value={modulo.id} onChange={e => setSeleccion(e.target.value)}>{calculados.map(m => <option key={m.id} value={m.id}>{m.nombre} · {numero(m.centroide!)} / 100</option>)}</select></label>}
        <div className="fuzzy-grid"><section><h3>1. Medición y pertenencias</h3><p>{medicion.nombre}: <strong>{numero(medicion.valor!)} {medicion.unidad}</strong> · {medicion.origen}</p><Curvas modulo={medicion}/>
          <div className="chips">{Object.entries(medicion.pertenencias).map(([nombre,g])=><span key={nombre} className="chip" style={{borderBottom:`3px solid ${colores[nombre]}`}}>{nombre}: {numero(g)}</span>)}</div>
        </section><section><h3>2. Agregación y centroide</h3><svg viewBox="0 0 600 180" role="img" aria-label={`Conjunto de salida agregado; centroide ${numero(modulo.centroide!)}`}>
          <path d="M40 15V145H565" fill="none" stroke="currentColor" opacity=".35"/>
          <polygon points={`40,145 ${modulo.curva.map(([x,y])=>`${40+x*5.2},${145-y*120}`).join(' ')} 560,145`} fill="#E5A93C" fillOpacity=".3" stroke="#A56A0E"/>
          <line x1={40+modulo.centroide!*5.2} x2={40+modulo.centroide!*5.2} y1="15" y2="145" stroke="#1B3B2B" strokeWidth="2"/>
          <text x="40" y="168" fontSize="12">0 · severidad baja</text><text x="560" y="168" textAnchor="end" fontSize="12">100 · alta</text>
        </svg><p>Centroide: <strong>{numero(modulo.centroide!)} / 100</strong> · área: {numero(modulo.area!)}</p>
          <p>{modulo.solicitud === 'CORRECCION' ? 'Solicita corrección preventiva.' : modulo.solicitud === 'MONITOREO' ? 'Solicita seguimiento reforzado.' : 'No añade una solicitud correctiva.'} La decisión final considera también las otras mediciones, restricciones y datos pendientes.</p>
        </section></div>
        <details open={!!nucleo}><summary>3. Reglas activadas y fundamento del modelo</summary><div className="table-scroll"><table><thead><tr><th>Regla</th>{nucleo && <th>SI</th>}<th>ENTONCES</th><th>Activación α</th></tr></thead><tbody>{modulo.reglas.map(r=><tr key={r.id}><td>{r.id}</td>{nucleo && <td>{r.antecedente ? condicion(r.antecedente, nucleo.entradas!) : '—'}</td>}<td>Severidad {r.consecuente}</td><td>{r.estado === 'NO_APLICA' ? 'No aplica' : numero(r.alfa)}</td></tr>)}</tbody></table></div><p>{modulo.fundamento_transicion}</p></details>
      </>}
      <details><summary>Estado de todas las entradas del modelo</summary><div className="table-scroll"><table><thead><tr><th>Módulo</th><th>Estado</th><th>Centroide</th><th>Efecto</th></tr></thead><tbody>{datos.modulos.map(m=><tr key={m.id}><td>{m.nombre}</td><td>{m.estado.replaceAll('_',' ').toLowerCase()}</td><td>{m.centroide === null ? 'No disponible' : numero(m.centroide)}</td><td>{m.solicitud?.toLowerCase() ?? 'Sin solicitud adicional'}</td></tr>)}</tbody></table></div></details>
    </div>
  </Panel></>
}
