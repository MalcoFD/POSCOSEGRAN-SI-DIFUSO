"""Sistema experto POSCOSEGRAN, organizado según su arquitectura clásica.

    base_conocimiento  Representación del conocimiento: reglas, parámetros,
                       tablas y resolución, leídos de un archivo versionado.
    base_hechos        Hechos del caso: observaciones iniciales y hechos
                       inferidos durante la evaluación.
    difuso             Funciones de pertenencia, variables lingüísticas,
                       agregación Mamdani, centroide y medidas difusas.
    lenguaje           Evaluador del lenguaje de condiciones con grados de
                       verdad [inf, sup] (Zadeh: mín, máx, 1 - x); la lógica de
                       tres estados es su caso particular.
    calculos           Procedimientos de cálculo que las reglas invocan por
                       nombre, configurados desde la base de conocimiento.
    motor              Motor de inferencia genérico: sistema de inferencia
                       difusa tipo Mamdani (Modus Ponens Generalizado, Max-Min,
                       centroide) con resolución jerárquica por cortes-α.
    explicacion        Módulo de explicación: cómo, por qué no y por qué se
                       pregunta.
    adquisicion        Módulo de adquisición: propuesta, validación e impacto
                       de nuevas versiones de la base de conocimiento.

El motor no contiene ningún umbral, término lingüístico, regla ni prioridad del
dominio: todo se lee de la base de conocimiento.
"""
