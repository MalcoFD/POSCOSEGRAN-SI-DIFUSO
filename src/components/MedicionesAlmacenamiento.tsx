import { useState } from 'react'
import campos from '../campos.json'
import Captura, { type CapturaDatos } from './Captura'

export const entradasAlmacenamiento = ['humedad_grano', 'temperatura_grano', 'hr_almacen', 'granos_defectuosos']
const procedimiento = ['metodo_humedad', 'temperatura_muestra', 'equipo_humedad_verificado', 'muestra_representativa', 'procedimiento_medicion_cumplido', 'punto_medicion', 'metodo_termico', 'temperatura_almacen']
const anteriores = ['temperatura_grano_previa', 'punto_medicion_previo', 'metodo_termico_previo']
const aireacion = ['temperatura_aire_exterior', 'hr_aire_exterior', 'lluvia_o_niebla', 'humedad_equilibrio_maiz', 'tabla_equilibrio_id']

export default function MedicionesAlmacenamiento({ datos, historicos, onChange, hermetico }: { datos: CapturaDatos; historicos: CapturaDatos; onChange: (datos: CapturaDatos) => void; hermetico: boolean }) {
  const [todo, setTodo] = useState(false)
  const actuales = { ...historicos, ...datos }
  const aw = actuales.aw_medida?.valor === 'true'
  const props = { datos, historicos, onChange }
  return <div className="stack">
    <div className="fuzzy-intro"><p className="eyebrow">Núcleo Mamdani · 9 reglas conjuntas</p><h3>{hermetico ? 'Tres entradas para almacenamiento hermético' : 'Cuatro entradas para evaluar el almacenamiento'}</h3><p>Registra las mediciones reales. El sistema combina sus condiciones y calcula una única severidad para orientar la autorización.</p><p className="muted">{hermetico ? 'La humedad relativa ambiental no representa el interior de un recipiente hermético y queda fuera del núcleo.' : 'Humedad del grano + temperatura del grano + humedad relativa + granos defectuosos.'}</p></div>
    <Captura {...props} filtro={entradasAlmacenamiento.filter(c => !hermetico || c !== 'hr_almacen')} />
    <details className="capture-group" open><summary>Validación de las mediciones y temperatura del almacén</summary><p>Estas comprobaciones respaldan los datos y mantienen las restricciones documentadas. No son entradas adicionales del núcleo difuso.</p><Captura {...props} filtro={procedimiento}/></details>
    {!todo && <details className="capture-group"><summary>Mediciones complementarias según el caso</summary><p>No necesitas inventar mediciones que no realizaste. Los datos pendientes necesarios se indicarán al evaluar.</p>
      <Captura {...props} filtro={['aw_medida']}/>
      {aw && <Captura {...props} filtro={['actividad_agua']}/>}
      <details><summary>Comparación con una lectura térmica anterior</summary><Captura {...props} filtro={anteriores}/></details>
      {!hermetico && <details><summary>Evaluar una posible aireación</summary><Captura {...props} filtro={aireacion}/></details>}
    </details>}
    <label className="check"><input type="checkbox" checked={todo} onChange={e => setTodo(e.target.checked)}/>Mostrar todos los campos complementarios para revisar o corregir</label>
    {todo && <Captura {...props} filtro={Object.keys(campos).filter(c => campos[c as keyof typeof campos].paso === 2 && !entradasAlmacenamiento.includes(c) && !procedimiento.includes(c))}/>}
  </div>
}
