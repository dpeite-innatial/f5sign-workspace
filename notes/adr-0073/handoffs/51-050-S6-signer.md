# Traspaso al signer (PROVISIONAL): una participación cerrada con el sobre abierto ya no entra ni lee

| | |
|---|---|
| **Origen** | TASK-050 (ADR-0073 §2.3, §2.8), arreglos S6 y "corte síncrono de lecturas", más el reword de `ENVELOPE_NO_LONGER_LIVE` |
| **Medido en** | `f5sign-backend` rama `feat/deadline-bars` @ `3a837cbe` (2026-09-29), sin mergear en `develop` ni desplegar; signer `f5sign-signer-adr0073` rama `feat/prep-adr-0073-envelope-ending` @ `810275a` (2026-09-29) |
| **Repos afectados** | signer. dashboard-sf no: no usa rutas de firma |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando aterrice el paquete ADR-0073 |

## Qué cambió (commiteado)

Con TASK-050, la participación de un miembro puede cerrarse **mientras el sobre sigue abierto**: un firmante
bloqueante liberado por el plazo de su paso (`RELEASED` · `released_by: STEP_DEADLINE`), o quien rechazó. Hasta
ahora ese miembro podía seguir abriendo su enlace y leyendo. Ahora no, **salvo que ya firmara o sea
informativo** (visor, etc.), que siguen entrando y leyendo como antes (ADR-0073 §2.3).

1. **Abrir la sesión** (`POST /api/v1/signing/session`) y **pasar el código** (auth-response) responden
   **409 `LEG_CLOSED`** si su participación ya no pasa la puerta, aunque la cerrara un plazo un instante antes.
   No se acuña credencial. El código ya existía; lo nuevo es que aparece también en ese instante.
2. **Los bytes del documento** (`GET /api/v1/signing/session/documents/{id}`) responden **404** a una
   participación cerrada que ya no pasa la puerta, **aunque la credencial de sesión (15 min) siga viva**. No
   esperan a la revocación asíncrona.
3. **`GET /api/v1/signing/session`** responde **409 `LEG_CLOSED`** al liberado (ya lo hacía). **Quien rechazó**
   sigue recibiendo **200 con `status: DECLINED`**, pero sus bytes ahora dan 404. El spec lo dice: la garantía
   "las dos rutas no pueden discrepar" tiene esa excepción.
4. **`ENVELOPE_NO_LONGER_LIVE` ya no significa "cancelado".** Un sobre también se cierra **con acuerdo** sin la
   parte de este destinatario: el emisor lo cerró al estar asegurado (close-now), o venció un plazo. Para
   saber cómo terminó, leed `outcome` (la participación) y `envelope_outcome` (`AGREED` \| `NOT_AGREED`) en
   `GET /api/v1/signing/session/auth`, que el mismo enlace sigue alcanzando.

## Lo que vi en vuestro árbol (@ `810275a`) y qué tocaría

- **`LEG_CLOSED` y `ENVELOPE_NO_LONGER_LIVE` llevan a `/s/{token}/declined`**
  (`useSignerNavigation.ts` `errorCodeToPath()`, líneas ~135 y ~168). En `es.json`, `status.declined.subtitle`
  dice *"El sobre fue rechazado o anulado."* **Revisad qué subtítulo ve un liberado por plazo** que llega por
  `LEG_CLOSED`: no rechazó nada, y el sobre puede haber terminado `AGREED`. Si ve el subtítulo por defecto, el
  texto es falso. `auth.vue` ya tiene `legReleasedSubtitle`, que lee `envelope_outcome` (línea ~349): es el texto
  correcto para este caso. Proponemos que `LEG_CLOSED` reutilice esa lógica o esa pantalla, en vez del
  "rechazado o anulado" genérico.
- **El 404 de bytes lo tratáis como reintentable** (`usePdfDocument.ts` `classifyPdfError()`, ~65:
  `NOT_FOUND` no es terminal). Ahora un 404 también puede significar "tu participación se cerró mientras
  leías". Proponemos que, ante un 404 de bytes, **releáis `GET /api/v1/signing/session` antes de reintentar**:
  - si responde `LEG_CLOSED` o `status: DECLINED`, es terminal: navegad a la pantalla de participación cerrada;
  - si no, seguid como ahora.
- **Quien rechazó** (`status: DECLINED`) no debe intentar descargar: los bytes darán 404. Vuestro middleware ya
  trata `DECLINED` como terminal (`session.global.ts`). Comprobad que ninguna pantalla de rechazado pide el PDF.

## Qué no cambia

Firmantes que ya firmaron y miembros informativos: mismas respuestas que antes, también con el sobre cerrado.
`ENVELOPE_NO_LONGER_LIVE` sigue siendo terminal (no reintentar); solo cambia lo que significa.
