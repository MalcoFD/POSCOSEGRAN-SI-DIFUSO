import { useState } from 'react'
import Panel from './Shared'
import GraficoPertenencia from './GraficoPertenencia'
import { decision } from '../api/client'
import { antecedente, numero, texto, type Entrada, type Regla } from './conocimiento/difuso'
type Observada = { nombre: string; valor: number | string | null; estado: string; unidad: string; pertenencias: Record<string,number>; definicion: Entrada; fecha_observacion?: string; metodo?: string; evidencia?: string }
type Informe = { matriz: string | null; modalidad: string; centroide: number | null; area: number | null; curva: number[][]; entradas: Record<string,Observada>; reglas: (Regla & {alfa:number})[]; decision: string; recomendacion: string; fundamento: string }
export default function InferenciaDifusa({ informe }: { informe: Record<string, unknown> | null | undefined }) {
  const [todas, setTodas] = useState(false)
  if (!informe || informe.estructura !== 'MATRICIAL_DIRECTA') return null
  const x = informe.decision as Informe
  const activas = x.reglas.filter(r => r.alfa > 0)
  return <Panel title="Cálculo Mamdani de la evaluación"><div className="stack">
    <div className="metrics"><div><span>Matriz aplicada</span><strong>{x.matriz ?? 'Sin modalidad'} · {x.reglas.length} reglas</strong></div><div><span>Reglas activadas</span><strong>{activas.length}</strong></div><div><span>Centroide</span><strong>{x.centroide === null ? 'No calculable' : `${numero(x.centroide)} / 100`}</strong></div></div>
    <p>AND mínimo → implicación mínimo → agregación máximo → centroide exacto → recomendación. El cálculo lo realiza el servidor.</p>
    {x.centroide !== null && <><svg viewBox="0 0 600 200" role="img" aria-label={`Salida agregada y centroide ${numero(x.centroide)}`} style={{width:'100%',maxHeight:270}}><path d="M40 20V160H565" fill="none" stroke="currentColor" opacity=".3" /><polygon points={`40,160 ${x.curva.map(([a,b]) => `${40+a*5.2},${160-b*130}`).join(' ')} 560,160`} fill="#E5A93C" fillOpacity=".3" stroke="#A56A0E" /><line x1={40+x.centroide*5.2} x2={40+x.centroide*5.2} y1="20" y2="160" stroke="#1B3B2B" strokeWidth="2" /><text x="40" y="185" fontSize="12">0 · menor intervención</text><text x="560" y="185" fontSize="12" textAnchor="end">100 · mayor intervención</text></svg><p><strong>{decision(x.decision)}</strong> · área agregada {numero(x.area!)}. El índice no es una probabilidad.</p></>}
    <details open><summary>1. Entradas y pertenencias</summary><div className="stack">{Object.entries(x.entradas).map(([id,e]) => <section key={id}><h3>{e.nombre}: {e.valor === null ? 'Sin dato' : `${typeof e.valor === 'number' ? numero(e.valor) : texto(e.valor)} ${e.unidad === 'categoría' ? '' : e.unidad}`}</h3><p className="muted">{texto(e.estado)} · {e.metodo ?? 'Sin método'} · {e.fecha_observacion ? new Date(e.fecha_observacion).toLocaleString('es-PE') : 'Sin fecha'}</p>{e.estado !== 'NO_APLICA' && e.definicion.tipo === 'CONTINUA' && <GraficoPertenencia {...e.definicion} valor={typeof e.valor === 'number' ? e.valor : null} />}<div className="chips">{Object.entries(e.pertenencias).map(([k,v]) => <span className="chip" key={k}>{texto(k)}: {numero(v)}</span>)}</div>{e.evidencia && <p>{e.evidencia}</p>}</section>)}</div></details>
    <details open><summary>2. Reglas y activación α</summary><label className="check"><input type="checkbox" checked={todas} onChange={e => setTodas(e.target.checked)} />Mostrar también las reglas sin activación</label><div className="table-scroll"><table><thead><tr><th>Regla</th><th>Antecedentes unidos por Y</th><th>Consecuente</th><th>α</th></tr></thead><tbody>{(todas ? x.reglas : activas).map(r => <tr key={r.id}><td>{r.id}</td><td>{antecedente(r.si,x.entradas)}</td><td>{texto(r.entonces)}</td><td>{numero(r.alfa)}</td></tr>)}</tbody></table></div>{!activas.length && <p>No hay activaciones: revisa los datos pendientes.</p>}</details><p className="muted">{x.fundamento}</p>
  </div></Panel>
}
