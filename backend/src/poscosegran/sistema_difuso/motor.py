"""Mamdani conjunto integrado en la agenda y compatibilidad modular histórica.

Los comparadores históricos son límites conservadores. Antes de calcular los
plazos, el centroide difuso puede solicitar corrección o monitoreo preventivo
en zonas de transición. No se ejecuta un segundo motor para resolver el caso.
"""
from collections.abc import Mapping
from typing import Any

from ..dominio.hechos import Accion, Motivo, Pendiente
from ..dominio.valores import F, V, Tri
from ..inferencia.base_hechos import Activacion, BaseHechos
from ..inferencia.lenguaje import Evaluador
from ..inferencia.motor import Motor
from .defuzzificacion import centroide
from .pertenencia import pertenencia
from .reglas import activacion, referencias

VERSION_MOTOR = '1.0.0-mamdani'


def version_modelo(base: Any) -> str:
    modelo = base.contenido['operativa'].get('difuso', {})
    if 'decision' in modelo:
        return '3.0.0-mamdani'
    return '2.0.0-mamdani' if modelo.get('estructura') == 'MULTIVARIABLE' else VERSION_MOTOR


class EvaluadorDifuso(Evaluador):
    def definicion(self, nombre: str) -> Tri:
        resultado = super().definicion(nombre)
        if nombre == 'riesgo_activo' and resultado is F and self.hechos.difuso:
            if any(m.get('solicitud') for m in self.hechos.difuso['modulos']):
                return V
        return resultado


