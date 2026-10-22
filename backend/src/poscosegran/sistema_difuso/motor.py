"""Mamdani integrado en la agenda: núcleo de conservación y decisión final.

Las reglas documentales encadenan hechos y solicitudes. En su etapa, el núcleo
multivariable fuzzifica las mediciones y calcula el centroide de conservación;
tras el punto fijo, la decisión final se infiere con las reglas MF01–MF14.
"""
from collections.abc import Mapping
from typing import Any

from ..dominio.hechos import Accion, Motivo, Pendiente
from ..dominio.valores import F, V, Tri
from ..inferencia.base_hechos import BaseHechos
from ..inferencia.lenguaje import Evaluador
from ..inferencia.motor import Motor
from .defuzzificacion import centroide
from .pertenencia import pertenencia
from .reglas import activacion, referencias

VERSION_MOTOR = '3.0.0-mamdani'


class EvaluadorDifuso(Evaluador):
    def definicion(self, nombre: str) -> Tri:
        resultado = super().definicion(nombre)
        if nombre == 'riesgo_activo' and resultado is F and self.hechos.difuso:
            if any(m.get('solicitud') for m in self.hechos.difuso['modulos']):
                return V
        return resultado


class MotorDifuso(Motor):
    version = VERSION_MOTOR

    def crear_evaluador(self, hechos: BaseHechos) -> Evaluador:
        return EvaluadorDifuso(self.base, hechos, calculadora=None)

    def completar_etapa(self, etapa: str, hechos: BaseHechos, evaluador: Evaluador) -> None:
        modelo = self.base.contenido['operativa']['difuso']
        if hechos.difuso is None:
            hechos.difuso = {
                'tipo': modelo['tipo'], 'version': self.version, 'operadores': modelo['operadores'],
                'politica': modelo['politica'], 'modulos': [],
                'nota': 'Índices del prototipo, no probabilidades ni certificación de inocuidad.',
            }
        for modulo in modelo['modulos']:
            if modulo.get('etapa', 'encadenamiento') == etapa:
                hechos.difuso['modulos'].append(self._conjunto(modulo, modelo, hechos, evaluador))

    def _resolver(self, hechos: BaseHechos, evaluador: Evaluador) -> str:
        from .decision import inferir
        informe = inferir(self.base.contenido['operativa']['difuso']['decision'], hechos, evaluador)
        assert hechos.difuso is not None
        hechos.difuso['decision'] = informe
        decision: str = informe['decision']
        mensaje = f"Decisión Mamdani {decision}: centroide final {informe['centroide']:.3f}; clasificación de la salida agregada."
        hechos.motivos.append(Motivo(id='R30:MAMDANI_FINAL', regla='R30', mensaje=mensaje,
                                     fuentes=self.base.fuentes_de('R30'), fundamento='POLITICA_PROTOTIPO'))
        if decision in {'CORREGIR_Y_REEVALUAR', 'AUTORIZAR_CON_MONITOREO'}:
            hechos.acciones.append(Accion(codigo='CORREGIR' if decision == 'CORREGIR_Y_REEVALUAR' else 'MONITOREAR',
                                          descripcion=mensaje, responsable_requerido='PRODUCTOR'))
        # El plan y el control responden a la decisión ya inferida; no la eligen.
        if decision == 'AUTORIZAR_CON_MONITOREO':
            hechos.solicitar('MONITOREO', 'R30')
        return decision

    def _entrada(self, entrada: Mapping[str, Any], hechos: BaseHechos, evaluador: Evaluador) -> dict[str, Any]:
        traza: dict[str, Any] = {
            'id': entrada['id'], 'nombre': entrada['nombre'], 'origen': entrada['origen'],
            'unidad': entrada['unidad'], 'estado': 'DESCONOCIDO', 'valor': None,
            'pertenencias': {}, 'conjuntos': entrada['conjuntos'], 'dominio': entrada['dominio'],
            'fuentes': list(self.base.fuentes_de(entrada['origen'])),
            'fundamento_transicion': entrada['fundamento_transicion'],
        }
        aplicable = evaluador.evaluar(entrada.get('aplica_si', {'siempre': True})).valor
        if aplicable is not V:
            traza['estado'] = 'NO_APLICA' if aplicable is F else 'CONTEXTO_PENDIENTE'
            return traza
        if evaluador.evaluar(entrada.get('valido_si', {'siempre': True})).valor is not V:
            return traza
        n = hechos.dato(entrada['entrada']['campo']).numero
        if n is None:
            return traza
        valor = float(n)
        traza['valor'] = valor
        minimo, maximo = entrada['dominio']
        if not minimo <= valor <= maximo:
            traza['estado'] = 'FUERA_DE_DOMINIO'
            return traza
        traza['pertenencias'] = {nombre: pertenencia(valor, puntos) for nombre, puntos in entrada['conjuntos'].items()}
        traza['estado'] = 'CALCULADO'
        return traza

    def _conjunto(
        self, modulo: Mapping[str, Any], modelo: Mapping[str, Any],
        hechos: BaseHechos, evaluador: Evaluador,
    ) -> dict[str, Any]:
        entradas = {k: self._entrada(e, hechos, evaluador) for k, e in modulo['entradas'].items()}
        traza: dict[str, Any] = {
            'id': modulo['id'], 'nombre': modulo['nombre'], 'origen': modulo['origen'],
            'origenes': modulo['origenes'], 'estado': 'DESCONOCIDO', 'entradas': entradas,
            'reglas': [], 'centroide': None, 'area': None, 'curva': [], 'solicitud': None,
            'fundamento_transicion': modulo['fundamento_transicion'],
        }
        if any(e['estado'] not in {'CALCULADO', 'NO_APLICA'} for e in entradas.values()):
            return traza
        grados = {k: e['pertenencias'] for k, e in entradas.items() if e['estado'] == 'CALCULADO'}
        for regla in modulo['reglas']:
            habilitada = evaluador.evaluar(regla.get('aplica_si', {'siempre': True})).valor is V
            alfa = activacion(regla['si'], grados) if habilitada else 0.0
            traza['reglas'].append({
                'id': regla['id'], 'antecedente': regla['si'], 'alfa': alfa,
                'estado': 'EVALUADA' if habilitada else 'NO_APLICA',
                'consecuente': regla['entonces'], 'puntos_salida': modelo['salidas'][regla['entonces']],
                'soportes': sorted({k for k, _ in referencias(regla['si'])}),
            })
        calculo = centroide([(r['puntos_salida'], r['alfa']) for r in traza['reglas']])
        if calculo is None:
            traza['estado'] = 'SIN_COBERTURA'
            return traza
        indice, area, curva = calculo
        politica = modelo['politica']
        solicitud = 'CORRECCION' if indice >= politica['correccion_desde'] else (
            'MONITOREO' if indice >= politica['monitoreo_desde'] else None
        )
        traza.update(estado='CALCULADO', centroide=indice, area=area, curva=curva, solicitud=solicitud)
        return traza

    def _pendientes(self, hechos: BaseHechos, evaluador: Evaluador, calculadora: Any) -> list[Pendiente]:
        pendientes = [Pendiente(p.campo, p.motivo, 2 if p.campo == 'granos_defectuosos' else p.paso)
                      for p in super()._pendientes(hechos, evaluador, calculadora)]
        # La indisponibilidad participa en la decisión Mamdani, para que sus reglas y
        # su explicación coincidan con la decisión; no se modifica después.
        for modulo in (hechos.difuso or {}).get('modulos', []):
            for entrada in modulo['entradas'].values():
                if entrada['estado'] not in {'CALCULADO', 'NO_APLICA'}:
                    campo = entrada['id']
                    if not any(p.campo == campo for p in pendientes):
                        pendientes.append(Pendiente(campo, 'Entrada requerida por el núcleo Mamdani; verificar medición, método y dominio.', 2))
            if modulo['estado'] in {'SIN_COBERTURA', 'FUERA_DE_DOMINIO'}:
                pendientes.append(Pendiente(modulo['id'], 'Módulo Mamdani fuera del dominio o sin cobertura; revisar modelo y observación.', 2))
        return pendientes
