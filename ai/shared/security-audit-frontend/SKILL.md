---
name: security-audit-frontend
description: 'Checks de seguridad específicos del stack frontend (Vue/Nuxt/TypeScript). Complementa a security-audit-core con: XSS (v-html + sanitización), CSP, secretos en código cliente, localStorage con datos sensibles, open redirects, postMessage con validación de origin, dependencias npm con CVEs. Invocada por security-audit-core. Úsalo con /security-audit-frontend T{id}. Activar con "security frontend", "audit Vue/JS", "check XSS/CSP".'
---

# Security Audit Frontend

Checks específicos del stack frontend. Normalmente invocada por `security-audit-core`; directamente invocable para debugging.

## Invocación

```
/security-audit-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea
- Output de `npm audit --json` provisto por task-runner

## Outputs

- `var/task-runner/T{id}/security-audit-frontend.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...]}`

## Ejecución

### XSS

- [ ] `v-html` con contenido sanitizado. Grep de `v-html` en templates:
  - Si el valor viene de una variable no saneada → FAIL categoría `xss-v-html`
  - Saneamiento aceptable: DOMPurify, sanitize-html, o el input viene de una fuente confiable documentada
- [ ] `innerHTML` en código JS/TS con input externo → FAIL
- [ ] `dangerouslySetInnerHTML` (si el proyecto usa alguna lib React-like) → FAIL
- [ ] Rendering de markdown del usuario: siempre via librería que sanitize (marked + DOMPurify, o similar)

### CSP (Content Security Policy)

Si el proyecto define CSP estricta:
- [ ] No se introducen `<script>` inline en `*.vue` (solo `<script setup>` procesado por el compilador)
- [ ] No `<style>` inline; usar `<style scoped>` o clases
- [ ] No `eval`, `new Function`, `setTimeout('string')` — ninguno con strings como código
- [ ] Imports de scripts externos via CSP whitelist

### Secretos en código cliente

- [ ] Búsqueda exhaustiva en ficheros frontend de:
  - Claves API (`API_KEY`, `sk_live_`, `pk_live_`, `AIza...`, etc.)
  - Tokens JWT incrustados
  - Passwords / credentials hardcoded
  - URLs internas no públicas
- Cualquier match → FAIL categoría `secret-hardcoded`
- Las variables públicas del frontend deben venir de `runtimeConfig.public` (Nuxt) o env vars expuestas al cliente, nunca hardcoded

### localStorage / sessionStorage / cookies

- [ ] No almacenar tokens JWT ni session tokens en localStorage/sessionStorage (deben ir en httpOnly cookies)
  - Grep de `localStorage.setItem` / `sessionStorage.setItem` con claves como `token`, `jwt`, `bearer`, `auth`, `refresh`
- [ ] Datos sensibles (PII, números de tarjeta, DNI) no se persisten en storage cliente
- [ ] Si se usa localStorage para state no crítico: documentar qué se guarda y por qué

### Veredicto de sesion en pantallas que no lo revalidan

Aplica a apps con middleware de ruta que solo corre en una ruta raiz (el signer:
`session.global.ts` corta con `if (!isIndexRoute) return` para no reentrar en SSR). Las
SUB-RUTAS se pintan enteras desde el store persistido, que puede ser de una sesion ya
muerta, y **nadie revalida nada**.

- [ ] Toda pantalla que renderice desde la sesion valida que sigue viva **contra el
      backend**, no solo comprobando que el store tenga datos
  - El caso que muerde no es el store vacio: es el store POBLADO y rancio, donde
    `session` existe y no dice nada
- [ ] Un **401 de una llamada de sesion** se ENRUTA (descartar sesion + volver a la ruta
      de arranque), nunca se pinta como error local dentro de un componente
  - Grep: manejadores de error que solo hacen `errorMessage.value = ...` sobre un 401
  - Un error confinado dentro de un visor/panel deja el resto de la pantalla **viva**:
    el usuario sigue operando sobre una sesion que el backend ya no reconoce
- [ ] Antes de rebotar se DESCARTA el estado invalido
  - Si el middleware tiene rama de reutilizacion (`session !== null && !error`), rebotar
    sin limpiar devuelve a la misma pantalla → bucle
- [ ] El rebote esta acotado a una vez por carga

⛔ **Por que es FAIL y no WARN, con un caso real:** en el signer se podia entrar a `/view`
y a `/sign` con la sesion caducada y recorrer la ceremonia entera —rieles, campos y boton
de firmar— con el fallo escondido en una tarjeta dentro del recuadro del PDF. Un firmante
puede llegar al final y **creer que firmo**. Lo encontro un usuario, no una revision: los
tests unitarios no lo ven porque vive en la interaccion entre pagina, middleware y store
persistido, asi que **este check se verifica en NAVEGADOR** con la sesion invalidada a
mano, no leyendo codigo.

### URLs externas y redirects

- [ ] Nuevos dominios en `fetch`/`axios`/`$fetch` están documentados (permite CSP connect-src)
- [ ] Redirects del cliente (`router.push`, `window.location`) no aceptan URLs externas del query string sin whitelist (open redirect)
  - Grep: `router.push(route.query.redirect)` sin validación → FAIL
- [ ] Links con `target="_blank"` incluyen `rel="noopener noreferrer"` (tabnabbing)

### postMessage y iframes

- Si el código nuevo usa `postMessage` o embebe iframes:
- [ ] `addEventListener('message', ...)` valida `event.origin` contra whitelist
- [ ] `postMessage(data, targetOrigin)` usa targetOrigin específico, no `'*'`
- [ ] iframes con `sandbox` attribute restrictivo

### Dependencias npm

Input: output de `npm audit --json`.
- [ ] Sin CVEs CRITICAL → FAIL si las hay
- [ ] Sin CVEs HIGH → FAIL si las hay
- [ ] MEDIUM → WARN
- [ ] LOW → WARN

Si el diff introduce dependencias nuevas:
- [ ] Cada dependencia nueva con CVEs es rechazada
- [ ] Dependencias con mantenimiento abandonado (ej. último commit >2 años, <20 stars) → WARN

### Formularios

- [ ] Formularios tradicionales con `action="..."`: tienen CSRF token en header o hidden field (según convención del proyecto)
- [ ] Si es SPA con fetch y cookies SameSite=Strict/Lax: CSRF auto-cubierto, OK
- [ ] Campos sensibles (passwords, tokens) usan `autocomplete="new-password"` / `autocomplete="off"` si procede

### Dependencias de DOM manipulation

- [ ] No se usa `document.write` (legacy, vulnerable)
- [ ] Refs al DOM (`ref()`) con `innerHTML = ...` con input externo → FAIL

### Tests de seguridad (si la tarea es sensible)

- [ ] Si tarea involucra auth (login, logout, refresh): tests E2E verifican que tras logout el token ya no funciona, que refresh falla cuando token expirado, que se limpian cookies
- [ ] Si tarea maneja PII: test que verifica que datos no quedan en localStorage tras logout

## Gravedad

- **FAIL:**
  - XSS vía v-html sin sanitizar
  - Secreto hardcoded en código cliente
  - Token almacenado en localStorage
  - CVEs HIGH/CRITICAL en dependencias
  - Open redirect
  - postMessage sin validación de origin
  - `innerHTML` / `document.write` con input externo
  - Sesion invalidada que deja operable una pantalla de accion (firma, pago, envio):
    el usuario puede completar un acto que el backend ya no reconoce
- **WARN:**
  - Dependencia pesada nueva
  - Dependencia con mantenimiento abandonado
  - `target="_blank"` sin rel
  - CVE LOW/MEDIUM

## Report

```markdown
# security-audit-frontend — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Categorías revisadas
- XSS: OK
- CSP: OK
- Secretos en código: OK
- localStorage: OK
- Redirects: OK
- postMessage: n/a
- Dependencias npm: 2 LOW, 0 MEDIUM, 0 HIGH, 0 CRITICAL
- Formularios: OK
```

## JSON de retorno

```json
{"status":"fail","summary":"1 XSS vía v-html + 1 token en localStorage","issues":[{"severity":"fail","category":"xss-v-html","file":"components/EnvelopeDescription.vue:28","message":"v-html con envelope.description sin sanitizar"}]}
```

## Qué NO hace

- No hace los checks genéricos (secretos en backend, PII en logs del servidor, authz conceptual) — eso es `security-audit-core`
- No audita la API que consume — eso es `contract-check-frontend` (tipos) + `security-audit-backend` (backend)
- No valida accesibilidad (`a11y-check`)
- No ejecuta pentesting del cliente (XSS real no detectable sin runtime)

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/frontend/06 - Security Audit Frontend.md`
- security-audit-core: `.claude/skills/security-audit-core/SKILL.md`
- OWASP Top 10 Web: https://owasp.org/www-project-top-ten/
