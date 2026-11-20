# Traspaso al frontal — tres rutas dejan de aceptar el token del correo: llega la credencial de sesión

<!-- OFFREPO: los hechos del lado cliente (los ficheros de `f5sign-signer` que se nombran aquí, y el hallazgo de origen cruzado sobre el Caddyfile de `f5sign-infra`) vienen de esos dos repos, que no son alcanzables desde un checkout sólo-backend. Los confirmó la sesión que trabajaba en `f5sign-signer` el 2026-08-18 y están reescritos en línea donde se usan, así que nada de este documento exige tener esos repos delante. -->

| | |
|---|---|
| **Origen** | rama `feat/session-credential-and-refresh` · **en curso, NO mergeada** · último commit al escribir esto: `2ffcab9` · sin PR todavía. ⚠ La rama sigue viva: ese sha es la foto del día, no el punto de llegada |
| **Fecha** | 2026-08-18 |
| **Repos afectados** | **signer** únicamente. El dashboard no toca ninguna de estas rutas |
| **Naturaleza** | **rompe el contrato.** Tres rutas ya desplegadas dejan de aceptar el token del correo. No es aditivo y no hay periodo de convivencia: la ruta acepta una credencial u otra, nunca las dos ([ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md), un tipo por ruta sin cadena ni fallback) |
| **Acción requerida** | **migrar en la misma ventana que el backend** — ni antes (no hay contra qué hablar) ni después (el signer desplegado se queda fuera de las tres rutas). Y **leer el punto de contrato de abajo antes de diseñar el almacenamiento**, porque el patrón por defecto de una SPA es exactamente el que rompe |
| **Status** | Pending — **y el backend tampoco está listo.** Esto es la especificación con la que empezar a planificar, no un aviso de que ya podéis integrar |

> ⚑ **El punto de contrato que decide vuestro diseño, y va primero porque el patrón por defecto lo incumple.**
>
> **La renovación exige las DOS credenciales: el JWT caducado *y* el refresh.** Un cliente que sólo conserve
> el refresh **no puede renovar**, y su sesión se ha terminado.
>
> Esto descarta el patrón al que una SPA va por defecto — refresh en cookie, JWT sólo en memoria. Bajo ese
> arreglo **un recargado de página termina la sesión en silencio**. Y desde vuestro lado no se presenta como
> un error que puedas leer en una traza: se presenta como un **cierre de sesión intermitente**, que aparece
> cuando el usuario recarga, cuando el navegador descarta la pestaña en segundo plano, o cuando vuelve al
> flujo desde el correo. Los dos valores tienen que **sobrevivir a un reload**, los dos.
>
> El *por qué* está más abajo (§«Por qué la renovación necesita el JWT caducado»), y está escrito porque lo
> pedisteis explícitamente: es más barato razonar sobre el mecanismo que adivinarlo.

## Qué deroga este documento del traspaso del 2026-08-18

Este traspaso **enmienda** a [`2026-08-18-signer-contract-reconciliation.md`](2026-08-18-signer-contract-reconciliation.md).
Si leéis los dos, **manda éste** en los dos puntos siguientes y sólo en esos dos.

1. ⛔ **Se cae la fila `auth_status` de su tabla «Lo que NO está listo todavía».** Esa fila declara
   `auth_expires_at: null`, `auth_ttl_minutes: 0` y un `auth_completed_at` recalculado en cada lectura, y os
   dice que cualquier «tu sesión caduca en X» es una invención. **Con esta task deja de serlo**: los tres
   pasan a salir de un hecho — la caducidad real de la credencial y el instante real en que se pasó la
   puerta — en vez de literales del presenter. La derogación es **de esos tres campos y de nada más**:
   `method_used` sigue siendo el literal `DIRECT_LINK` hasta que [TASK-021](../tasks/TASK-021-two-gate-auth-model-and-access-gate.md)
   traiga el catálogo de métodos, y **la fila `auth_requirements` de esa misma tabla sigue siendo verdad**
   (`[]` siempre, también con esta task).
