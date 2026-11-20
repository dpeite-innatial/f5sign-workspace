# Traspaso a signer y dashboard — el correo de cada ocasión imprime el id del sobre en su pie

| | |
|---|---|
| **Origen** | rama `feat/envelope-reference-in-emails` · [TASK-061](../tasks/TASK-061-every-recipient-email-carries-the-envelope-reference.md) · commit `f76722ae` (tip de la rama al escribirlo) |
| **Fecha** | 2026-10-20 |
| **Repos afectados** | signer y dashboard (solo informativo) |
| **Naturaleza** | aditivo: ningún cambio de contrato HTTP ni de eventos |
| **Acción requerida** | ninguna |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió

- El pie de **todo correo** de destinatario (todas las ocasiones) termina ahora con una línea: la etiqueta y el **id completo del sobre** (`envelope.id`), en texto plano, **no un enlace**. Solo en el canal de correo; el SMS no cambia.
- Es el mismo id que muestra la lectura de la sesión de firma y el que devuelven las rutas de sobres. Conocerlo no admite a nada.
- Una notificación fijada antes de este cambio conserva el pie con el que se fijó.

## Qué tiene que hacer el cliente

Nada. Si una pantalla del signer o del dashboard ayuda a localizar «el correo que recibí», puede mostrar `envelope.id` completo para que coincida con el pie; es opcional.

## Lo que NO está listo

- Nada pendiente en el contrato: no hay campo nuevo que esperar.

## Cómo verificarlo

- Regenerar el OpenAPI y comparar: no debe haber diferencias.
