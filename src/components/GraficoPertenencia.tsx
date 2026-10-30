import { colores, grado, numero, texto, type Entrada } from './conocimiento/difuso'

type Props = {
  nombre: string
  unidad: string
  conjuntos: Entrada['conjuntos']
  dominio: Entrada['dominio']
  valor?: number | null
  rangoCompleto?: boolean
}

/** Representación de las funciones publicadas; el cálculo de la decisión sigue en la API. */
export default function GraficoPertenencia({ nombre, unidad, conjuntos, dominio, valor, rangoCompleto = false }: Props) {
  const curvas = Object.entries(conjuntos).filter((v): v is [string, number[]] => Array.isArray(v[1]))
  if (!curvas.length) return null
  const min = Number(dominio[0]), max = Number(dominio[1])
  const interiores = curvas.flatMap(([, p]) => p).filter(x => x > min && x < max)
  const observado = typeof valor === 'number' && valor >= min && valor <= max ? valor : null
  const a = rangoCompleto ? min : Math.max(min, Math.min(...interiores, observado ?? max) - 5)
  const b = rangoCompleto ? max : Math.min(max, Math.max(...interiores, observado ?? min) + 5)
  const xs = [...new Set([a, b, ...interiores])].sort((x, y) => x - y)
  const px = (x: number) => 48 + (x - a) / (b - a) * 510
  const ticks = Array.from({ length: 6 }, (_, i) => a + (b - a) * i / 5)
  return <div className="membership-chart">
    <svg viewBox="0 0 600 210" role="img" aria-label={`Funciones de pertenencia de ${nombre}`} style={{ width: '100%', display: 'block' }}>
      <title>{`Funciones de pertenencia de ${nombre}`}</title>
      {[0, 0.5, 1].map(y => <g key={y}>
        <line x1="48" x2="558" y1={145 - y * 110} y2={145 - y * 110} stroke="currentColor" opacity=".12" />
        <text x="38" y={149 - y * 110} textAnchor="end" fontSize="12" fill="currentColor">{numero(y)}</text>
      </g>)}
      <text x="10" y="18" fontSize="12" fill="currentColor">μ</text>
      <path d="M48 25V145H558" fill="none" stroke="currentColor" opacity=".35" />
      {curvas.map(([k, p]) => <polyline key={k} points={xs.map(x => `${px(x)},${145 - grado(x, p) * 110}`).join(' ')} fill="none" stroke={colores[k]} strokeWidth="2.5" />)}
      {observado !== null && <line x1={px(observado)} x2={px(observado)} y1="25" y2="145" stroke="#1B3B2B" strokeDasharray="5 4" />}
      {ticks.map((x, i) => <text key={i} x={px(x)} y="167" textAnchor={i === 0 ? 'start' : i === 5 ? 'end' : 'middle'} fontSize="12" fill="currentColor">{numero(x, 1)}</text>)}
      <text x="303" y="195" textAnchor="middle" fontSize="12" fill="currentColor">{nombre} · {unidad}</text>
    </svg>
    <div className="legend" aria-label={`Etiquetas de ${nombre}`}>{curvas.map(([k]) => <span key={k}><i aria-hidden="true" style={{ background: colores[k] }} />{texto(k)}</span>)}{observado !== null && <span>Medición: {numero(observado)} {unidad}</span>}</div>
  </div>
}
