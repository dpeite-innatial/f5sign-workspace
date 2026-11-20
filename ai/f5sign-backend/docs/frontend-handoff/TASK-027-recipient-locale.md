# Traspaso al frontal — un destinatario puede declarar su idioma, y el idioma por defecto pasa a español

| | |
|---|---|
| **Origen** | rama `feat/recipient-locale-chain` · el contrato lo cambia `e46e4f8` (campo `locale`) y el comportamiento `2c09c92` (idioma por defecto) · sin PR todavía |
| **Fecha** | 2026-08-17 |
| **Repos afectados** | dashboard (autoría de destinatarios) · signer (ninguna acción, ver abajo) |
| **Naturaleza** | additive — ningún campo cambia de tipo ni desaparece · **pero cambia un comportamiento observable**: el idioma por defecto de los correos |
| **Acción requerida** | update types (un campo opcional nuevo en dos sitios) · exponer el campo en el alta de destinatario cuando se decida el UX. ⚑ 2026-09-01: **y en el claim**, si adoptáis los huecos declarados de [TASK-036](TASK-036-claimable-recipient-slot.md) — ver el aviso de abajo |
| **Status** | Pending |

## Lo que cambió en el contrato

Un destinatario tiene ahora un **idioma opcional**, y **este cambio** lo pone en dos sitios del contrato
publicado (hay un tercero desde 2026-09-01: ver el aviso más abajo). Las formas exactas están en el spec
(`GET /api/doc.json`); aquí solo va **qué cambió y qué hacer**:

1. **`POST /api/v1/envelopes/{id}/recipients`** acepta `locale`, opcional, una etiqueta BCP-47 (`es`, `en`).
   Omitirlo o enviar `null` significa *"no indicado"*. Enviar `""` es **422**: la cadena vacía no es un tercer
   significado, es un valor mal formado.
2. **`GET /api/v1/envelopes/{id}`** devuelve `locale` en cada elemento de `recipients` — la misma etiqueta que
   se envió, o `null` si no se indicó nada.

⛔ **`locale` se fija al crear el destinatario y no se puede editar después.** No hay endpoint que lo cambie,
igual que no lo hay para `email` ni para `full_name`: hoy no existe ninguna ruta que edite un destinatario ya
añadido. Si el UX necesita corregirlo, hoy la única vía es anular el sobre y reemitirlo — no hay `PATCH` que
podamos usar y no conviene diseñar la pantalla como si lo hubiera.

> ⚑ **AMPLIADO 2026-09-01 — el alta ya no es el único momento en que se escribe `locale`.**
> [TASK-036](TASK-036-claimable-recipient-slot.md) añade
> `POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim`, que **rellena** un destinatario dado de
> alta como hueco declarado (`claimable: true`), y ese cuerpo **puede traer `locale`**. No es una grieta
> en el párrafo de arriba: es el caso opuesto a una corrección. Una corrección cambia *dónde* se alcanza
> a una parte **ya nombrada**; el claim es el momento en que la parte **se nombra por primera vez**, y
> por tanto el primer momento en que su idioma es conocible siquiera.
>
> Lo de arriba sigue valiendo entero para todo lo demás, y estas tres son las que hacen que el claim no
> sea la ruta de edición que este documento dice que no existe:
>
> - sobre un destinatario **nombrado en el alta** no hay ninguna ruta que toque `locale`, y el claim
>   tampoco: se rechaza con **409 `RECIPIENT_NOT_CLAIMABLE`** si el destinatario no se declaró hueco;
> - un hueco se rellena **una sola vez**: un segundo claim con otro `locale` es **409
>   `RECIPIENT_ALREADY_CLAIMED`**, no una actualización;
> - un claim que **omite** `locale` deja el valor como está — ausente significa *"no lo afirmo"*, nunca
>   *"bórralo"*.
>
> ⚠ **Nada de esto está desplegado**: `feat/claimable-recipient-slot` (`3bef45f`) no está mergeada. Las
> formas exactas del cuerpo están en el spec, y el traspaso que os toca leer para usarlo es el de
> TASK-036; este aviso está aquí solo para que la nota **dueña de `locale`** no siga diciendo que el alta
> es el único sitio.

⚠ **Y el cambio que se nota sin tocar una línea de frontal: el idioma por defecto de las notificaciones pasa de
inglés a español.** Con `locale` sin indicar (que es lo que envía todo cliente actual), un destinatario recibía
el correo en inglés y ahora lo recibe en español. La resolución es, en este orden:

