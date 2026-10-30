"""Registra las cuatro corridas simuladas mediante HTTP y comprueba su persistencia.

Requiere la API local en ejecución. No borra ni modifica evaluaciones anteriores.
Los códigos M320-L01 a M320-L04 identifican las unidades de demostración.
"""
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / 'backend/.env')


def main():
    casos = json.loads((ROOT / 'knowledge/corridas_4.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=60) as c:
        r = c.post('/auth/local/sesion', json={'usuario': 'productor', 'password': os.environ['POSCOSEGRAN_AUTH_LOCAL_PASSWORD']})
        r.raise_for_status()
        c.headers['Authorization'] = 'Bearer '+r.json()['access_token']

        def get(path):
            r = c.get('/api/v1'+path)
            r.raise_for_status()
            return r.json()

        def post(path, body, key=None):
            r = c.post('/api/v1'+path, json=body, headers={'Idempotency-Key': key or str(uuid.uuid4())})
            if r.status_code != 201:
                raise RuntimeError(f'{path}: {r.status_code}: {r.text}')
            return r.json()

        almacen = next((a for a in get('/almacenes?limite=100')['items'] if a['nombre']=='Almacén demostrativo Mamdani 320'), None)
        if almacen is None:
            almacen = post('/almacenes', {'nombre': 'Almacén demostrativo Mamdani 320', 'ubicacion':'Cusco, escenario académico simulado', 'clima_calido':False, 'fundamento_clima':'Contexto de demostración; no constituye caracterización climática de campo.'})
        lotes = get('/lotes?limite=100')['items']
        unidades = get('/unidades?limite=100')['items']
        evidencia = []
        for caso in casos:
            lote = next((fila for fila in lotes if fila['codigo']==caso['id']), None)
            if lote is None:
                lote = post('/lotes', {'codigo':caso['id'], 'variedad':'MAIZ_CHULPI','uso_final':'ALIMENTACION'})
            u = next((u for u in unidades if u['id_lote']==lote['id']), None)
            if u is None:
                u = post('/unidades', {'id_lote':lote['id'],'id_almacen':almacen['id'],'nombre_recipiente':caso['id']+' '+caso['titulo'], 'tipo_almacenamiento':caso['modalidad']})
            historial = get('/unidades/'+u['id']+'/historial')['items']
            if historial:
                resultado = historial[0]
            else:
                ahora = datetime.now(UTC)-timedelta(seconds=2)
                valores = dict(caso['valores'])
                if caso['modalidad']=='HERMETICO':
                    valores.update(estado_barrera='INTEGRA', procedimiento_interno='INSPECCION_PREVIA_SELLADO')
                observaciones = [{'campo':k,'valor':v,'captura':'APORTADO',
                    'unidad':'TEXTO' if isinstance(v,str) else 'PCT_BH' if k=='humedad_grano' else 'PCT_HR' if k=='hr_almacen' else 'CELSIUS',
                    'fecha_observacion':ahora.isoformat(),'metodo':'INSPECCION' if isinstance(v,str) else 'INSTRUMENTAL',
                    'valor_original':str(v),'evidencia':f'CORRIDA SIMULADA {caso["id"]}. Muestra representativa declarada para prueba de software. '+('Moho visible observado en el escenario.' if v=='HALLAZGO_CRITICO' else 'Sin hallazgos críticos en este registro de prueba.'), 'motivo_no_aplica':None} for k,v in valores.items()]
                body={'revision_unidad':u['revision'],'revision_almacen':u['revision_almacen'],'fase':'INGRESO','observaciones':observaciones,
                      'historial':{'fecha_inicio_historial':None,'vida_previa_documentada':None,'evidencia_vida_previa':None,'intervalos_historial':[]},'dias_previstos_restantes':None,'fecha_salida_prevista':None}
                key=str(uuid.uuid4())
                resultado=post('/unidades/'+u['id']+'/evaluaciones',body,key)
                assert post('/unidades/'+u['id']+'/evaluaciones',body,key)==resultado
            e=resultado['evaluacion']
            assert e['decision_final']==caso['decision']
            assert abs(e['difuso']['decision']['centroide']-caso['centroide'])<1e-6
            assert get('/evaluaciones/'+e['id']+'/explicacion')['difuso']==e['difuso']
            evidencia.append({'codigo':caso['id'],'titulo':caso['titulo'],'id_lote':lote['id'],'id_unidad':u['id'],'id_evaluacion':e['id'],
                'fecha_evaluacion':e['fecha_evaluacion'],'decision':e['decision_final'],'centroide':e['difuso']['decision']['centroide'],
                'reglas_activadas':e['reglas_activadas'],'version_base':e['version_base'],'version_parametros':e['version_parametros'],
                'version_motor':e['version_motor'],'vigencia_al_registrar':resultado['vigencia']['estado'], 'valores':caso['valores']})
    engine=create_engine(os.environ['POSCOSEGRAN_BD_URL_APP'])
    with engine.connect() as db:
        ids=[uuid.UUID(x['id_evaluacion']) for x in evidencia]
        n=db.scalar(text('SELECT count(*) FROM poscosegran.evaluacion WHERE id = ANY(:ids)'),{'ids':ids})
        assert n==4
        for ev in evidencia:
            ev['evaluaciones_en_historial']=db.scalar(text('SELECT count(*) FROM poscosegran.evaluacion WHERE id_unidad=:id'), {'id':uuid.UUID(ev['id_unidad'])})
            ev['incidencias_abiertas']=db.scalar(text("SELECT count(*) FROM poscosegran.incidencia WHERE id_unidad=:id AND estado='ABIERTA'"), {'id':uuid.UUID(ev['id_unidad'])})
        auditorias=db.scalar(text("SELECT count(*) FROM poscosegran.auditoria WHERE recurso_tipo='evaluacion' AND recurso_id=ANY(:ids)"),{'ids':ids})
        assert auditorias == 4
    salida={'fecha_verificacion':datetime.now(UTC).isoformat(),'entorno':'PostgreSQL local; datos simulados', 'cuatro_evaluaciones_comprobadas':n,'auditorias_evaluacion':auditorias,'corridas':evidencia}
    (ROOT/'docs/EVIDENCIA_CORRIDAS_4.json').write_text(json.dumps(salida,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(salida,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
