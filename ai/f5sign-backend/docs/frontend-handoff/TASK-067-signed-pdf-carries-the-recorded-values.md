# Traspaso al dashboard y al signer — el PDF firmado lleva los valores de campo y las reservas

| | |
|---|---|
| **Origen** | rama `feat/field-values-drawn-into-the-pdf` · commit `91b0e8db` · [TASK-067](../tasks/TASK-067-recorded-field-values-are-drawn-into-the-signed-pdf.md) · [ADR-0085](../adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md) |
| **Fecha** | 2026-10-21 |
| **Repos afectados** | **dashboard** y **signer** (solo lectura de lo que ya mostráis; ningún código obligatorio) |
| **Naturaleza** | **sin cambio de contrato**: ninguna ruta, cuerpo, `code` ni enum cambia. Cambia el contenido del PDF firmado |
| **Acción requerida** | ninguna · retirad, si los tenéis, los textos que dicen que el PDF aún no lleva los valores |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

Nada en la API. Cambia el comportamiento:

- Antes de cada firma que recibe un documento, en los dos modos, los valores que las partes registraron
  (`TEXT`, `DATE`, `DROPDOWN`, `RESERVATIONS`, …) se dibujan en él como campos de formulario de solo lectura, en
  la posición de cada ocurrencia del campo. La firma que sigue los bloquea. Cierra BL-269.
- Un `DROPDOWN` dibuja la etiqueta de la opción elegida; un texto que no cabe a 7 pt se corta con `…` en lo que se
  ve y conserva el valor completo en el campo.
- Las reservas de un destinatario se registran en la admisión de su firma, junto a los valores, no al completar.
  Quien lea las reservas ya las ve desde ese momento.
- La marca visible firmada en un campo nuestro cae donde el visor muestra la página (CropBox y `/Rotate`).
- Un documento con una firma ajena, un formulario XFA, bytes que el motor no lee o una geometría de página que no
  sabemos convertir se firma **sin dibujar**, como hasta ahora, y queda un log `error` en el backend.

## Lo que el frontal tiene que hacer

1. Nada es obligatorio. Si alguna pantalla avisa de que la copia firmada todavía no lleva los valores o las
   reservas, retirad el aviso cuando este traspaso esté desplegado (ver *Desplegado*).

## Lo que NO está listo todavía

- Que un visor **haga cumplir** el bloqueo de una firma: ni DSS ni la mayoría de los visores validan `FieldMDP` hoy
  (ADR-0085 §3.2). El bloqueo está escrito en el PDF; no se garantiza que nadie lo respete.
- Los sobres ya firmados no se redibujan.

## Cómo verificarlo desde el frontal

- Con el backend desplegado, enviad un sobre con un campo `TEXT` y firmadlo; abrid la copia firmada y comprobad que
  el valor aparece en la posición del campo. El OpenAPI generado no cambia: un diff de la spec debe salir vacío.