1. el `locale` del destinatario, si lo declaró;
2. el idioma por defecto del tenant, si está configurado;
3. el idioma por defecto de la plataforma, que ahora es **español**.

Un idioma que el backend no sabe redactar **no se rechaza**: el correo sale igualmente en el idioma de
respaldo (español) y el envío queda registrado con el idioma realmente usado, no con el pedido. Así que
`locale: "fr"` es una petición válida que produce un correo en español, sin error y sin aviso.

## Lo que el frontal tiene que hacer

**Dashboard:**

- **Añadir `locale?: string | null` a los tipos** del payload de alta de destinatario y del destinatario que
  devuelve el `GET`. Es aditivo: no hacer nada sigue funcionando, con el destinatario sin idioma declarado.
- **Decidir el UX del selector** en el alta de destinatario. Dos avisos que ahorran un rediseño:
  - solo se puede elegir **al añadir** —o, en un hueco declarado `claimable`, en el claim que lo rellena
    (aviso de 2026-09-01, arriba)—; sobre un destinatario ya nombrado la interfaz no debe ofrecer
    cambiarlo;
  - hoy solo hay copia en **`es` y `en`**. Si el selector ofrece más idiomas, el correo saldrá en español sin
    ningún error — así que un desplegable abierto promete algo que el backend no cumple. Limitarlo a esos dos.
- **No tratar `null` como "inglés".** `null` significa que nadie lo indicó, y lo que se envía en ese caso
  depende del tenant y de la plataforma. Si la interfaz muestra el idioma efectivo, tiene que pedirlo al
  backend o dejarlo en blanco; calcularlo en el frontal duplica una decisión que va a cambiar.

**Signer:** ninguna acción. No consume ni `POST /recipients` ni el proyección de sobre; el único efecto es que
el correo con el que llega el firmante puede venir en otro idioma, lo que no cambia ninguna ruta ni payload.

## Lo que NO está listo todavía

- **Nada permite configurar el idioma por defecto de un tenant.** La tabla existe (`notification.tenant_default`)
  pero **no hay endpoint ni pantalla de aprovisionamiento**: hoy se inserta a mano en base de datos. No
  construir una pantalla de ajustes del tenant contra este campo — no hay API detrás.
- **No se puede editar el idioma de un destinatario ya creado**, ni ningún otro de sus campos. Eso es una
  superficie de edición de destinatarios que no existe todavía, no un hueco de este cambio. ⚑ **Sigue
  siendo cierto después del 2026-09-01**: el claim de [TASK-036](TASK-036-claimable-recipient-slot.md)
  *rellena* un hueco declarado vacío, y sobre un destinatario ya nombrado se rechaza — no es la ruta de
  edición que aquí se dice que no existe.
- **No hay validación del idioma pedido y no la va a haber a corto plazo.** No existe endpoint que diga qué
  idiomas sabe redactar el backend, así que el frontal no puede consultarlo: si necesita la lista, hoy es una
  constante suya (`es`, `en`) que hay que revisar cuando se añada un idioma.
- **No hay traducción del resto de la plataforma.** Este cambio es solo el **idioma de los correos**. El PDF
  de pista de auditoría tiene su propio campo (`settings_audit_trail_locale`) y los dos son **independientes**:
  ninguno hereda del otro, así que un sobre puede tener la pista en un idioma y el correo en otro.
- **La copia en español cubre solo dos avisos** (invitación a firmar y firma completada), que son los dos
  únicos que la plataforma envía hoy.

## Cómo verificarlo desde el frontal

1. **El campo viaja y vuelve.** `POST /api/v1/envelopes/{id}/recipients` con `"locale": "es"` → `201`; después
   `GET /api/v1/envelopes/{id}` y comprobar que ese destinatario trae `"locale": "es"`.
2. **Omitirlo no inventa nada.** El mismo `POST` sin la clave `locale` → el `GET` devuelve `"locale": null`,
   no `"en"` ni `"es"`.
3. **La cadena vacía se rechaza.** `"locale": ""` → `422` con la violación de campo, no `201` y no `500`.
4. **El idioma llega al correo.** En el stack de desarrollo, enviar el sobre y leer el mensaje capturado en
   Mailpit (`http://localhost:8025`): con `locale: "en"` el asunto empieza por *"You have been invited"*; sin
   indicar nada, por *"Le invitamos a firmar"*. Ese segundo caso es el que confirma que el defecto cambió.
5. **El spec es la fuente de las formas.** `GET /api/doc.json` → `components.schemas.Recipient.locale` y el
   cuerpo de `POST /recipients`. Si esta nota y el spec no coinciden, el spec manda.
