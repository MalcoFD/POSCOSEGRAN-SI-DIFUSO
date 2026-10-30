import { Field } from './Shared'
import { ahoraLocal, vacio, type CapturaDatos, type CapturaValor } from './Captura'
const opciones: Record<string, Record<string, string>> = {
  estado_fisico_sanitario: { SIN_HALLAZGOS: 'Sin hallazgos', DANO_FISICO: 'Daño físico', INDICIOS_BIOLOGICOS: 'Indicios biológicos', HALLAZGO_CRITICO: 'Hallazgo crítico: moho o insectos vivos' },
  estado_barrera: { INTEGRA: 'Barrera y cierre íntegros, verificados', NO_INTEGRA: 'Barrera o cierre no íntegros', NO_VERIFICADA: 'Integridad no verificada' },
  procedimiento_interno: { SENSOR_INTERNO: 'Sensor interno e inspección representativa documentada', INSPECCION_PREVIA_SELLADO: 'Medición e inspección previas al sellado vigente' },
}
const labels: Record<string,string> = { estado_fisico_sanitario: 'Estado físico y sanitario del grano', estado_barrera: 'Integridad de la barrera hermética', procedimiento_interno: 'Procedimiento de observación interna' }
export default function InspeccionMatricial({ datos, historicos, onChange, hermetico }: { datos: CapturaDatos; historicos: CapturaDatos; onChange: (d: CapturaDatos) => void; hermetico: boolean }) {
  const campos = ['estado_fisico_sanitario', ...(hermetico ? ['estado_barrera', 'procedimiento_interno'] : [])]
  return <div className="stack"><p>Inspecciona una muestra representativa y selecciona el estado de mayor severidad observado: hallazgo crítico, indicios biológicos, daño físico o sin hallazgos. Sin hallazgos exige haber realizado la inspección. Los indicios no confirman infestación; moho visible o insectos vivos corresponden a hallazgo crítico.</p>
    {hermetico && <p>La HR ambiental queda excluida. Documenta la barrera íntegra y el procedimiento interno; no abras el recipiente únicamente para completar una casilla.</p>}
    {campos.map(c => {
      const v = datos[c] ?? historicos[c] ?? { ...vacio(), fecha: ahoraLocal(), metodo: 'INSPECCION' }
      const cambiar = (patch: Partial<CapturaValor>) => onChange({ ...datos, [c]: { ...v, ...patch } })
      return <section className="capture-field" key={c}><h3>{labels[c]}</h3>
        {!datos[c] && historicos[c] && <p className="muted">Observación anterior: {v.fecha.replace('T', ' ')}. Revisa su vigencia antes de reutilizarla.</p>}
        <Field label={labels[c]}><select value={v.valor} onChange={e => cambiar({ valor: e.target.value, captura: e.target.value ? 'APORTADO' : 'DESCONOCIDO' })}><option value="">Sin observación</option>{Object.entries(opciones[c]).map(([k,l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <div className="form-grid"><Field label={`Fecha · ${labels[c]}`}><input type="datetime-local" value={v.fecha} onChange={e => cambiar({ fecha: e.target.value })} /></Field><Field label={`Método · ${labels[c]}`}><input value={v.metodo} onChange={e => cambiar({ metodo: e.target.value })} /></Field></div>
        <Field label={`Evidencia · ${labels[c]}`} hint="Muestra, procedimiento, hallazgos y responsable. Obligatoria para calcular."><textarea rows={3} value={v.evidencia} onChange={e => cambiar({ evidencia: e.target.value })} /></Field>
      </section>
    })}</div>
}