class MotorDifuso(Motor):
    version = VERSION_MOTOR

    def __init__(self, base: Any) -> None:
        super().__init__(base)
        self.version = version_modelo(base)

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
            if modulo.get('etapa', 'encadenamiento') != etapa:
                continue
            traza = self._modulo(modulo, modelo, hechos, evaluador)
            hechos.difuso['modulos'].append(traza)
            if traza.get('solicitud') and 'decision' not in modelo:
                self._solicitar(modulo, traza, hechos)

    def _resolver(self, hechos: BaseHechos, evaluador: Evaluador) -> tuple[str, str]:
        modelo = self.base.contenido['operativa']['difuso']
        if 'decision' not in modelo:
            from ..sistema_experto.motor import resolver
            return resolver(self.base, hechos, evaluador)
        from .decision import inferir
        informe = inferir(modelo['decision'], hechos, evaluador)
        assert hechos.difuso is not None
        hechos.difuso['decision'] = informe
        decision = informe['decision']
        mensaje = f"Decisión Mamdani {decision}: centroide final {informe['centroide']:.3f}; clasificación de la salida agregada."
        hechos.motivos.append(Motivo(id='R30:MAMDANI_FINAL', regla='R30', mensaje=mensaje,
                                     fuentes=self.base.fuentes_de('R30'), fundamento='POLITICA_PROTOTIPO'))
        if decision in {'CORREGIR_Y_REEVALUAR', 'AUTORIZAR_CON_MONITOREO'}:
            hechos.acciones.append(Accion(codigo='CORREGIR' if decision == 'CORREGIR_Y_REEVALUAR' else 'MONITOREAR',
                                          descripcion=mensaje, responsable_requerido='PRODUCTOR'))
        # El plan y el control responden a la decisión ya inferida; no la eligen.
        if decision == 'AUTORIZAR_CON_MONITOREO':
            hechos.solicitar('MONITOREO', 'R30')
        return decision, 'MAMDANI_FINAL'

    def _entrada(
        self, modulo: Mapping[str, Any], modelo: Mapping[str, Any],
        hechos: BaseHechos, evaluador: Evaluador,
    ) -> dict[str, Any]:
        traza: dict[str, Any] = {
            'id': modulo['id'], 'nombre': modulo['nombre'], 'origen': modulo['origen'],
            'unidad': modulo['unidad'], 'estado': 'DESCONOCIDO', 'valor': None,
            'pertenencias': {}, 'reglas': [], 'centroide': None, 'area': None,
            'curva': [], 'solicitud': None, 'conjuntos': modulo['conjuntos'],
            'dominio': modulo['dominio'], 'fuentes': list(self.base.fuentes_de(modulo['origen'])),
            'fundamento_transicion': modulo['fundamento_transicion'],
        }
        aplicable = evaluador.evaluar(modulo.get('aplica_si', {'siempre': True})).valor
        if aplicable is not V:
            traza['estado'] = 'NO_APLICA' if aplicable is F else 'CONTEXTO_PENDIENTE'
            return traza
        if evaluador.evaluar(modulo.get('valido_si', {'siempre': True})).valor is not V:
            return traza
        entrada = modulo['entrada']
        valor: float | None = None
        if entrada['tipo'] == 'dato':
            n = hechos.dato(entrada['campo']).numero
            valor = float(n) if n is not None else None
        elif entrada['tipo'] == 'calculo':
            n = evaluador.calculadora.valor(entrada['campo'])
            valor = float(n) if n is not None else None
        elif entrada['tipo'] == 'diferencia':
            a, b = (hechos.dato(c).numero for c in entrada['campos'])
            valor = float(a - b) if a is not None and b is not None else None
        if valor is None:
            return traza
        traza['valor'] = valor
        minimo, maximo = modulo['dominio']
        if not minimo <= valor <= maximo:
            traza['estado'] = 'FUERA_DE_DOMINIO'
            return traza
        grados = {nombre: pertenencia(valor, puntos) for nombre, puntos in modulo['conjuntos'].items()}
        traza['pertenencias'] = grados
        traza['estado'] = 'CALCULADO'
        return traza

    def _modulo(
        self, modulo: Mapping[str, Any], modelo: Mapping[str, Any],
        hechos: BaseHechos, evaluador: Evaluador,
    ) -> dict[str, Any]:
        if 'entradas' in modulo:
            return self._conjunto(modulo, modelo, hechos, evaluador)
        traza = self._entrada(modulo, modelo, hechos, evaluador)
        if traza['estado'] != 'CALCULADO':
            return traza
        grados = traza['pertenencias']
        traza['reglas'] = [
            {'id': f"{modulo['id']}.{nombre}", 'alfa': alfa, 'consecuente': nombre,
             'puntos_salida': modelo['salidas'][nombre]}
            for nombre, alfa in grados.items()
        ]
        calculo = centroide([(modelo['salidas'][nombre], alfa) for nombre, alfa in grados.items()])
        if calculo is None:
            traza['estado'] = 'SIN_COBERTURA'
            return traza
        indice, area, curva = calculo
        politica = modelo['politica']
        solicitud = 'CORRECCION' if indice >= politica['correccion_desde'] else (
            'MONITOREO' if indice >= politica['monitoreo_desde'] else None
        )
        if modulo.get('solo_recomendacion'):
            solicitud = None
        traza.update(estado='CALCULADO', centroide=indice, area=area, curva=curva, solicitud=solicitud)
        return traza

    def _conjunto(
        self, modulo: Mapping[str, Any], modelo: Mapping[str, Any],
        hechos: BaseHechos, evaluador: Evaluador,
    ) -> dict[str, Any]:
        entradas = {k: self._entrada(e, modelo, hechos, evaluador) for k, e in modulo['entradas'].items()}
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

    def _solicitar(self, modulo: Mapping[str, Any], traza: dict[str, Any], hechos: BaseHechos) -> None:
        solicitud = traza['solicitud']
        origen = modulo['origen']
        hallazgo = f"DIFUSO_{modulo['id']}"
        hechos.solicitar(solicitud, origen)
        hechos.hallazgos.append(hallazgo)
        if origen not in hechos.reglas_activadas:
            hechos.reglas_activadas.append(origen)
        mensaje = (
            f"{modulo['nombre']}: centroide Mamdani {traza['centroide']:.2f}/100; "
            f"requiere {'corrección' if solicitud == 'CORRECCION' else 'seguimiento reforzado'} "
            'según la política preventiva del modelo.'
        )
        hechos.motivos.append(Motivo(
            id=f'{origen}:{hallazgo}', regla=origen, mensaje=mensaje,
            fuentes=tuple(dict.fromkeys(f for r in modulo.get('origenes', [origen]) for f in self.base.fuentes_de(r))),
            fundamento='POLITICA_PROTOTIPO',
        ))
        hechos.acciones.append(Accion(
            codigo='CORREGIR' if solicitud == 'CORRECCION' else 'MONITOREAR',
            descripcion=mensaje, responsable_requerido='PRODUCTOR',
        ))
        hechos.traza.append(Activacion(
            orden=len(hechos.traza) + 1, etapa='mamdani', pasada=1, produccion=modulo['id'],
            regla=origen, hallazgo=hallazgo, soportes=(modulo['id'],),
            solicitudes=(f'{solicitud}_SOLICITADA' if solicitud != 'MONITOREO' else 'MONITOREO_SOLICITADO',),
        ))

    def _pendientes(self, hechos: BaseHechos, evaluador: Evaluador, calculadora: Any) -> list[Pendiente]:
        pendientes = super()._pendientes(hechos, evaluador, calculadora)
        if self.base.contenido['operativa']['difuso'].get('estructura') == 'MULTIVARIABLE':
            pendientes = [Pendiente(p.campo, p.motivo, 2 if p.campo == 'granos_defectuosos' else p.paso) for p in pendientes]
        # La indisponibilidad participa en R30, para que también sus ramas y
        # explicación coincidan con la decisión; no se modifica después.
        for modulo in (hechos.difuso or {}).get('modulos', []):
            for entrada in modulo.get('entradas', {}).values():
                if entrada['estado'] not in {'CALCULADO', 'NO_APLICA'}:
                    campo = entrada['id']
                    if not any(p.campo == campo for p in pendientes):
                        pendientes.append(Pendiente(campo, 'Entrada requerida por el núcleo Mamdani; verificar medición, método y dominio.', 2))
            if modulo['estado'] in {'SIN_COBERTURA', 'FUERA_DE_DOMINIO'}:
                pendientes.append(Pendiente(modulo['id'], 'Módulo Mamdani fuera del dominio o sin cobertura; revisar modelo y observación.', 2))
        return pendientes
