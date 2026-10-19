import {useState,useCallback,useEffect,useRef} from "react"
import {request} from "../api/client"
export default function useValidacionEnVivo(definicion: Record<string, unknown>) {
  const [errores, setErrores] = useState<string[]>([])
  const [validando, setValidando] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastJson = useRef("")

  const validar = useCallback(async (def: Record<string, unknown>) => {
    const json = JSON.stringify(def)
    if (json === lastJson.current) return
    lastJson.current = json
    setValidando(true)
    try {
      const r = await request<{ valida: boolean; errores: string[] }>("/adquisicion/validar-regla", { method: "POST", body: JSON.stringify({definicion:def}) })
      setErrores(r.errores)
    } catch {
      // La validación en vivo es informativa; no bloquear por errores de red
    } finally {
      setValidando(false)
    }
  }, [])

  useEffect(() => {
    if (timer.current !== null) clearTimeout(timer.current)
    timer.current = setTimeout(() => void validar(definicion), 600)
    return () => {
      if (timer.current !== null) clearTimeout(timer.current)
    }
  }, [definicion, validar])

  return { errores, validando }
}

