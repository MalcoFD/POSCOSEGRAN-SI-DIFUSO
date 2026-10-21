import { useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { nombre, request, type Schema } from '../api/client'
import Panel, { Empty, ErrorMessage, PageHeader, SkeletonPage } from '../components/Shared'
import { IconCode, IconHelp, IconSearch } from '../components/Icons'
import { Source } from './Resultado'
import ModeloAlmacenamiento from '../components/ModeloAlmacenamiento'
import Guiado from '../components/conocimiento/Guiado'
import Tecnico from '../components/conocimiento/Tecnico'
import { leerModelo } from '../components/conocimiento/difuso'

type Modo = 'guiada' | 'tecnica'
const CLAVE = 'poscosegran:conocimiento:modo'
function modoInicial(): Modo {
  try { return localStorage.getItem(CLAVE) === 'tecnica' ? 'tecnica' : 'guiada' } catch { return 'guiada' }
}

export default function Conocimiento() {
  const [q, setQ] = useState('')
  const [modo, setModoEstado] = useState<Modo>(modoInicial)
  const idBuscar = useId()
  const data = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  function setModo(m: Modo) { setModoEstado(m); try { localStorage.setItem(CLAVE, m) } catch { /* Preferencia opcional. */ } }
  if (data.isLoading) return <SkeletonPage label="Cargando la base de conocimiento…" />
  const modelo = leerModelo(data.data?.modelo_difuso)
  const vista: Modo = modelo ? modo : 'tecnica'
  const texto = q.toLowerCase()
  const reglas = data.data ? [...data.data.reglas, ...data.data.ramas_r30].filter(r => JSON.stringify(r).toLowerCase().includes(texto)) : []
  return <div className="stack">
    <PageHeader eyebrow={`Conocimiento documentado · Base ${data.data?.version_base ?? '—'} · parámetros ${data.data?.version_parametros ?? '—'}`} title="Base de conocimiento"
      description={`${modelo ? 'Sistema difuso Mamdani. ' : 'Sistema experto histórico. '}El motor no contiene umbrales ni reglas: los lee de esta base. Lo que ves aquí es exactamente lo que se aplica.`}
      actions={modelo && <div className="segmented" role="tablist" aria-label="Modo de lectura">
        <button role="tab" aria-selected={vista === 'guiada'} onClick={() => setModo('guiada')}><IconHelp size={16} />Vista guiada</button>
        <button role="tab" aria-selected={vista === 'tecnica'} onClick={() => setModo('tecnica')}><IconCode size={16} />Vista técnica</button>
      </div>} />
    <ErrorMessage error={data.error} onRetry={() => void data.refetch()} />

    {modelo && vista === 'guiada' && <Guiado modelo={modelo} />}

    {vista === 'tecnica' && <>
      {modelo && <Tecnico modelo={modelo} />}
      <ModeloAlmacenamiento modelo={data.data?.modelo_difuso} />
      {data.data && <>
        <Panel title={`Catálogo documental R01–R${String(data.data.reglas.length).padStart(2, '0')}`}>
          <div className="field" style={{ marginBottom: 12 }}><label htmlFor={idBuscar}>Buscar regla o término</label>
            <div className="search-box"><IconSearch size={16} /><input id={idBuscar} type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Ej. R19, humedad, cuarentena" /></div>
          </div>
          {reglas.length ? reglas.map(r => <details className="reason" key={r.id}><summary><span className="badge code">{r.id}</span> {r.consecuente}</summary>
            <div className="form-grid" style={{ marginTop: 8 }}><div><span className="muted" style={{ fontSize: 13 }}>Condición</span><p className="mono" style={{ margin: '2px 0 0', fontSize: 13 }}>{r.antecedente}</p></div><div><span className="muted" style={{ fontSize: 13 }}>Acción</span><p style={{ margin: '2px 0 0' }}>{r.accion}</p></div></div>
            <Source text={r.fundamento_markdown} /></details>)
            : <Empty title="Sin coincidencias" icon={<IconSearch size={26} />}>Prueba con otro código de regla o término.</Empty>}
        </Panel>
        <Panel title="Parámetros vigentes">{data.data.parametros?.length ? <div className="table-scroll"><table><thead><tr><th>Parámetro</th><th>Valor</th><th>Fundamento</th><th>Fuentes</th></tr></thead><tbody>{data.data.parametros.filter(p => JSON.stringify(p).toLowerCase().includes(texto)).map(p => <tr key={p.nombre}><td>{p.descripcion}<small className="mono">{p.nombre}</small></td><td className="mono-cell">{p.valor} {p.unidad}</td><td><span className="badge">{nombre(p.fundamento)}</span></td><td>{p.fuentes.join(', ') || '—'}</td></tr>)}</tbody></table></div> : <p className="muted">La versión activa no expone parámetros.</p>}</Panel>
        <Panel title="Fuentes">{data.data.fuentes.map(f => <div className="reason" key={f.id}><span className="badge code">{f.id}</span><Source text={f.referencia_markdown} /></div>)}</Panel>
      </>}
    </>}
  </div>
}
