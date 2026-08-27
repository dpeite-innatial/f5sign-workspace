# Handoff — un reto de FIRMA verificado no caduca nunca (revisar)

> **Estado:** hallazgo, no tarea cerrada. Repo a revisar: `f5sign-backend`.
> **Encontrado:** 2026-08-26, depurando el signer contra el stack local. Reportado por el
> firmante con la frase *"he firmado sin requerir código otp por email"*.
> **No es defecto del signer.** El cliente es reactivo por diseño (`commit` → 401
> `AUTH_NO_OPEN_CHALLENGE` → `ReauthModal` sobre `/sign`) y se comportó bien: el backend
> no le pidió nada, así que no pintó nada.

## El hecho

Una firma ejecutada a las **09:10:07** consumió un reto de firma **verificado a las
07:40:37** y cuyo `expires_at` era **07:55:28**. Hora y media después de probarse, y una
hora y cuarto después de su propia caducidad.

Fila real (`session.auth_challenge`, sesión `1384e472-38f9-5374-bf15-eaf89626b88d`):

```
 gate    | method    | issued_at | verified_at | consumed_at | expires_at
 SIGNING | OTP_EMAIL | 07:40:28  | 07:40:37    | 09:10:07    | 07:55:28
```

Entre la verificación y el consumo, ese mismo firmante **volvió a pasar la puerta de ACCESO
seis veces** (verificaciones ACCESS a las 08:32:06, 08:49:48, 08:55:30, 08:57:45, 08:59:50 y
09:09:55). Ninguna de ellas tocó la prueba de firma retenida. El correo de firma más reciente
es de las 07:40; en la ventana en que se firmó no salió ninguno.

## Dónde está

`SigningSession::consumeSigningChallengeFor()` filtra así:

```php
if ($challenge->gate() !== AuthGate::SIGNING) { continue; }
if (!$challenge->isVerifiedAndUnspent())      { continue; }
if (!$challenge->authorises($documentSet))    { throw ...signingChallengeMisbound($this->id); }
$challenge->consume($now);
```

Y `AuthChallenge::isVerifiedAndUnspent()` es exactamente:

```php
return $this->verifiedAt !== null && $this->consumedAt === null;
```

**No mira `expiresAt`.** El helper que sí lo mira, `AuthChallenge::isLive()`
(`$this->expiresAt === null || $now < $this->expiresAt`), no se usa en esta ruta.

## Lo que YA está decidido y documentado — no re-litigar

Los docblocks cubren bien dos cosas, y son correctas:

1. **La prueba tiene que sobrevivir a la verificación.** Si el reto muriese al verificar, el
   guard tendría que caer en *"la sesión dice que está verificada"*, que es un flag, que es la
   puerta de acceso, que es el colapso que ADR-0049 §2.4 existe para impedir
   (`markVerified()`).
2. **Un reto ya consumido no autoriza un segundo acto.** `isVerifiedAndUnspent()` exige las dos
   mitades a propósito, y el bucle termina en
   `throw AuthGateRefusedException::noOpenChallenge(AuthGate::SIGNING)` cuando no encuentra
   ninguno — o sea, el enforcement en el caso normal **funciona**.

## Lo que NO aborda ningún comentario

**Cuánto tiempo puede quedarse esa prueba en el aire.** *Verificado y sin gastar* no tiene
límite temporal ni se invalida por nada de lo que pase después.

En producción eso significa: un firmante pide su código para firmar, lo teclea, se distrae o
cierra — y horas más tarde, o desde otro dispositivo con el enlace, la firma sale sin volver a
probar nada. Es justo la propiedad que ADR-0049 §2.4 dice que hace que la puerta de firma valga
algo: que la prueba se gaste contra **este** acto. Hoy se gasta contra este acto, sí, pero
**cuando sea**.

## Decisiones que os tocan a vosotros

No las tomo desde aquí, son de vuestro dominio:

1. ¿El bound es el `expires_at` del propio reto, o una ventana propia de *retención* distinta de
   la de adivinación del código? (Son cosas distintas: 15 min para acertar el código no tiene por
   qué ser lo mismo que 15 min para gastar la prueba.)
2. ¿Pasar de nuevo la puerta de ACCESO debería invalidar una prueba de FIRMA retenida? En el caso
   medido hubo **seis** en medio, varias de ellas por recuperación ADR-0053, y ninguna la tocó.
   Argumento a favor: reautenticarse el acceso implica que la sesión anterior se perdió.
3. ¿Qué código de error? Reutilizar `AUTH_NO_OPEN_CHALLENGE` mantiene el enrutado del cliente sin
   cambios (`errorCodeToPath` ya lo lleva al `ReauthModal`), y sería lo barato. Un código nuevo
   exige declararlo antes en el signer o cae a `/invalid` — ver la nota de contrato del signer
   sobre 4xx no declarados.

## Repro

1. Sesión con `auth_signing_gate` declarado (aquí `["OTP_EMAIL"]` en ambas puertas).
2. Pasar ACCESO; pedir código de FIRMA y **verificarlo**.
3. **No firmar.** Dejar pasar más de `expires_at` (15 min).
4. Volver, pasar ACCESO otra vez (o varias), y firmar.
5. Observado: firma aceptada, cero códigos de firma emitidos, `consumed_at` muy posterior a
   `expires_at`.

## Cómo salió a la luz

Depurando dos defectos del signer en `/auth` (arreglados en `f5sign-signer` `dadac91`,
`599e7e2`). Una de las pruebas verificó un reto de FIRMA que se quedó sin gastar porque la
pantalla estaba congelada por el segundo defecto. Hora y media después el firmante real firmó y
consumió aquel reto. O sea: **el hallazgo es un efecto colateral de una sesión de depuración**,
y la pregunta de si eso debería haber sido posible es la que se traslada aquí.

A fecha de este documento no queda ningún reto verificado sin consumir en la BD local
(`WHERE verified_at IS NOT NULL AND consumed_at IS NULL` → 0 filas).
