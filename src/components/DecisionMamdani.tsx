import Panel from './Shared'
import { decision } from '../api/client'

type Nodo = {entrada?:string;conjunto?:string;todos?:Nodo[];alguno?:Nodo[]}
type Informe = {decision:string;centroide:number;area:number;curva:number[][];fundamento:string;
  clasificacion:{hasta:number;decision:string}[];
  entradas:Record<string,{nombre:string;valor:unknown;estado:string;pertenencias:Record<string,number>}>;
  reglas:{id:string;si:Nodo;alfa:number;entonces:string}[]}
const numero=(n:number)=>n.toLocaleString('es-PE',{maximumFractionDigits:3})

export default function DecisionMamdani({informe}:{informe:Record<string,unknown>}) {
  const x=informe as unknown as Informe
  function antecedente(n:Nodo):string {
    if(n.entrada) return `${x.entradas[n.entrada]?.nombre ?? n.entrada}: ${n.conjunto}`
    return `(${(n.todos??n.alguno??[]).map(antecedente).join(n.todos?' Y ':' O ')})`
  }
  return <Panel title="Decisión final mediante Mamdani">
    <p>Las reglas finales combinan conservación, evidencia y condiciones sanitarias. Se recortan sus consecuentes, se agregan por máximo y la acción es la clasificación del centroide.</p>
    <div className="metrics"><div><span>Centroide final</span><strong>{numero(x.centroide)}</strong></div><div><span>Reglas finales</span><strong>{x.reglas.length}</strong></div><div><span>Clasificación</span><strong>{decision(x.decision)}</strong></div></div>
    <svg viewBox="0 0 600 180" role="img" aria-label={`Salida final agregada Mamdani; centroide ${numero(x.centroide)}`} style={{width:'100%',maxHeight:240}}>
      <path d="M40 15V145H565" fill="none" stroke="currentColor" opacity=".35"/>
      <polygon points={`40,145 ${x.curva.map(([a,b])=>`${40+a*5.2},${145-b*120}`).join(' ')} 560,145`} fill="#E5A93C" fillOpacity=".35" stroke="#A56A0E"/>
      <line x1={40+x.centroide*5.2} x2={40+x.centroide*5.2} y1="15" y2="145" stroke="#1B3B2B" strokeWidth="2"/>
      <text x="40" y="168" fontSize="12">0 · codificación de acciones</text><text x="560" y="168" textAnchor="end" fontSize="12">100</text>
    </svg>
    <p className="muted">Esta salida codifica acciones; no mide una magnitud física ni una probabilidad de inocuidad. Área agregada: {numero(x.area)}.</p>
    <details><summary>Reglas finales y activaciones</summary><div className="table-scroll"><table><thead><tr><th>Regla</th><th>SI</th><th>ENTONCES</th><th>α</th></tr></thead><tbody>{x.reglas.map(r=><tr key={r.id}><td>{r.id}</td><td>{antecedente(r.si)}</td><td>{decision(r.entonces)}</td><td>{numero(r.alfa)}</td></tr>)}</tbody></table></div></details>
    <details><summary>Evidencia y pertenencias del nivel final</summary><div className="table-scroll"><table><thead><tr><th>Antecedente</th><th>Valor</th><th>Estado</th><th>Pertenencias</th></tr></thead><tbody>{Object.entries(x.entradas).map(([k,e])=><tr key={k}><td>{e.nombre}</td><td>{e.valor===null?'Sin dato':String(e.valor)}</td><td>{e.estado}</td><td>{Object.entries(e.pertenencias).map(([c,v])=>`${c}: ${numero(v)}`).join(' · ')}</td></tr>)}</tbody></table></div></details>
    <details><summary>Clasificación del centroide y fundamento</summary><div className="table-scroll"><table><thead><tr><th>Intervalo de salida</th><th>Acción</th></tr></thead><tbody>{x.clasificacion.map((c,i)=><tr key={c.decision}><td>{i?x.clasificacion[i-1].hasta:0} ≤ centroide &lt; {Math.min(c.hasta,100)}</td><td>{decision(c.decision)}</td></tr>)}</tbody></table></div><p>{x.fundamento}</p></details>
  </Panel>
}
