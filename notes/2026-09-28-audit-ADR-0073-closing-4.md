# Cuarta auditoría (cierre) — ADR-0073 y TASK-048/049/050

- **Rama:** `feat/ending-without-agreement`, auditada en `6bac3194`; tras aplicar, `619f2a84`, pusheada.
- **Método:** relectura íntegra por mi parte, un subagente sonnet buscando regresiones de las ediciones de hoy
  (`git diff b7e31d82..HEAD -- docs`) y casos de uso rotos, y un subagente haiku con la comprobación mecánica
  completa.

## Veredicto

**Cerrado.** Solo aparecieron tres incoherencias de redacción entre frases vecinas, las tres introducidas hoy y ya
corregidas. Ninguna cambia una regla ni pide una decisión. La comprobación mecánica sale limpia en todo:
referencias `§`, enlaces, tablas, numeración, enums cerrados, nombres de eventos, sin emoji, ancho de 100 columnas
y BL-306…309 únicos.

## Lo corregido (un commit)

1. **Quién escribe las columnas de apertura.** "Only their own writers" estaba junto a "the relay-borne writers
   refuse after `closed_at`" sin decir que estos siguen existiendo. Ahora se dice que son gemelos de la escritura
   síncrona, con la misma escritura única `IS NULL`: el que llega tarde no cambia nada.
2. **Por qué no se corrige ni se reenvía a una pierna cerrada.** La razón escrita ("la puerta rechazaría el
   enlace") era falsa para firmantes e informativos. La razón real: una invitación pide un acto que esa pierna ya
   no puede dar. Esos dos vuelven a entrar por reset/desbloqueo y por el enlace de copia lista.
3. **El predicado `Signed` nombra la aprobación** en su propia definición (ADR §2.14, TASK-048 §3.7), no solo donde
   se usa.

## Comprobado y coherente

Unanimidad solo como `ALL`; `AT_LEAST` no último sin plazo; el tercer disparador de cierre frente a
`released_by: ENVELOPE_CLOSED`; las dos columnas de liberación en todos sus consumidores; el censo de webhooks;
el aviso de copia lista; el orden de construcción 048 → 049 → 050 barra por barra; D9 (la migración no registra
hechos) frente al comando post-deploy; el disparo de `MEMBER_NOT_REACHED` en el caso (h).
