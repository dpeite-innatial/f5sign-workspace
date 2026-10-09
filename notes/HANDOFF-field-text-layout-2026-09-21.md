# Handoff — Cómo va el texto de un campo dentro de su recuadro, en pantalla y en el PDF

| | |
|---|---|
| **Fecha** | 2026-09-21 |
| **De** | sesión `f5sign-signer` (`develop`) |
| **Para** | sesión `f5sign-backend`, para cuando se haga [BL-269](../f5sign-backend/docs/BACKLOG.md) (dibujar los valores en el PDF) |
| **Estado** | **Signer commiteado en `develop` local** (`7bb07cb` reglas + casos, `7d91fc9` pintado), **sin push**: el fichero de casos todavía no está en el remoto. El push lo decide el usuario (`develop` lleva además commits de zoom de otra sesión). Backend: nada construido. ⚑ *Corregido 2026-09-21 tras la revisión del backend: decía «SIN commitear».* |
| **Revisión** | 2026-09-21, sesión `f5sign-backend-claimable-98`. Reimplementó las reglas en Python solo con la cabecera de `fieldTextLayout.ts` y reprodujo los 17 casos. Lo suyo (§2.1, §2.2, §3, la inversión de `y`, qué dibujar para DATE/DROPDOWN/CHECKBOX) está en la fila BL-269 del backend: rama `docs/field-text-layout`, `8f29bca` (rehecho sobre `develop` `50fa923`), sin push. Allí consta que esta nota se corrigió el mismo día y que el golden se copiará del remoto del signer, fijado por `version`, cuando llegue. Lo del signer se corrige aquí. |
| **Origen** | Petición del usuario: que el texto se ajuste al recuadro (hoy "Reservas" sale en una línea cortada) *"y luego también entre todo correctamente dentro del pdf"*. Decisiones suyas: **la fuente estándar del PDF** (*"lo más simple"*), **no hace falta que sea perfecto al 100 %**, y **el signer no impide firmar**: qué hacer si no cabe lo decide el backend (§2). |

## 1. La idea

El recuadro que el firmante ve sobre el documento y lo que el backend dibuje en el PDF tienen que partir
las líneas igual. Si no, en pantalla caben tres líneas y en el PDF se corta la cuarta. Así que las dos
partes siguen **las mismas reglas**.

**Dónde están las reglas:** en la cabecera de
[`f5sign-signer/app/utils/fieldTextLayout.ts`](../f5sign-signer/app/utils/fieldTextLayout.ts). No se copian
aquí para que no se desfasen. En resumen:
- Helvetica estándar, de 10 pt a 7 pt;
- márgenes de 3 pt;
- a partir de 60 pt de alto el recuadro es de varias líneas; por debajo, de una.

**Casos de referencia:**
[`f5sign-signer/tests/fixtures/field-text-layout/golden-v1.json`](../f5sign-signer/tests/fixtures/field-text-layout/golden-v1.json).
- **Qué son:** texto y recuadro, con el tamaño y las líneas que deben salir.
- **De dónde salen:** de una implementación independiente de las reglas escritas.
- **Uso:** el test del signer los reproduce todos. Al backend le sirven para comprobar su dibujo.

**No hace falta exactitud al último decimal.** Con la misma fuente, los mismos tamaños, los mismos márgenes
y el mismo corte por palabras, las líneas salen iguales en la práctica.

⚑ **Añadido 2026-09-21 tras la revisión: el ancho de reserva ya está en las reglas.** Un carácter sin glifo
en WinAnsi cuenta **556** unidades, y todo se cuenta **por code point** (en PHP, `mb_str_split`; no bytes ni
grafemas). Antes el 556 solo estaba en el código: la reimplementación del backend daba 17/17 con ese ancho a
0, a 556 o a 1000, así que otro backend podía pasar todos los casos y partir distinto justo con `ł`/`ș` o
emoji. El fichero de casos pasa de 17 a **20**, con tres casos `fallback width:` que sí lo fijan. El último
fija que una palabra demasiado ancha se corta entre code points aunque sea dentro de un emoji compuesto
(ZWJ). Sigue siendo `version: 1`, porque el comportamiento no cambia: solo queda fijado. Commiteado en
`18316cc`, sin push.

**Alcance: solo `TEXT` pasa por estas reglas.** Solo `TextField` usa `FieldTextPreview`.
- **DATE, DROPDOWN, CHECKBOX y RADIO:** no hay nada definido. En DATE el firmante ve el formato de su
  dispositivo (p. ej. 21/09/2026) y se envía ISO. Qué se dibuja para cada uno está registrado en BL-269.
- **`RESERVATIONS`:** el signer todavía no pinta este tipo (0 coincidencias en `app/`). El «mismas reglas» de
  §3 es un compromiso pendiente, que va con el traspaso de TASK-044 al signer. ADR-0069 §3.2 pide que el
  signer conozca el tipo antes de que TASK-044 se despliegue.

**Dónde vive el contrato: pendiente de decidir el usuario.**
- **Hoy:** las reglas y los casos viven en el signer, y la documentación del backend no puede enlazar
  `../f5sign-signer`. El backend copiará `golden-v1.json` a sus tests, fijado por `version`.
