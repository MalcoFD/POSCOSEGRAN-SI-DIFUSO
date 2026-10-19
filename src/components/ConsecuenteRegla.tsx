import {Field} from "./Shared"
import {nombre} from "../api/client"
const SOLICITUDES = ["CUARENTENA", "SUSPENSION", "CORRECCION", "MONITOREO"] as const
export default function ConsecuenteEditor({
  entonces,
  onChange,
}: {
  entonces: Record<string, unknown>
  onChange: (e: Record<string, unknown>) => void
}) {
  const solicitudes = Array.isArray(entonces.solicitudes)
    ? (entonces.solicitudes as string[])
    : []
  return (
    <div className="consecuente-editor">
      <Field label="Hallazgo (hecho deducido)">
        <input
          type="text"
          value={String(entonces.hallazgo || "")}
          placeholder="Ej: INFRAESTRUCTURA_CON_FILTRACION"
          onChange={(e) =>
            onChange({ ...entonces, hallazgo: e.target.value })
          }
        />
      </Field>
      <Field label="Solicitudes de acción">
        <div className="check-group">
          {SOLICITUDES.map((s) => (
            <label key={s} className="check">
              <input
                type="checkbox"
                checked={solicitudes.includes(s)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...solicitudes, s]
                    : solicitudes.filter((x) => x !== s)
                  onChange({ ...entonces, solicitudes: next })
                }}
              />
              {nombre(s)}
            </label>
          ))}
        </div>
      </Field>
      <Field label="Mensaje explicativo">
        <textarea
          value={String(entonces.mensaje || "")}
          placeholder="Texto que verá el usuario en el módulo de explicación"
          onChange={(e) =>
            onChange({ ...entonces, mensaje: e.target.value })
          }
        />
      </Field>
    </div>
  )
}

