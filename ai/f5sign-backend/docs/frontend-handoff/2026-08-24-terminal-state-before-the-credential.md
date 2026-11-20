# Traspaso al frontal — una pierna cerrada lo dice antes de la credencial

<!-- OFFREPO: los hechos del lado cliente (el bucle middleware → `/auth`, la lectura de `gate: null` +
`access_gate` como "firmante varado", el hueco `attestedStatus` del store, y el trazado de DELEGATED
que rebaja la severidad de BL-183) los midió la sesión que trabajaba en `f5sign-signer` los días
2026-08-21 y 2026-08-24 contra este backend. Están reescritos en línea donde se usan, así que nada de
este documento exige tener ese repo delante. -->

| | |
|---|---|
| **Origen** | rama `fix/terminal-session-on-pre-credential-routes` · [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) |
| **Fecha** | 2026-08-24 |
| **Repos afectados** | **signer** únicamente. El dashboard no toca estas rutas |
| **Naturaleza** | **rompe la unión publicada** de `status` en la ruta 2 (tercer miembro) · **aditivo** en la ruta 3 (`outcome`) |
| **Acción requerida** | leer `status === 'COMPLETED'` **antes** que nada en la apertura · leer `outcome !== null` en el descriptor · **dejar de inferir recuperabilidad de `access_gate`** |
| **Status** | Pending |
| **Versión** | `/v1` **no se bumpa**. Ver el porqué al final |

> ⛔ **Qué arregla: a quien ya firmó se le estaba pidiendo un código de verificación.** `POST
> /api/v1/signing/session` respondía `AUTH_PASSED` para una sesión `COMPLETED` —correctamente en un
> sentido estrecho: la puerta *sí* se pasó— y sin credencial, que es byte a byte el cuerpo del
> **firmante varado**. El cliente ofrecía recuperación, pintaba el campo de código leyendo
> `access_gate` del descriptor, y **todo envío moría en `AUTH_NO_OPEN_CHALLENGE` antes de tocar
> ningún canal**. Cero correos, cero SMS. Se reportó como "está roto el envío de correo".

## 1. Lo que cambia en el cable

### Ruta 2 — `POST /api/v1/signing/session`

```diff
- "status": "AUTH_PASSED" | "AUTH_PENDING"
+ "status": "AUTH_PASSED" | "AUTH_PENDING" | "COMPLETED"
```

`COMPLETED` **tiene precedencia** sobre los otros dos.

⛔ **`COMPLETED` NO implica que falte la credencial.** Si la puerta de acceso del destinatario es
neutra, la apertura sigue acuñando —llegar con el enlace *es* pasar esa puerta, y eso no deja de ser
cierto después de firmar—, así que `COMPLETED` junto a un `access_credential` vivo es un cuerpo
legítimo y útil: es cómo un firmante terminado conserva el acceso a su copia sellada. **Seguid
ramificando por la presencia de `access_credential`** para decidir si podéis llamar a las rutas 6-8;
`status` responde otra pregunta.

⚠ **`access_grant_expires_at` viene en el pasado cuando `status` es `COMPLETED`, y siempre vendrá.**
Una sesión terminal no se retira nunca por inactividad, así que su concesión no vuelve a abrirse. No
dibujéis cuenta atrás sin comprobar `status` primero. El traspaso del 2026-08-19 decía lo contrario y
queda marcado como desmentido allí.

### Ruta 3 — `GET /api/v1/signing/session/auth`

```diff
+ "outcome": null | "COMPLETED"      // siempre presente, nunca ausente
```

- `null` → la pierna **no** está cerrada. Cubre tanto *sesión aún no abierta* (esta ruta es llamable
  antes de la apertura) como *sesión viva*: ninguna de las dos está cerrada, que es lo único que este
  campo responde.
- No-null → cerrada, y **dice cómo**.

