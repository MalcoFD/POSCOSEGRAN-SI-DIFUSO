# Conocimiento Mamdani vigente

La versión 6.0 contiene una inferencia directa por modalidad. `base_conocimiento.yaml` publica funciones, política, clasificación y las matrices de 256 y 64 reglas. `catalogo.yaml` documenta esas mismas 320 reglas y sus referencias S01–S09.

`matriz_320.json` exporta la definición completa para revisión. `casos_referencia.json` congela 320 anclas para comparar propuestas. `corridas_4.json` contiene las cuatro demostraciones, sus pertenencias, reglas activadas y centroides. El historial real de esas demostraciones está identificado en la evidencia local `docs/EVIDENCIA_CORRIDAS_4.json`, distribuida por separado. La descripción publicada de las matrices está en [Reglas actuales](../docs/REGLAS_ACTUALES.md).

Los scripts `backend/scripts/generar_modelo_matricial.py` y `generar_casos_referencia.py` preparan estos archivos fuera de las evaluaciones. Después se carga una versión en PostgreSQL mediante `poscosegran.conocimiento.cargar`. El motor de la API utiliza esa versión publicada, no vuelve a generar reglas durante el cálculo.

La cuarta entrada es una inspección categórica con pertenencias 0/1. Las otras tres son continuas y solapadas. En hermético se excluye HR y se exige evidencia vigente de barrera y procedimiento interno. Las fuentes orientan el diseño, pero no publican esta matriz ni validan sus vértices para chulpi.
