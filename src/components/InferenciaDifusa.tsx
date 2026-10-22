import { useState } from 'react'
import Panel from './Shared'
import DecisionMamdani from './DecisionMamdani'

type Antecedente = { entrada?: string; conjunto?: string; todos?: Antecedente[]; alguno?: Antecedente[] }
type Regla = { id: string; alfa: number; consecuente: string; puntos_salida: number[]; antecedente?: Antecedente; estado?: string }
type Entrada = {
  id: string; nombre: string; origen: string; unidad: string; estado: string; valor: number | null
  pertenencias: Record<string, number>; conjuntos: Record<string, number[]>; dominio: number[]
}
type Nucleo = {
  id: string; nombre: string; estado: string; entradas: Record<string, Entrada>; reglas: Regla[]
  centroide: number | null; area: number | null; curva: number[][]; fundamento_transicion: string
}
type Informe = { tipo: string; version: string; nota: string; modulos: Nucleo[]; decision?: Record<string, unknown> }
const colores: Record<string,string> = { bajo: '#2E7D32', medio: '#A56A0E', alto: '#C23C32' }
const numero = (n: number) => n.toLocaleString('es-PE', { maximumFractionDigits: 3 })

function condicion(n: Antecedente, entradas: Record<string, Entrada>): string {
  if (n.entrada) return `${entradas[n.entrada]?.nombre ?? n.entrada}: severidad ${n.conjunto}`
  return `(${(n.todos ?? n.alguno ?? []).map(h => condicion(h, entradas)).join(n.todos ? ' Y ' : ' O ')})`
}

function grado(x: number, puntos: number[]) {
  const [a,b,c,d] = puntos.length === 3 ? [puntos[0],puntos[1],puntos[1],puntos[2]] : puntos
  if (x < a || x > d) return 0
  if (x >= b && x <= c) return 1
  return x < b ? (x-a)/(b-a) : (d-x)/(d-c)
}

function Curvas({ entrada }: { entrada: Entrada }) {
  const conjuntos = Object.entries(entrada.conjuntos)
  const interiores = conjuntos.flatMap(([,p]) => p).filter(x => x > entrada.dominio[0] && x < entrada.dominio[1])
  const a = Math.min(...interiores), b = Math.max(...interiores), margen = Math.max((b-a)*.4,.01)
  const inicio = Math.max(entrada.dominio[0], Math.min(a-margen, entrada.valor ?? a))
  const fin = Math.min(entrada.dominio[1], Math.max(b+margen, entrada.valor ?? b))
  const px = (x:number) => 40+(x-inicio)/(fin-inicio)*520
  const xs = [...new Set([inicio,fin,...interiores])].sort((x,y)=>x-y)
  return <svg viewBox="0 0 600 180" role="img" aria-label={`Funciones de pertenencia de ${entrada.nombre}; los grados exactos se muestran en la tabla`}>
    <path d="M40 15V145H565" fill="none" stroke="currentColor" opacity=".35" />
    {conjuntos.map(([nombre,p]) => <polyline key={nombre} points={xs.map(x=>`${px(x)},${145-grado(x,p)*120}`).join(' ')} fill="none" stroke={colores[nombre]} strokeWidth="2.5" />)}
    {entrada.valor !== null && <line x1={px(entrada.valor)} x2={px(entrada.valor)} y1="15" y2="145" stroke="#1B3B2B" strokeDasharray="5 4" />}
    <text x="40" y="168" fontSize="12">{numero(inicio)} {entrada.unidad}</text><text x="560" y="168" textAnchor="end" fontSize="12">{numero(fin)} {entrada.unidad}</text>
    <text x="15" y="28" fontSize="12">1</text><text x="15" y="145" fontSize="12">0</text>
  </svg>
}