- **El riesgo:** los dos repos se despliegan por separado y la versión no viaja en la petición. Un v2 en el
  signer se desviaría del backend sin que nada lo detectara.
- **La propuesta del backend:** el texto de las reglas y los casos van en `f5sign-docs/`, y cada repo copia
  los casos tal cual.

## 2. Lo que decide el backend: el signer deja firmar siempre

**Decisión del usuario (2026-09-21):** *"que fuese el backend el que se encargase de saber qué hacer si el
texto es más grande a la hora de ponerlo encima del pdf. No haría que el signer no dejase firmar"*.

El signer **no bloquea la firma** por cómo quede el texto. Envía el valor tal cual y el backend resuelve
dos casos al dibujar:

1. **Texto que no cabe ni a 7 pt.**
   - **En el signer:** el recuadro lo pinta a 7 pt y lo que sobra queda recortado.
   - **Lo que tiene que decidir el backend:** recortar igual, seguir bajando el tamaño o avisar de otra
     forma.
   - **Por qué solo él puede hacerlo:** es el único que conoce **todos** los rectángulos. ADR-0041 §6 oculta
     al firmante los de documentos que no puede leer. En Factor5 la reserva del destinatario también se
     imprime en la **conjunta**, que no ve, y allí el recuadro fluye con el cuerpo, así que su alto puede ser
     distinto (≥ 65 pt según `WaybillSignatureCells::RESERVATIONS_MIN_HEIGHT`).
   - **Cuándo pasa:** en 254×65 pt caben **7 líneas a 7 pt**; la 8.ª se sale aunque el texto sean 120
     caracteres, porque bastan 7 saltos de línea. Además, en `RESERVATIONS` `max_length` es opcional y el
     canal admite 2000 caracteres (ADR-0069 §2.4). ⚑ *Corregido 2026-09-21: decía «es raro».*
2. **Caracteres que Helvetica no tiene.**
   - **Cuáles:** la fuente estándar solo cubre **WinAnsi**. Entran español, catalán, francés, alemán,
     portugués y €. Quedan fuera `ł ś ź ș ő`, el cirílico y los emoji, que un conductor polaco o rumano puede
     escribir.
   - **Qué hace hoy el signer:** en pantalla los muestra tal cual, con la fuente del dispositivo.
   - **Lo que tiene que decidir el backend:** qué imprimir en su lugar. Por ejemplo, la letra sin el signo
     (ł→l) o un `?`.
   - **Un aviso:** lo que se imprima dejará de ser exactamente lo escrito. El texto original sigue guardado:
     - en `TEXT`, en `envelope.field.value`;
     - en `RESERVATIONS`, en el `reservations` del destinatario. Según ADR-0069 §2.2, `value` se queda en
       `NULL`.

     ⚑ *Corregido 2026-09-21: decía que siempre queda en `envelope.field.value`. Eso hoy solo vale para
     Factor5, porque aún crea "Reservas" como `TEXT` (`WaybillSignatureFormFields.php:65`, en `factor5_dashboard_sf`).*

## 3. Al dibujar

**Propuesta nueva, no un recordatorio.** De TASK-044 §6 y TASK-018 F4 salen solo dos cosas: los dos
modos necesitan mecanismos distintos, y tocar el contenido de una página después de una firma rompe las
firmas anteriores. Lo que sigue sobre `/AP`, `/DA`, `NeedAppearances` y la inversión de `y` es propuesta de
esta nota. ⚑ *Corregido 2026-09-21: decía «Recordatorio de lo que ya dice TASK-044 §6 / TASK-018 F4».*

**Requisito previo, que TASK-044 §6 sí dice:** el backend **no tiene motor PDF**, y DSS solo dibuja dentro
del widget de la firma. Nada de lo que sigue es posible sin añadir uno.

- **`SINGLE_SEAL`:** dibujar las líneas **antes** del sello, en la posición del rectángulo. El origen está
  arriba a la izquierda con `y` hacia abajo, así que hay que invertir `y` con la altura de la página.
- **`SEQUENTIAL_PADES`:**
  - los campos de formulario del PDF se crean antes de la primera firma, y su **aspecto (`/AP`) lo genera el
    backend** con estas líneas;
  - no dejar el tamaño en automático (`/DA` con 0) ni usar `NeedAppearances`: cada visor lo resuelve a su
    manera.
- **`RESERVATIONS` (ADR-0069):** mismas reglas, y el texto sale de `reservations`, no del campo. En el signer
  está pendiente (ver *Alcance* en §1).

## 4. Qué cambió en el signer (`7bb07cb`, `7d91fc9`; sin push)

- **El recuadro sobre el PDF muestra el texto con estas reglas.** Es un SVG en puntos PDF, así que escala con
  el zoom. En recuadros de varias líneas se ve partido y arriba a la izquierda, en vez de una línea cortada.
  En los de una línea se ve al soltar el campo; mientras se escribe, se ve el input.
- **Validación:** ninguna nueva. Ni "no cabe" ni los caracteres fuera de WinAnsi bloquean la firma (§2).
- **Para el integrador:** 60 pt de alto sigue siendo la frontera entre una línea y varias. Antes decidía si se
  editaba en línea o en la hoja inferior, y ahora decide también cómo se dibuja.
