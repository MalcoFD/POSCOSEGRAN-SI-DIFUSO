import Panel from './Shared'

type Condicion = { entrada?: string; conjunto?: string; todos?: Condicion[]; alguno?: Condicion[] }
type Nucleo = { entradas: Record<string, { nombre: string; unidad: string; referencia: number }>; reglas: { id: string; si: Condicion; entonces: string; aplica_si?: { igual: string } }[] }
type Final = { entradas: Record<string, { nombre: string; conjuntos?: Record<string, number[]> | string[] }>; reglas: { id: string; si: Condicion; entonces: string }[]; salidas: Record<string, number[]>; clasificacion: { hasta: number; decision: string }[]; fundamento: string }

export default function ModeloAlmacenamiento({ modelo }: { modelo: Record<string, unknown> | null | undefined }) {
  if (modelo?.estructura !== 'MULTIVARIABLE') return null
  const nucleo = (modelo.modulos as Nucleo[])[0]
  const final = modelo.decision as Final | undefined
  function texto(n: Condicion): string {
    if (n.entrada) return `${nucleo.entradas[n.entrada].nombre}: severidad ${n.conjunto}`
    return `(${(n.todos ?? n.alguno ?? []).map(texto).join(n.todos ? ' Y ' : ' O ')})`
  }
  function textoFinal(n: Condicion): string {
    if (n.entrada) return `${final?.entradas[n.entrada]?.nombre ?? n.entrada}: ${n.conjunto}`
    return `(${(n.todos ?? n.alguno ?? []).map(textoFinal).join(n.todos ? ' Y ' : ' O ')})`
  }
  return <Panel title="Núcleo difuso para autorizar almacenamiento">
    {final && <p className="message">La evaluación final usa un segundo nivel Mamdani con {final.reglas.length} reglas. El núcleo siguiente aporta la conservación; las reglas documentales proporcionan hechos y contexto, sin seleccionar la decisión mediante R30.</p>}
    <p><strong>{Object.keys(nucleo.entradas).length} entradas · {nucleo.reglas.length} reglas Mamdani · una salida conjunta</strong></p>
    <p>En hermético no participa la humedad relativa ambiental. Las reglas documentales se conservan como restricciones, validaciones y contexto.</p>
    <div className="chips">{Object.entries(nucleo.entradas).map(([id, e]) => <span className="chip" key={id}>{e.nombre} · {e.unidad}</span>)}</div>
    <div className="table-scroll"><table><thead><tr><th>Regla</th><th>SI</th><th>ENTONCES</th><th>Modalidad</th></tr></thead><tbody>{nucleo.reglas.map(r => <tr key={r.id}><td>{r.id}</td><td>{texto(r.si)}</td><td>Severidad {r.entonces}</td><td>{r.aplica_si?.igual.replaceAll('_', ' ').toLowerCase() ?? 'Ambas'}</td></tr>)}</tbody></table></div>
    <p className="muted">Las curvas y las interacciones son política del prototipo. El centroide no representa probabilidad de seguridad. Una restricción obligatoria puede impedir la autorización aunque el índice sea bajo.</p>
    {final && <section className="stack"><h3>Decisión final Mamdani · {Object.keys(final.entradas).length} antecedentes · {final.reglas.length} reglas</h3>
      <p>La fase, los hallazgos y la suficiencia de evidencia son antecedentes con pertenencia 0/1. La conservación del primer nivel conserva grados intermedios. Las reglas críticas incluyen exclusiones explícitas de acciones incompatibles.</p>
      <div className="table-scroll"><table><thead><tr><th>Regla</th><th>SI</th><th>ENTONCES</th></tr></thead><tbody>{final.reglas.map(r=><tr key={r.id}><td>{r.id}</td><td>{textoFinal(r.si)}</td><td>{r.entonces.replaceAll('_',' ').toLowerCase()}</td></tr>)}</tbody></table></div>
      <details><summary>Curvas de salida y clasificación</summary><div className="table-scroll"><table><thead><tr><th>Acción</th><th>Trapecio o triángulo</th><th>Centroide menor que</th></tr></thead><tbody>{final.clasificacion.map(c=><tr key={c.decision}><td>{c.decision.replaceAll('_',' ').toLowerCase()}</td><td>{final.salidas[c.decision].join(' · ')}</td><td>{c.hasta}</td></tr>)}</tbody></table></div><p>{final.fundamento}</p></details>
    </section>}
  </Panel>
}