export default function InferenciaDifusa({ informe }: { informe: Record<string, unknown> | null | undefined }) {
  const [entradaSeleccionada, setEntradaSeleccionada] = useState('')
  if (!informe) return null
  const datos = informe as unknown as Informe
  const nucleo = datos.modulos[0]
  if (!nucleo) return null
  const entradas = Object.values(nucleo.entradas)
  const calculadas = entradas.filter(e => e.estado === 'CALCULADO')
  const medicion = calculadas.find(e => e.id === entradaSeleccionada) ?? calculadas[0]
  return <>{datos.decision && <DecisionMamdani informe={datos.decision}/>}<Panel title="Cómo evaluó el sistema difuso">
    <div className="stack">
      <p>Mamdani · AND mínimo · OR máximo · agregación máximo · centroide. {datos.nota}</p>
      <div className="metrics"><div><span>Modelo</span><strong>Mamdani tipo 1</strong></div><div><span>Entradas aplicables</span><strong>{entradas.filter(e => e.estado !== 'NO_APLICA').length}</strong></div><div><span>Reglas conjuntas</span><strong>{nucleo.reglas.length} · una salida de severidad</strong></div></div>
      <p>Las mediciones se evalúan juntas. La autorización también exige cumplir las restricciones y completar la evidencia necesaria.</p>
      <div className="table-scroll"><table><thead><tr><th>Entrada principal</th><th>Medición</th><th>Estado</th></tr></thead><tbody>{entradas.map(e => <tr key={e.id}><td>{e.nombre}</td><td>{e.valor === null ? 'Sin medición' : `${numero(e.valor)} ${e.unidad}`}</td><td>{e.estado.replaceAll('_', ' ').toLowerCase()}</td></tr>)}</tbody></table></div>
      {!medicion || nucleo.centroide === null ? <p>No hay mediciones suficientes para calcular la conservación. Los hallazgos y restricciones conocidos conservan su efecto.</p> : <>
        <label className="field">Explorar una entrada del núcleo<select value={medicion.id} onChange={e => setEntradaSeleccionada(e.target.value)}>{calculadas.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}</select></label>
        <div className="fuzzy-grid"><section><h3>1. Medición y pertenencias</h3><p>{medicion.nombre}: <strong>{numero(medicion.valor!)} {medicion.unidad}</strong> · {medicion.origen}</p><Curvas entrada={medicion}/>
          <div className="chips">{Object.entries(medicion.pertenencias).map(([nombre,g])=><span key={nombre} className="chip" style={{borderBottom:`3px solid ${colores[nombre]}`}}>{nombre}: {numero(g)}</span>)}</div>
        </section><section><h3>2. Agregación y centroide</h3><svg viewBox="0 0 600 180" role="img" aria-label={`Conjunto de salida agregado; centroide ${numero(nucleo.centroide)}`}>
          <path d="M40 15V145H565" fill="none" stroke="currentColor" opacity=".35"/>
          <polygon points={`40,145 ${nucleo.curva.map(([x,y])=>`${40+x*5.2},${145-y*120}`).join(' ')} 560,145`} fill="#E5A93C" fillOpacity=".3" stroke="#A56A0E"/>
          <line x1={40+nucleo.centroide*5.2} x2={40+nucleo.centroide*5.2} y1="15" y2="145" stroke="#1B3B2B" strokeWidth="2"/>
          <text x="40" y="168" fontSize="12">0 · severidad baja</text><text x="560" y="168" textAnchor="end" fontSize="12">100 · alta</text>
        </svg><p>Centroide: <strong>{numero(nucleo.centroide)} / 100</strong> · área: {numero(nucleo.area!)}</p>
          <p>Este centroide es la entrada «conservación» de la decisión final Mamdani, junto con las restricciones, la evidencia, la fase y el plan.</p>
        </section></div>
        <details open><summary>3. Reglas activadas y fundamento del modelo</summary><div className="table-scroll"><table><thead><tr><th>Regla</th><th>SI</th><th>ENTONCES</th><th>Activación α</th></tr></thead><tbody>{nucleo.reglas.map(r=><tr key={r.id}><td>{r.id}</td><td>{r.antecedente ? condicion(r.antecedente, nucleo.entradas) : '—'}</td><td>Severidad {r.consecuente}</td><td>{r.estado === 'NO_APLICA' ? 'No aplica' : numero(r.alfa)}</td></tr>)}</tbody></table></div><p>{nucleo.fundamento_transicion}</p></details>
      </>}
    </div>
  </Panel></>
}
