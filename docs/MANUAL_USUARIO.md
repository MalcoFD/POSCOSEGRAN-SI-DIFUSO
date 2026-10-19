> Versión 5.0: Mamdani determina la acción final. P2 contiene las cuatro mediciones principales y el plazo; P3 las verificaciones aplicables. Resultado explica los dos niveles de inferencia, con 9 y 14 reglas. Véase [CONVERSION_DIFUSA.md](CONVERSION_DIFUSA.md).

# Manual de uso

1. Inicia sesión. En desarrollo usa `productor` y la contraseña indicada en el README. El nombre mostrado y los permisos corresponden a la identidad verificada.
2. En Inicio, registra almacén, lote y unidad. Documenta el fundamento del clima cuando lo declares; una unidad representa condiciones homogéneas. Puedes reutilizar almacenes y lotes existentes.
3. Abre Evaluar. P1 identifica la fase y permite corregir modalidad o clima. P2 reúne las mediciones principales, su validación y el plazo. P3 muestra las verificaciones del lote y la inspección vigente del almacén, si existe. La revisión y los enlaces «Editar» aparecen al final de P3 antes de enviar; P4 es el resultado.
4. No se sabe no equivale a No. Cada dato aportado requiere fecha y método; agrega evidencia. NO_APLICA requiere motivo y contexto compatible. Puedes enviar una evaluación parcial, especialmente ante un hallazgo adverso.
5. Guarda borrador para continuar después. Se conserva una captura de la pestaña por usuario/unidad y un borrador opcional en el servidor. Recuperar el borrador reemplaza la captura visible. Si otro cambio produce un conflicto, revisa los datos, actualiza las revisiones y vuelve a enviar.
6. Resultado muestra qué hacer, por qué, las acciones, los datos pendientes y el próximo control. *Decisión final mediante Mamdani* muestra el centroide final, los once antecedentes, sus pertenencias, las catorce reglas y la curva agregada; el panel de conservación muestra las cuatro mediciones y nueve reglas anteriores. *Ver fundamento técnico* conserva hechos, motivos, fuentes y cálculos. Junto a cada campo, *¿Por qué se pide este dato?* señala las reglas que lo usan. La vida consumida es una fracción del tiempo de referencia, no una probabilidad de seguridad. Un resultado histórico puede estar invalidado o vencido.
7. En Seguimiento registra controles, aperturas, resellados, secado, enfriamiento u otros eventos y planes de monitoreo. El servidor distingue controles completos y parciales. Reevalúa después de una actuación.
8. Un técnico asignado puede emitir dictámenes, revisar incidencias y registrar resoluciones justificadas. Una inspección favorable o una revisión no cierra por sí sola la cuarentena. Una resolución tampoco autoriza automáticamente el almacenamiento.
9. La admisión solo se registra con evaluación actual y autorización vigente; el servidor vuelve a verificarlo al guardar.

Almacenes y lotes permite buscar y filtrar unidades y registrar una inspección compartida del almacén. Comparte solo infraestructura e higiene ambiental; las mediciones y hallazgos del grano permanecen por lote. Revisión técnica reúne incidencias de unidades asignadas. Base de conocimiento muestra las reglas y fuentes, incluidos los dos niveles Mamdani. Adquisición permite al ingeniero proponer y simular versiones. Configuración permite al administrador asignar o revocar el acceso de técnicos a almacenes y lotes; no convierte a un productor en técnico.

Los errores aparecen junto a la captura. Un fallo de red puede tener resultado incierto: reintenta la misma operación sin alterar los datos para conservar su clave de idempotencia. Si la sesión expira, vuelve a entrar con la misma cuenta; las capturas de evaluación y seguimiento permanecen en esa pestaña. Cerrar la pestaña elimina el almacenamiento de sesión; usa el borrador del servidor para conservar una evaluación.


## Continuar una evaluación y consultar Mamdani

Al regresar se conserva la captura de la pestaña y el paso. Después de emitir una evaluación se muestran las observaciones anteriores con su fecha y procedencia; solo los campos modificados se envían como nuevas observaciones. Corregir una observación registra otra, sin reescribir el historial. Revisar fase, plazo y fecha real al tomar una medición nueva.

En Resultado, «Decisión final mediante Mamdani» muestra los antecedentes, reglas, curva agregada, centroide y acción. «Cómo evaluó el sistema difuso» explica el nivel anterior de conservación. Los índices son codificaciones del prototipo, no probabilidades. Las cuarentenas abiertas siguen como hechos de entrada y requieren resolución competente.

En Adquisición, el ingeniero puede preparar una nueva versión JSON del modelo Mamdani, simularla y proponer su activación. Las curvas y la política se validan en el servidor; no se editan desde el formulario de campo.
