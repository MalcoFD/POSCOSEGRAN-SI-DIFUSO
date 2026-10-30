export type Nodo = { entrada?: string; conjunto?: string; todos?: Nodo[] }
export type Regla = { id: string; si: Nodo; entonces: string; alfa?: number }
export type Entrada = { nombre: string; unidad: string; tipo: 'CONTINUA' | 'CATEGORICA'; dominio: (number | string)[]; conjuntos: Record<string, number[] | { valor: string }>; protocolo?: Record<string, string>; fundamento: string; fuentes: string[] }
export type Matriz = { id: string; nombre: string; entradas: string[]; reglas: Regla[] }
export type Modelo = { estructura: string; entradas: Record<string, Entrada>; matrices: Record<string, Matriz>; salidas: Record<string, number[]>; clasificacion: { hasta: number; conjunto: string; decision: string; recomendacion: string }[]; fundamento: string }
export const numero = (n: number, dec = 3) => n.toLocaleString('es-PE', { maximumFractionDigits: dec })
export const colores: Record<string, string> = { bajo: '#2E7D32', medio: '#9A7319', alto: '#C65C24', muy_alto: '#A1271D', favorable: '#2E7D32', vigilancia: '#7A941F', acondicionamiento: '#C48924', suspension: '#C04B24', separacion: '#7B2030' }
export const texto = (s: string) => s.toLowerCase().replaceAll('_', ' ').replace(/^./, c => c.toUpperCase())
export function grado(x: number, p: number[]) { const [a,b,c,d] = p.length === 3 ? [p[0],p[1],p[1],p[2]] : p; if (x < a || x > d) return 0; if (x >= b && x <= c) return 1; return x < b ? (x-a)/(b-a) : (d-x)/(d-c) }
export function leerModelo(v: Record<string, unknown> | null | undefined): Modelo | null { return v?.estructura === 'MATRICIAL_DIRECTA' ? v as unknown as Modelo : null }
export function antecedente(n: Nodo, entradas: Record<string, { nombre: string }>): string { return n.entrada ? `${entradas[n.entrada]?.nombre ?? n.entrada} es ${texto(n.conjunto ?? '')}` : (n.todos ?? []).map(h => antecedente(h, entradas)).join(' Y ') }