2. ✅ **Su aviso «no toquéis el borde de auth/sesión, está a punto de moverse» era éste, y esto es la
   llegada.** Ese bloque decía que TASK-029 iba primero y que era «donde ocurre la cascada de
   `f5sign-signer`». Es este documento. Los dos hechos que adelantaba siguen en pie y aquí se concretan:
   pasar la puerta **acuña una credencial** en vez de marcar un flag, y el borde se parte por rutas.

Todo lo demás de aquel documento sigue vigente tal cual: los cinco bloques stub restantes, las siete rutas
que no existen, las seis ramas de error muertas y el arreglo del botón de descarga. **Nada de eso lo arregla
esta task.**

## Lo que cambió en el contrato

Las formas exactas están en el spec (`GET /api/doc.json`) cuando esto aterrice; aquí va **qué cambia y qué
hacer**. Y por primera vez el spec dirá también **qué credencial pide cada ruta**: hasta hoy ese dato vivía
sólo en un `default` de ruta en PHP, invisible para un cliente ([ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.6).

### 1. La partición: tres rutas cambian de credencial, dos no

| Ruta | Método | Antes | Después |
|---|---|---|---|
| `/api/v1/signing/session` | **POST** (abrir/reanudar) | token del correo | **token del correo** (sin cambio) |
| `/api/v1/signing/session` | **GET** (read-model) | token del correo | ⛔ **credencial de sesión** |
| `/api/v1/signing/session/documents/{documentId}` | **GET** (bytes) | token del correo | ⛔ **credencial de sesión** |
| `/api/v1/signing/commit` | **POST** (firmar) | token del correo | ⛔ **credencial de sesión** |

La frontera tiene una regla, y merece la pena saberla porque predice dónde caerá cualquier ruta futura:
**¿tiene esta ruta un propósito legítimo *antes* de que el firmante pruebe nada?** Si sí, se queda con el
enlace, porque en ese momento todavía no puede existir ninguna credencial. Si no, pide la credencial, y
quien sólo tenga el enlace se rechaza en el borde antes de que corra una sola consulta
([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3).

⚠ **Presentar la credencial equivocada es un rechazo, no un intento con la otra.** No hay cadena ni fallback:
un token del correo en una ruta de credencial se rechaza, y al revés también. Los dos verificadores tienen
secretos distintos, así que esto es estructural y no depende de que alguien se acuerde.

### 2. Lo que recibís: un par, no un valor

- **Una credencial de acceso: un JWT de 15 minutos.** Es lo que va en cada petición a las tres rutas de
  arriba. Autodescriptivo a propósito y por excepción argumentada ([ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.1);
  no lo parseéis para tomar decisiones de producto, que para eso está el read-model.
- **Una credencial de renovación: opaca y rotatoria, 60 minutos.** No es un JWT y no se puede leer: es un
  valor opaco cuyo digest guarda el backend. **Se renueva en cada rotación**, así que cada renovación os
  devuelve un refresh nuevo y retira el anterior.
- **Un tope absoluto de 12 horas.**

**La renovación es reactiva, nunca programada.** Se renueva cuando una petición se rechaza por JWT caducado,
no con un temporizador. Un temporizador mantiene viva indefinidamente una pestaña abandonada, que es
exactamente lo contrario de para lo que existe la caducidad.

### 3. Por qué la renovación necesita el JWT caducado — es ALCANCE, no admisión

Lo pedisteis explícitamente y va entero, porque el resumen corto («hacen falta los dos») invita justo a la
conclusión equivocada: que el JWT caducado *sigue admitiendo algo*. **No admite nada.**

- El digest del refresh vive en una fila de `session.signing_session`. Esa tabla está bajo **row-level
  security con `FORCE`**, y su política se apoya en `public.current_tenant_id()`, que es **fail-closed**:
  si el alcance de tenant no está puesto, **revienta** en vez de devolver cero filas
  ([ADR-0017](../adr/ADR-0017-tenant-isolation-rls-persistence-contract.md)).
- Así que para *leer* el digest hay que fijar antes el tenant. Y el tenant **no puede venir de la petición**:
  [ADR-0044](../adr/ADR-0044-principal-resolution-at-the-edge.md) §2.3 prohíbe que el alcance salga de una
  entrada del cliente; tiene que salir del **resultado de una verificación**.
- **La firma del JWT caducado sigue siendo válida** — lo único que ha pasado es su `exp`. Por tanto el tenant
  que lleva dentro es uno que acuñamos nosotros y que podemos verificar. Verificamos la firma, fijamos el
  alcance con ese tenant, y a partir de ahí leemos el digest bajo RLS como cualquier otra fila.

**El JWT caducado ALCANZA; el digest del refresh AUTENTICA.** La propiedad que compra esto, y que es la
razón de que no valga cualquier otro arreglo: **un JWT caducado del tenant A emparejado con un refresh del
tenant B no encuentra fila.** La búsqueda ya corre dentro del alcance del primero.

No es *binding* de una credencial a otra, y no es detección de reutilización — eso es otra cosa y va aparte
(la rotación). Es que sin el JWT no hay forma legítima de saber en qué tenant buscar.

### 4. El tope de 12 horas corre desde el PRIMER acuñado y NO se recalcula

Es un **techo fijo, no deslizante**. Las 12 horas se cuentan desde que se acuñó el primer par de la sesión y
**la rotación no las reinicia**: renovar cien veces no compra ni un minuto más. Pasadas las 12 horas la
renovación deja de funcionar **con independencia de la actividad**, y hay que volver a pasar la puerta de
acceso.

Esto importa para el copy y para el diseño: un firmante que lleve toda la jornada con la pestaña abierta y
trabajando **va a ser expulsado**, y no por inactividad. Si vuestra UI explica el cierre de sesión, tiene dos
causas distintas que decir de forma distinta — inactividad (el refresh de 60 minutos) y tope absoluto (las 12
horas) — y confundirlas es prometer al usuario que «si sigo trabajando no me pasa».

## Lo que el frontal tiene que hacer

Estos puntos están escritos contra lo que hoy hay en `f5sign-signer`, confirmado el 2026-08-18.

### 1. Dos ranuras donde hoy hay una, y las dos sobreviven al reload

`useSessionStore` (`app/stores/useSessionStore.ts`) persiste **un solo `token`** a `sessionStorage`. Ahora
hacen falta **dos**, y ninguna de las dos puede vivir sólo en memoria — por el punto de contrato de arriba.
El token del correo además **sigue estando en la URL** para las rutas que abren sesión, así que en realidad
hay tres valores en juego con tres vidas distintas.

### 2. Enrutado por endpoint en el adapter

Doce métodos de `SigningApi.real.ts` reciben `args: { token }` y lo mandan sin distinguir. Ya no vale un
único valor: **token del correo** para las rutas que abren sesión, **credencial de sesión** para las tres
particionadas. Lo que hoy es un parámetro pasa a ser una decisión del propio adapter por endpoint.

### 3. ⛔ El middleware NO se repunta

`app/middleware/session.global.ts` compara `session.token === to.params.token` contra el segmento de la URL.
**Esa comparación tiene que seguir refiriéndose al token del correo.** Repuntarla a «la credencial vigente»
—que es lo que parece coherente cuando estás renombrando cosas— deja de casar con el segmento de URL, y el
resultado es un **refetch en cada navegación**. Es la identidad de reutilización de sesión, no la credencial
de la petición: son dos cosas que hoy coinciden en un mismo campo y a partir de ahora no.

### 4. Una sola renovación en vuelo por cliente

Un rechazo por JWT caducado dispara **una** renovación y luego reintenta la petición; los rechazos
concurrentes **esperan a esa única llamada** en vez de arrancar cada uno la suya.

⚑ **Esto es la defensa principal contra la carrera de rotación, y vive en vuestro lado.** El backend tiene
una ventana de gracia de 30 segundos durante la cual el refresh retirado todavía renueva, pero eso es sólo el
respaldo para el caso de **dos pestañas distintas**, donde vuestro single-flight no puede llegar. Fuera de esa
ventana, presentar un refresh ya retirado **termina la sesión entera** — a esas alturas no es una carrera,
es que existe una copia. Si cada petición rechazada arranca su propia renovación, os matáis la sesión sola.

### 5. `AuthResponse` no tiene dónde recibir la credencial

El tipo cliente que declara la respuesta de la puerta **no tiene campo** para una credencial. Hay que
abrirlo, y conviene hacerlo sabiendo que llegan dos valores y no uno.

### 6. La rama de re-auth de `useSignFlow`: **aparcar, no borrar**

Ya os lo dijo otra sesión y se repite aquí para que no se pierda: esa rama hoy es inalcanzable, pero **el
borde de auth es justo lo que se está construyendo**. Dejadla donde está.

⚠ **Y un aviso para que no la cableéis contra una cadena inventada:** el `code` concreto con el que el
backend distinguirá «JWT caducado, renueva» de «credencial inválida, sesión terminada» **todavía no se
emite**. [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3 nombra `AUTH_REQUIRED` para el
rechazo de borde en una ruta que exige credencial, pero eso es la decisión escrita, no una cadena que hoy
salga por el cable. En este backend **un `code` existe sólo si una excepción lo declara** — es el mecanismo
que ya os dejó seis ramas muertas, documentado en el traspaso anterior. Así que: **no ramifiquéis sobre una
cadena adivinada**; la definitiva llega en el spec publicado con el endpoint de renovación.

## La pregunta de la cookie, en las dos direcciones

Se registra aquí entera —el hallazgo lo aportó la sesión de `f5sign-signer` el 2026-08-18— para que no se
vuelva a discutir desde cero **ni se descarte mal**. Las dos mitades importan.

**Por qué una cookie `HttpOnly` para el refresh no es viable HOY.** En producción el signer y la API están en
**orígenes distintos**: el Caddyfile de `f5sign-infra` tiene un bloque propio para el signer que sólo hace
reverse-proxy al contenedor del signer, y el Caddy del propio signer sirve estáticos y **no** proxea `/api`.
Cross-origin, esa cookie es una **cookie de terceros** — y **Safari iOS, que es vuestro objetivo declarado,
las bloquea de plano**. No es una preferencia de configuración, es que no llega.

⚠ **Y en desarrollo esto es invisible**, que es lo que lo hace peligroso: en local **sí** sois mismo origen,
vía el `devProxy` de Nitro. Un montaje con cookie funcionaría perfectamente en vuestra máquina y fallaría en
producción sobre el navegador que más os importa.

**Pero no es imposible: está sin construir.** Lo único que hace falta es que **alguien proxee `/api` en el
origen del signer**, y eso es un cambio de `f5sign-infra` — **no es de ninguno de los dos equipos en
solitario**, y por eso no está hecho y por eso no lo decide este traspaso.

**El coste de no tenerlo, dicho en voz alta para que la decisión sea consciente:** con las credenciales en
almacenamiento accesible desde JavaScript, el radio de explosión de un XSS pasa de *el enlace del correo* a
**hasta 12 horas de acceso a la sesión**. No es una razón para bloquear la integración —el tope absoluto es
justo lo que acota ese radio— pero sí para que quede escrito quién tendría que mover qué si algún día se
quiere cerrar.

## Lo que NO está listo todavía

- ⛔ **El propio backend.** La rama `feat/session-credential-and-refresh` está **en curso y sin mergear**.
  Nada de este documento se puede llamar hoy. Es la especificación para planificar, y os llegará el aviso
  cuando aterrice.
- **El endpoint de renovación no tiene ruta publicada.** Su path, su forma y **cómo viaja cada una de las dos
  credenciales en esa petición** aterrizan con el propio endpoint en el spec. **No los adivinéis**: hasta que
  salga en `debug:router` y en `/api/doc.json`, no existe. (Es la misma trampa de las siete rutas inventadas
  que ya os documentó el traspaso anterior.)
- ⚠ **[TASK-028](../tasks/TASK-028-opaque-signing-token.md) NO entra en esta ventana.** Es una task
  **distinta**, la lleva **otra sesión**, y traerá su propio traspaso. Es la que convierte el token del correo
  en credencial opaca y la que hace que un enlace caducado se distinga de uno manipulado con un `code` propio
  (`TOKEN_EXPIRED`). **Nada de eso llega con esta task.** El plan escrito quería agrupar las dos cascadas en
  una sola ventana para vosotros; a día de hoy no van juntas, así que **no contéis con que llegan a la vez**
  y mantened `/expired` aparcada tal y como se os dijo.
- **`auth_requirements` sigue siendo `[]`**, y con él toda la puerta de acceso real: métodos, desafíos,
  intentos y bloqueos son [TASK-021](../tasks/TASK-021-two-gate-auth-model-and-access-gate.md), que va
  **después** de ésta. Esta task construye *qué te admite*; aquélla, *qué tienes que probar*. Con el par
  neutro —que es todo sobre existente— la puerta está abierta y la credencial se acuña en la primera
  petición, así que la ceremonia no cambia de aspecto.
- **Los otros bloques stub del read-model siguen igual**: `config`, `branding` y `fields_draft` no los toca
  nada de esto. La tabla del traspaso anterior sigue siendo la referencia para ellos.
- ⚑ **Cinco rutas que llamáis y que el contrato no clasifica.** `PATCH …/fields`, `POST …/evidence`,
  `POST …/complete`, `…/decline` y `…/review-ack`. La tabla de [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md)
  §2.3 cubre ocho rutas y **ninguna de esas cinco aparece**. **La respuesta ya está dada, y es vuestra**: las
  cinco tomarían la **credencial de sesión**, porque las cinco son operaciones *posteriores* a la apertura de
  la sesión y ninguna tiene sentido sobre el enlace del correo a secas. La única que admitiría debate es
  `decline`, y sólo si algún día se quiere un enlace de rechazo directo desde el correo — que hoy no existe, y
  vuestro propio middleware abre sesión antes de llegar ahí. ⛔ **Pero está registrado como
  [`BL-142`](../BACKLOG.md) y NO se formaliza en esta task, a propósito**: escribirlo en la tabla es una
  **enmienda a ADR-0049 §2.3**, y ampliar una tabla ya decidida dentro de una task de implementación es
  precisamente la edición silenciosa de ADR que las reglas del repo prohíben. Ninguna de las cinco existe hoy
  en el backend, así que no os bloquea; lo que os debe bloquear es **construir contra una de ellas dando por
  hecho qué credencial pide**.

## Cómo verificarlo desde el frontal

Nada de esto se puede ejecutar hoy — es la lista para el día que aterrice, y el orden importa porque cada
paso descarta un fallo distinto.

1. **Las rutas existen y son las que dice este documento.** `docker compose exec -T php-fpm php bin/console debug:router`
   desde `f5sign-infra`. Si el endpoint de renovación no sale ahí, no ha aterrizado.
2. **El spec dice qué credencial pide cada ruta.** `GET http://localhost:8000/api/doc.json` → `securitySchemes`
   y el `security` de cada operación. Es la primera vez que ese dato es público; si el documento y este
   traspaso no coinciden, **manda el documento**.
3. **El enlace ya no admite.** Abrid sesión (`POST /api/v1/signing/session` con el token del correo), guardad
   el par, y llamad a `GET /api/v1/signing/session` **con el token del correo**. Debe **rechazarse**. Es la
   prueba de la fuga de enlace y es el punto entero de la task.
4. **El par admite.** La misma llamada con el JWT → 200.
5. ⚑ **La prueba del reload, que es la que os avisa de haber elegido mal el almacenamiento.** Tirad el estado
   en memoria como lo haría un refresco de página, restaurad **sólo** lo que hayáis persistido, y seguid
   firmando. Si el JWT no sobrevivió, aquí es donde aparece — y aparece como sesión terminada, no como error.
   Comprobadlo **descartando y restaurando el par**, no inspeccionando el `sessionStorage`: lo segundo pasa
   aunque el adapter no lo lea.
6. **La renovación se dispara sola y una sola vez.** Esperad a que caduque el JWT (15 minutos) o forzadlo, y
   lanzad **varias** peticiones a la vez. Debe salir **una** renovación, no varias, y todas las peticiones
   deben reintentarse con la credencial nueva.
7. **Dos pestañas no se matan entre ellas.** Con la misma sesión abierta en dos pestañas, provocad una
   renovación en cada una casi a la vez: las dos deben seguir funcionando (ahí es donde entra la ventana de
   gracia del servidor). Y presentar un refresh **viejo** pasado un rato debe **terminar la sesión** — es el
   comportamiento correcto, no un fallo.
8. **El tope de 12 horas.** Difícil de probar a mano y por eso conviene tenerlo escrito: pasadas 12 horas
   desde el primer acuñado, la renovación deja de funcionar aunque el firmante haya estado activo todo el
   rato.

---

## Añadido 2026-08-18, tras integrar con el equipo del signer

Dos cosas que no estaban en la primera redacción. La primera **no la sabía**; la segunda la descubrieron ellos construyendo, y es la más cara de las dos.

### El reloj de inactividad: 60 minutos, y no estaba en la versión anterior de este documento

La credencial de refresco **caduca a los 60 minutos**, empujados hacia adelante en cada rotación. No aparecía en la primera redacción porque **no estaba implementado**: [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.3 lo decidía y §2.5 lo declaraba *el* reloj de inactividad de la sesión, y el primer corte de la task no lo construyó. Lo encontró un barrido de documentación, no un test — ninguna de las doce barras de aceptación nombra la inactividad.

Consecuencias para un cliente:

- La tolerancia real está entre **45 y 60 minutos**, no exactos: la renovación es *reactiva*, así que la ventana solo se desliza cuando ocurre una renovación de verdad.
- El cap absoluto de 12 h sigue corriendo desde el primer mint y **sigue sin recalcularse**. Son dos límites distintos, no uno.
- ⚑ **Un rechazo por inactividad pasa de raro a cotidiano.** Antes hacía falta estar 11 horas parado; ahora basta con irse a comer. Si vuestro enrutado manda un 401 de renovación a una pantalla de *enlace no válido*, esa pantalla empieza a mentirle a gente que solo se ausentó un rato.

**Y la salida, que no necesita ningún endpoint nuevo:** reabrir con el enlace del email **acuña un par nuevo** y reinicia el reloj de inactividad. `startIfAbsent()` no-opea sobre la sesión existente, pero el mint corre después de forma incondicional, así que quien tiene el enlace siempre sale con un par utilizable — misma sesión, mismo estado, mismo consentimiento. Renovación rechazada → reabrir → seguir.

⚠ **Pasadas las 12 h el bucle se degrada en vez de parar**: reabrir sigue dando una credencial de quince minutos que ya no se puede renovar. Un cliente ingenuo reintenta para siempre cada cuarto de hora. Poned un corte.

### ⛔ La credencial pertenece a UN enlace, y el backend no puede detectar que lo olvidéis

La sesión se deriva **entera** del bearer: no hay id de sesión en la ruta, ni en la query, ni en el cuerpo. Eso es deliberado — [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) lo decidió así para que nadie pueda *nombrar* la sesión de otro. El precio es que una credencial del enlace A, presentada después de abrir el enlace B, devuelve la sesión de **A**: su firmante, su remitente, su sobre, sus documentos. La petición es impecable y está correctamente scopeada. **No hay nada que un servidor pueda rechazar ahí.**

Esto no es teoría. El equipo del signer lo pisó el 2026-08-18 integrando contra esta slice: su `beginLoad` limpiaba el `sessionStorage` pero dejaba las credenciales en memoria, y el guardado siguiente las reescribía bajo la clave del enlace nuevo. Abrir un segundo enlace de firma en la misma pestaña servía el read-model de otra persona — y el commit habría firmado el sobre equivocado. Lo arreglaron el mismo día.

**La regla que todo cliente debe cumplir:** *una credencial pertenece a un enlace; al cambiar de enlace se descartan **ambas** credenciales, no solo la copia en storage.* Ojo también con una renovación en vuelo durante un cambio de sesión: su resultado no debe aterrizar en la sesión nueva.

Registrado como `BL-144`. La mitigación barata que nadie ha costeado es que la respuesta de apertura devuelva el id del sobre, para que un cliente pueda comprobar que coincide con el enlace que acaba de abrir — aditivo, y hace el desajuste detectable sin debilitar la derivación.
