# Traspaso al frontal — el catálogo de códigos de error, publicado en el spec

| | |
|---|---|
| **Origen** | `develop` · `a38800c` |
| **Fecha** | 2026-08-21 |
| **Repos afectados** | **cualquier consumidor de la API** — dashboard, signer y clientes externos |
| **Naturaleza** | **additive** — un esquema nuevo en el spec. Ninguna respuesta cambia, ningún código cambia de significado |
| **Acción requerida** | *update types* cuando esté servido: sustituir vuestro mapeo descubierto por sondeo por el enum publicado |
| **Desplegado** | ⛔ **NO todavía.** El stack de este workspace sirve el checkout principal, hoy en `97d7e3c` — anterior a `a38800c`. Comprobadlo vosotros: `components.schemas.ProblemCode` en el `doc.json` que os sirven (regla 4) |
| **Status** | Pending |

---

## Lo que cambió en el contrato

Nada de lo que ya salía por el hilo. **Lo que se añade es la capacidad de leer el catálogo** en vez de
descubrirlo provocando errores.

`components.schemas.ProblemCode` publica los **códigos de la taxonomía por condición** — los que
lleva un rechazo que implementa `ProblemCoded`, y los que de verdad hace falta ramificar, porque dos
condiciones pueden compartir estado y significar cosas opuestas. **Cuántos son se cuenta en el `enum`
del `doc.json` que os sirven**, no aquí: el conjunto crece con cada condición nueva —la rama
`feat/claimable-recipient-slot` le añade cuatro— y lo que garantiza que el spec los trae **todos** no es
una cifra sino el check de § *Lo que sostiene esto* (al final de esta nota), que asserta que ese `enum`
**es igual**, en las dos direcciones, al conjunto de códigos que los rechazos emiten de verdad.

⚑ **Corregido 2026-09-01, quitando el número en vez de actualizarlo.** Esta frase decía *"publica los
**19 códigos** de la taxonomía por condición"*, y el paso 1 de *Cómo verificarlo* decía *"existe y trae
**19 miembros**"*. Un número aquí es una copia del spec —justo lo que prohíbe la regla 1 de
[`README.md`](README.md)—, y **este documento lo leen los dos repos**, así que la copia se vuelve a
copiar. El 2026-09-01 se documentó la cadena entera de un daño con esta forma exacta (`c532cb8`): una
lista publicada en un `#[OA\*]` nuestro acabó en tres comentarios y dos tests del repo del signer, y
ninguna de esas copias tenía forma de enterarse de que la lista había dejado de ser cierta. Un número no
se entera; un mecanismo sí.

## Lo que el frontal tiene que hacer

1. **Leed el enum del `doc.json`**, una vez, en lugar de mantener una lista descubierta.
2. **Seguid ramificando sobre `code`, nunca sobre el status a secas.** El caso que lo demuestra sigue
   vivo: `AUTH_METHOD_UNAVAILABLE` y `RECIPIENT_CANNOT_RECEIVE_METHOD` son **los dos 422** y uno es una
   escalada a soporte mientras el otro es un dato de contacto que el remitente arregla en segundos.
3. **Mantened el *fallback* por status.** No es una medida provisional: ver abajo.

## Lo que NO está listo todavía

- ⛔ **El enum NO es cerrado, y tratarlo como tal os romperá.** El spec lo dice y lo repetimos aquí
  porque es la parte que se lee en diagonal. Otras dos familias llegan al hilo:
  - **Los diez *fallbacks* por estado**, cuando un rechazo no nombra un código más fino:
    `BAD_REQUEST`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `LOCKED`,
    `TOO_MANY_REQUESTS`, `UNPROCESSABLE_ENTITY`, `INTERNAL_ERROR`, y `ERROR` como último recurso.
    Conjunto fijo, listado entero.
  - **La familia de validación**: `VALIDATION_ERROR`, más códigos `INVALID_*` **derivados del tipo del
    valor ofensor** (`INVALID_EMAIL`, `INVALID_PHONE_NUMBER`, `INVALID_TENANT_ID`, …). Ésa es **abierta
    por construcción** — el código se computa de un nombre de tipo — así que se describe y no se
    enumera. Un enum que dijera cerrarla sería falso.

  ▶ **Un código desconocido es esperado, no un bug.** Caed al status.

- **El `code` en cada respuesta 4xx/5xx ruta por ruta** sigue sin estar: **98 de 149** respuestas del
  spec son un `$ref` a un componente compartido que describe el estado y no nombra ningún código. Eso
  es [`BL-181`](../BACKLOG.md) y no lo cierra este cambio.

## Cómo verificarlo desde el frontal

1. `GET /api/doc.json` → `components.schemas.ProblemCode.enum` **existe y es una lista no vacía**.
   Contad sus miembros **ahí** y trabajad con esa lista.
   ⚠ **Corregido 2026-09-01, y las dos ramas que lo tocaron llegaron a la misma conclusión por
   separado: este paso decía «trae 19 miembros» y a esa fecha eran 22**. ⚠ **Y esa cifra ya se quedó
   atrás mientras se escribía esto**: el equipo de dashboard midió **25** en el spec que tiene
   alcanzable el mismo 2026-09-01, contra los 22 de la rama sobre la que se corrigió esta nota. Tres
   códigos habían aterrizado en `develop` entre medias. Es la demostración más limpia que hay de por
   qué esta nota no lleva número: dos partes contaron bien, en el mismo día, y les salieron cifras
   distintas porque contaban árboles distintos. El
   conjunto crece cada vez que aterriza una condición nueva — `CREDENTIAL_RETIRED` y
   `ENVELOPE_NO_LONGER_LIVE` el 08-28, los cuatro de la ranura reclamable el 09-01 — así que una cifra
   aquí convierte un despliegue correcto en un falso negativo. Esta nota **deliberadamente no lleva
   ninguna**: contad lo que haya y compáradlo con el `enum` del spec que estéis consumiendo, no con
   este fichero.
   ⚠ **Buscad la propiedad del esquema, no la palabra**: `ProblemCode` casa dentro de la prosa de otra
   descripción, y una comprobación laxa devuelve un positivo tranquilizador.
2. Si no está, ese despliegue es anterior a `a38800c` — vuestro mapeo parcial sigue siendo lo correcto.

---

## ⚑ Lo que sostiene esto, y por qué no se va a erosionar

La petición que lo originó tenía tres partes y **se construyó la tercera primero**: *un código nuevo se
documenta en el commit que lo introduce*. No como norma escrita, sino como check —
`OpenApiSpecTest::every_problem_coded_refusal_names_its_code_in_the_spec()` rompe el build **en las dos
direcciones**: un código que ninguna excepción lleva, y un código que una excepción lleva y no está
publicado. Saboteado en ambas antes de darlo por bueno.

⛔ **Y una nota para quien mantenga esto por nuestro lado**: el catálogo vive en el **spec** y no en un
enum PHP a propósito. [ADR-0025](../adr/ADR-0025-rfc9457-error-shape.md) dice dos veces que el BC es
dueño del término y el edge no enumera ninguno; centralizarlos en PHP para poder listarlos pagaría esa
decisión para comprar esta lista.
