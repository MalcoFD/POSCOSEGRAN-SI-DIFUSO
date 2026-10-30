import { test, expect, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
const password = readFileSync('backend/.env','utf8').match(/^POSCOSEGRAN_AUTH_LOCAL_PASSWORD=(.+)$/m)![1].trim()
const casos = JSON.parse(readFileSync('knowledge/corridas_4.json','utf8')) as {id:string;modalidad:string;valores:Record<string,string|number>;centroide:number;decision:string}[]
async function login(page:Page) {
  await page.goto('/')
  await page.getByLabel('Usuario local').fill('productor')
  await page.getByLabel('Contraseña',{exact:true}).fill(password)
  await page.getByRole('button',{name:'Entrar',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Inicio',exact:true})).toBeVisible()
}
for (const caso of casos) test(`matriz ${caso.id}: captura completa, cálculo e historial`,async ({page}) => {
  const errores:string[]=[]
  page.on('pageerror',e=>errores.push(e.message))
  await login(page)
  await page.getByRole('button',{name:'Registrar unidad',exact:true}).click()
  const suffix=caso.id+'-'+Date.now()
  await page.getByLabel('Nombre del almacén',{exact:true}).fill('Almacén E2E '+suffix)
  await page.getByLabel('Ubicación',{exact:true}).fill('Cusco, simulación')
  await page.getByRole('button',{name:'Guardar almacén',exact:true}).click()
  await expect(page.getByLabel('Almacén',{exact:true})).not.toHaveValue('')
  await page.getByLabel('Código del lote',{exact:true}).fill('E2E-'+suffix)
  await page.getByRole('button',{name:'Guardar lote',exact:true}).click()
  await expect(page.getByLabel('Lote',{exact:true})).not.toHaveValue('')
  await page.getByLabel('Nombre del recipiente',{exact:true}).fill('Unidad E2E '+suffix)
  await page.getByLabel('Modalidad',{exact:true}).selectOption(caso.modalidad)
  await page.getByRole('button',{name:'Crear unidad y capturar'}).click()
  await expect(page.getByRole('heading',{name:'Evaluar unidad',exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Siguiente',exact:true}).click()
  for (const [campo,label] of [['humedad_grano','Humedad del grano'],['temperatura_grano','Temperatura del grano'],['hr_almacen','Humedad relativa del almacén']]) {
    if (!(campo in caso.valores)) continue
    await page.getByLabel(new RegExp('^'+label+' ·')).fill(String(caso.valores[campo]))
    await page.getByLabel('Método · '+label,{exact:true}).fill('INSTRUMENTAL')
    await page.getByLabel('Evidencia · '+label,{exact:true}).fill('Medición de muestra representativa, simulación E2E')
  }
  if (caso.id==='M320-L02') {
    await page.getByRole('button',{name:'Guardar borrador',exact:true}).click()
    await expect(page.getByRole('status')).toContainText('Borrador guardado')
    await page.evaluate(()=>Object.keys(sessionStorage).filter(k=>k.startsWith('captura:')).forEach(k=>sessionStorage.removeItem(k)))
    await page.reload()
    await expect(page.getByRole('status')).toContainText('Borrador recuperado')
    await page.getByRole('button',{name:/Mediciones/}).click()
    await expect(page.getByLabel(/^Temperatura del grano ·/)).toHaveValue('18')
  }
  await page.getByRole('button',{name:'Siguiente',exact:true}).click()
  await page.getByLabel('Estado físico y sanitario del grano',{exact:true}).selectOption(String(caso.valores.estado_fisico_sanitario))
  await page.getByLabel('Evidencia · Estado físico y sanitario del grano',{exact:true}).fill(caso.id==='M320-L04'?'Moho visible en muestra, escenario simulado':'Muestra inspeccionada sin hallazgos, escenario simulado')
  if (caso.modalidad==='HERMETICO') {
    await page.getByLabel('Integridad de la barrera hermética',{exact:true}).selectOption('INTEGRA')
    await page.getByLabel('Evidencia · Integridad de la barrera hermética',{exact:true}).fill('Barrera y cierre verificados, simulación')
    await page.getByLabel('Procedimiento de observación interna',{exact:true}).selectOption('INSPECCION_PREVIA_SELLADO')
    await page.getByLabel('Evidencia · Procedimiento de observación interna',{exact:true}).fill('Muestra inspeccionada antes del sellado, simulación')
  }
  await page.getByRole('button',{name:'Calcular y registrar evaluación'}).click()
  await expect(page.getByRole('heading',{name:'Resultado de evaluación',exact:true})).toBeVisible()
  await expect(page.getByText(caso.centroide.toLocaleString('es-PE',{maximumFractionDigits:3})+' / 100',{exact:true})).toBeVisible()
  await expect(page.getByRole('heading',{name:'Cálculo Mamdani de la evaluación'})).toBeVisible()
  await page.screenshot({path:`test-results/${caso.id}-desktop.png`,fullPage:true})
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy()
  await page.screenshot({path:`test-results/${caso.id}-mobile.png`,fullPage:true})
  await page.getByRole('button',{name:'Ver seguimiento',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Seguimiento',exact:true})).toBeVisible()
  await page.getByRole('tab',{name:/Evaluaciones/}).click()
  await expect(page.getByRole('button',{name:'Ver explicación',exact:true})).toBeVisible()
  if (caso.id==='M320-L04') {
    await page.getByRole('button',{name:'Registrar admisión',exact:true}).click()
    await expect(page.getByRole('button',{name:'Guardar actuación',exact:true})).toBeDisabled()
  }
  expect(errores).toEqual([])
})