⛔ **`access_gate` SIGUE poblado en una pierna cerrada, a propósito.** Describe la **puerta**, que no
deja de existir porque la pierna se cierre — y vaciarlo rompería la pantalla de recuperación de todo
firmante genuinamente varado. **Ramificad por `outcome`, nunca por la presencia de `access_gate`**:
esa inferencia *es* el defecto original movido un campo a la derecha.

## 2. Las dos reglas, tal cual

```ts
// middleware, tras abrir sesión
if (open.status === 'COMPLETED') return goTo('/done')   // nunca /auth

// pantalla de autenticación, tras el descriptor
if (descriptor.outcome !== null) return renderClosed(descriptor.outcome)  // nunca el campo de código
```

`renderClosed`: `'COMPLETED'` → pantalla de finalizado. **Cualquier otro valor** → cerrado que este
cliente no sabe nombrar; pantalla neutra, nunca la de finalizado y nunca la ceremonia.

## 3. Por qué `outcome` es anulable y no un booleano

Se pidió `completed: boolean` y se descartó, y conviene que quede el porqué porque parecía más simple.
Un booleano no tiene sitio donde poner la respuesta el día que aterrice un estado terminal que **no
sea** una completación — `SigningSessionReader::status()` ya emite `'DECLINED'` en el read-model hoy
como literal, contra ese día. Entonces `true` le dice a quien rechazó que firmó, y `false` lo devuelve
a un campo de código que no puede satisfacer jamás. **Las dos ramas son incorrectas**, que es la señal
de que la forma está mal, no la disciplina de quien añada el caso. Una unión anulable crece: el caso
nuevo se nombra a sí mismo.

## 4. Lo que este cambio NO arregla

⚠ **Un `/done` sin credencial es correcto pero desnudo.** La fecha de firma, el nombre del documento y
la **descarga de la copia sellada** viven todos en el read-model, detrás de la credencial. Un firmante
terminado tras una puerta *declarada* no la tiene. `document_title` de la ruta 3 os salva de una
pantalla anónima y nada más. Que ese firmante pueda recuperar su copia es una decisión propia —
reabre [ADR-0053](../adr/ADR-0053-access-grant-recovery.md) §2.3 fila 1 en sus propios términos— y no
se ha colado aquí. **Registrada como [`BL-188`](../BACKLOG.md) y aparcada** el 2026-08-24: hay tres formas
visibles y ninguna costeada, así que espera decisión y no implementación. ⚠ Vuestro `/done` desnudo es
el estado estable mientras tanto, no un provisional que se vaya a arreglar solo.

⛔ **DELEGATED y SKIPPED siguen siendo invisibles a las dos rutas** ([`BL-183`](../BACKLOG.md)).
`outcome` se proyecta desde `SessionStatus`, la fila de **Session**, que para esos destinatarios está
perfectamente abierta — así que publicará `null`, o sea *abierto*. **No podéis degradar contra un
campo que afirma lo contrario de lo que pasa**, y por eso está escrito en la fila: la degradación
elegante cubre el cierre *nombrado-pero-desconocido*, no el *invisible*. La severidad real, trazada
por vosotros, no es callejón sino **ceremonia inútil y facturable**: se envía un código real a quien
no tenía nada que verificar y sólo la ruta 6 lo rechaza al final. Cerrarlo exige cruzar
`RecipientOutcome` al contexto de autenticación, que es un cambio en el Contract de Envelope.

## 5. La versión

`/v1` no se bumpa, y es decisión tomada, no silencio. [`BL-59`](../BACKLOG.md) y el fichero de rutas
reabren la pregunta en cada cambio rompedor; ésta es la cuarta vez y la razón es **nueva**: el modo de
fallo de un cliente sin actualizar bajo el tercer miembro es *el mismo callejón que ya tiene hoy*, así
que no hay cohorte a la que un 404 proteja ni ventana en la que los dos comportamientos difieran a
peor. El razonamiento caduca con su premisa, no con este documento.
