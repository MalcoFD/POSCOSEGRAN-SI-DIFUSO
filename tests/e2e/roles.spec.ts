import { test, expect, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'

const password = process.env.POSCOSEGRAN_AUTH_LOCAL_PASSWORD || readFileSync('backend/.env', 'utf8').match(/^POSCOSEGRAN_AUTH_LOCAL_PASSWORD=(.+)$/m)![1].trim()

async function entrar(page: Page, usuario: string) {
  await page.goto('/')
  await page.getByLabel('Usuario local').fill(usuario)
  await page.getByLabel('Contraseña', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Entrar', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Inicio', exact: true })).toBeVisible()
}

function cabeceras(page: Page) {
  return page.evaluate(() => ({ Authorization: `Bearer ${(JSON.parse(sessionStorage.getItem('poscosegran-session')!) as {access_token:string}).access_token}` }))
}

test('administrador asigna, técnico inspecciona, ingeniero revisa el Mamdani final', async ({ page }) => {
  const errores: string[] = []
  page.on('pageerror', e => errores.push(e.message))
  await entrar(page, 'administrador')
  await expect(page.getByRole('button', { name: 'Evaluaciones', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Configuración', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Configuración' })).toBeVisible()
  const headersAdmin = await cabeceras(page)
  const listado = await page.request.get('/api/v1/administracion/asignaciones', { headers: headersAdmin })
  expect(listado.status()).toBe(200)
  const recursos = (await listado.json()) as { recursos: { id:string;nombre:string;tipo:string }[] }
  const almacen = recursos.recursos.find(r => r.tipo === 'ALMACEN' && r.nombre.startsWith('Almacén E2E '))
  expect(almacen).toBeTruthy()
  const directo = await page.request.get('/api/v1/unidades', { headers: headersAdmin })
  expect(directo.status()).toBe(200)
  expect((await directo.json()).items).toEqual([])
  await page.getByLabel('Técnico a asignar').selectOption({ index: 1 })
  await page.getByLabel('Recurso a asignar').selectOption(`ALMACEN:${almacen!.id}`)
  await page.getByRole('button', { name: 'Guardar asignación' }).click()
  await expect(page.getByRole('row').filter({hasText:almacen!.nombre}).first()).toContainText('Vigente')

  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await entrar(page, 'tecnico')
  await expect(page.getByRole('button', { name: 'Revisión técnica', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Almacenes y lotes', exact: true }).click()
  const fila = page.getByRole('row').filter({hasText:almacen!.nombre}).first()
  await fila.getByRole('button', { name: 'Ver detalle' }).click()
  await expect(page.getByRole('heading', {name:'Inspección compartida del almacén'})).toBeVisible()
  await page.getByRole('button', {name:'Registrar inspección del almacén'}).click()
  await page.getByLabel('Evidencia de inspección del almacén').fill('Acta de inspección E2E')
  await page.getByLabel('Filtraciones de agua en el almacén', {exact:true}).selectOption('false')
  await page.getByLabel('Método · Filtraciones de agua en el almacén', {exact:true}).fill('Inspección de techo E2E')
  await page.getByRole('button', {name:'Guardar inspección compartida'}).click()
  await expect(page.getByText('Acta de inspección E2E')).toBeVisible()
  await page.getByRole('button', { name: 'Cerrar sesión' }).click()

  await entrar(page, 'ingeniero')
  await expect(page.getByRole('button', { name: 'Evaluaciones', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Adquisición', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Base de Conocimiento', exact: true }).click()
  await page.getByRole('tab', { name: 'Vista técnica' }).click()
  await expect(page.getByRole('heading', {name:'Decisión final Mamdani · 11 antecedentes · 14 reglas'})).toBeVisible()
  const final = page.getByRole('heading', {name:'Decisión final Mamdani · 11 antecedentes · 14 reglas'}).locator('..')
  await expect(final.locator('table').first().locator('tbody tr')).toHaveCount(14)
  await expect(final).toContainText('MF14')
  expect(errores).toEqual([])
})
