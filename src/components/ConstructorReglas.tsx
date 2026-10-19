import camposJson from "../campos.json"
const OPERADORES = ["GT", "GTE", "LT", "LTE", "EQ", "NEQ"] as const
const camposDisponibles = Object.keys(camposJson)
export default function CondicionEditor({
  nodo,
  onChange,
}: {
  nodo: Record<string, unknown>
  onChange: (n: Record<string, unknown>) => void
}) {
  const tipo: string =
    "todos" in nodo
      ? "todos"
      : "alguno" in nodo
        ? "alguno"
        : "dato" in nodo
          ? "dato"
          : "hecho" in nodo
            ? "hecho"
            : "definicion" in nodo
              ? "definicion"
              : "dato"

  return (
    <div className="condicion-editor">
      <div className="condicion-row">
        <select
          value={tipo}
          onChange={(e) => {
            const t = e.target.value
            if (t === "dato")
              onChange({ dato: "", op: "GT", valor: 0 })
            else if (t === "hecho") onChange({ hecho: "" })
            else if (t === "definicion") onChange({ definicion: "" })
            else if (t === "todos" || t === "alguno")
              onChange({ [t]: [{ dato: "", op: "GT", valor: 0 }] })
          }}
        >
          <option value="dato">Campo (dato)</option>
          <option value="hecho">Hecho inferido</option>
          <option value="definicion">Definición</option>
          <option value="todos">Todos (AND)</option>
          <option value="alguno">Alguno (OR)</option>
        </select>
      </div>
      {tipo === "dato" && (
        <div className="condicion-row">
          <select
            value={String(nodo.dato || "")}
            onChange={(e) => onChange({ ...nodo, dato: e.target.value })}
          >
            <option value="">Seleccionar campo</option>
            {camposDisponibles.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            value={String(nodo.op || "GT")}
            onChange={(e) => onChange({ ...nodo, op: e.target.value })}
          >
            {OPERADORES.map((o) => (
              <option key={o} value={o}>
                {o === "GT"
                  ? ">"
                  : o === "GTE"
                    ? "≥"
                    : o === "LT"
                      ? "<"
                      : o === "LTE"
                        ? "≤"
                        : o === "EQ"
                          ? "="
                          : "≠"}
              </option>
            ))}
          </select>
          <input
            type="text"
            inputMode="decimal"
            value={String(nodo.valor ?? "")}
            placeholder="Valor / umbral"
            onChange={(e) => {
              const v = e.target.value
              const num = Number(v.replace(",", "."))
              onChange({
                ...nodo,
                valor: v === "" ? "" : Number.isFinite(num) ? num : v,
              })
            }}
          />
        </div>
      )}
      {tipo === "hecho" && (
        <input
          type="text"
          value={String(nodo.hecho || "")}
          placeholder="Nombre del hecho"
          onChange={(e) => onChange({ hecho: e.target.value })}
        />
      )}
      {tipo === "definicion" && (
        <input
          type="text"
          value={String(nodo.definicion || "")}
          placeholder="Nombre de la definición"
          onChange={(e) => onChange({ definicion: e.target.value })}
        />
      )}
      {(tipo === "todos" || tipo === "alguno") && (
        <div className="condicion-hijos">
          {(Array.isArray(nodo[tipo]) ? (nodo[tipo] as Record<string, unknown>[]) : []).map(
            (hijo, i) => (
              <div key={i} className="condicion-hijo">
                <CondicionEditor
                  nodo={hijo}
                  onChange={(updated) => {
                    const lista = [
                      ...(nodo[tipo] as Record<string, unknown>[]),
                    ]
                    lista[i] = updated
                    onChange({ [tipo]: lista })
                  }}
                />
                <button
                  type="button"
                  className="chip-btn danger"
                  onClick={() => {
                    const lista = (
                      nodo[tipo] as Record<string, unknown>[]
                    ).filter((_, j) => j !== i)
                    onChange({ [tipo]: lista.length ? lista : [{ dato: "", op: "GT", valor: 0 }] })
                  }}
                >
                  ✕
                </button>
              </div>
            )
          )}
          <button
            type="button"
            className="chip-btn"
            onClick={() =>
              onChange({
                [tipo]: [
                  ...(nodo[tipo] as Record<string, unknown>[]),
                  { dato: "", op: "GT", valor: 0 },
                ],
              })
            }
          >
            + Añadir condición
          </button>
        </div>
      )}
    </div>
  )
}

