/** Utilidades de presentación del modelo Mamdani publicado por /conocimiento.
 *  Reproducen la definición de la base para explicarla; la decisión real la calcula el servidor. */

export type Condicion = { entrada?: string; conjunto?: string; todos?: Condicion[]; alguno?: Condicion[] }
export type EntradaNucleo = { id?: string; nombre: string; unidad: string; dominio: number[]; conjuntos: Record<string, number[]>; referencia?: number; aplica_si?: { contexto: string; igual: string } }
export type ReglaNucleo = { id: string; si: Condicion; entonces: string; aplica_si?: { contexto: string; igual: string } }
export type Nucleo = { id: string; nombre: string; origenes?: string[]; entradas: Record<string, EntradaNucleo>; reglas: ReglaNucleo[] }
export type EntradaFinal = { nombre: string; conjuntos?: Record<string, number[]> | string[]; modulo?: string; contexto?: string; certeza_conjunto?: string }
export type Final = { entradas: Record<string, EntradaFinal>; reglas: { id: string; si: Condicion; entonces: string }[]; salidas: Record<string, number[]>; clasificacion: { hasta: number; decision: string }[]; fundamento: string }
export type Modelo = { tipo: string; estructura: string; operadores: Record<string, string>; salidas: Record<string, number[]>; modulos: Nucleo[]; decision?: Final; politica?: Record<string, unknown> }

export const NIVELES = ['bajo', 'medio', 'alto'] as const
export const COLOR_NIVEL: Record<string, string> = { bajo: '#2E7D32', medio: '#C48924', alto: '#B3261E' }

export function leerModelo(modelo: Record<string, unknown> | null | undefined): Modelo | null {
  if (!modelo || modelo.estructura !== 'MULTIVARIABLE' || !Array.isArray(modelo.modulos) || !modelo.modulos.length) return null
  return modelo as unknown as Modelo
}

/** Grado de pertenencia trapezoidal (4 puntos) o triangular (3 puntos). */
export function grado(x: number, p: number[]) {
  const [a, b, c, d] = p.length === 3 ? [p[0], p[1], p[1], p[2]] : p
  if (x < a || x > d) return 0
  if (x >= b && x <= c) return 1
  return x < b ? (x - a) / (b - a) : (d - x) / (d - c)
}

export const forma = (p: number[]) => p.length === 3 ? 'trimf' : 'trapmf'

/** AND = mínimo, OR = máximo sobre los grados de cada entrada. */
export function evaluar(c: Condicion, mu: (entrada: string, conjunto: string) => number): number {
  if (c.entrada) return mu(c.entrada, c.conjunto ?? '')
  if (c.todos) return Math.min(...c.todos.map(h => evaluar(h, mu)))
  if (c.alguno) return Math.max(...c.alguno.map(h => evaluar(h, mu)))
  return 0
}

/** Agregación por máximo de consecuentes recortados (implicación mínimo) y centroide numérico. */
export function agregar(salidas: Record<string, number[]>, alfas: Record<string, number>, [z0, z1] = [0, 100], pasos = 2000) {
  const curva: [number, number][] = []
  let num = 0, den = 0
  for (let i = 0; i <= pasos; i++) {
    const z = z0 + ((z1 - z0) * i) / pasos
    const m = Math.max(0, ...Object.entries(salidas).map(([k, p]) => Math.min(alfas[k] ?? 0, grado(z, p))))
    curva.push([z, m]); num += z * m; den += m
  }
  return { curva, centroide: den > 0 ? num / den : null }
}

/** Ventana visible alrededor de las transiciones de una variable. */
export function ventana(e: EntradaNucleo): [number, number] {
  const puntos = Object.values(e.conjuntos).flat().filter(x => x > e.dominio[0] && x < e.dominio[1])
  if (!puntos.length) return [e.dominio[0], e.dominio[1]]
  const a = Math.min(...puntos), b = Math.max(...puntos), margen = Math.max((b - a) * 0.8, 0.5)
  return [Math.max(e.dominio[0], a - margen), Math.min(e.dominio[1], b + margen)]
}

export const numero = (n: number, dec = 2) => n.toLocaleString('es-PE', { minimumFractionDigits: dec, maximumFractionDigits: dec })
export const lista = (p: number[]) => p.map(x => String(x)).join(', ')

/** Antecedente en notación lógica: ∧ para todos, ∨ para alguno. */
export function formula(c: Condicion, nombreEntrada: (id: string) => string = id => id, binaria = false, raiz = true): string {
  if (c.entrada) {
    if (binaria && c.conjunto === 'presente') return nombreEntrada(c.entrada)
    if (binaria && c.conjunto === 'ausente') return `¬${nombreEntrada(c.entrada)}`
    return `${nombreEntrada(c.entrada)} ES ${c.conjunto}`
  }
  // Las anclas YAML anidan "todos" dentro de "todos": se aplanan y se quitan repeticiones.
  const planos = c.todos ? c.todos.flatMap(function aplanar(h: Condicion): Condicion[] { return h.todos ? h.todos.flatMap(aplanar) : [h] })
    : (c.alguno ?? []).flatMap(function aplanar(h: Condicion): Condicion[] { return h.alguno ? h.alguno.flatMap(aplanar) : [h] })
  const hijos = [...new Set(planos.map(h => formula(h, nombreEntrada, binaria, false)))]
  const texto = hijos.join(c.todos ? ' ∧ ' : ' ∨ ')
  return raiz || hijos.length < 2 ? texto : `(${texto})`
}
