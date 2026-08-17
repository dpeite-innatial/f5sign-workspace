# Handoff — implementar `FieldValidation` + `FieldChoice` (BL-47)

> **Estado:** siguiente slice tras `22150bd`. Repo: `f5sign-backend`, rama
> `feat/envelope-field-entity` (sale de `origin/develop`, **no de master**).

## Dónde estamos

`22150bd feat(envelope): the Field entity — every placed rectangle is one thing`

Ya está en verde (1007 tests, PHPStan 0, deptrac 0, Covered MSI 89%): entidad `Field`,
`FieldId`, `FieldType` (11 miembros), `FieldPlacement` con guardas de finitud y tope de página,
migración `Version20260803000001`, persistencia DBAL (escritura + lectura), `AddField` +
`POST /api/v1/envelopes/{id}/fields`, `FieldView` y presenter.

**La decisión que gobierna todo es `docs/adr/ADR-0040-field-entity-unified-placement.md`.** Léelo
antes de tocar nada; en especial la Decisión 5 (esquema y sus cuatro departures) y la 7 (contrato
de autoría). No re-litigues lo que ya decide.

## La tarea

Las cinco columnas existen **sin dominio detrás** y nada las escribe:

```
validation_max_length      SMALLINT
validation_pattern         TEXT
validation_pattern_message TEXT
validation_date_format     TEXT
choices                    JSONB
```

Hay que crear los dos value objects y cablearlos. **No hace falta migración nueva** — las columnas
ya están y son nullable.

### Restricciones ya decididas (no re-abrir)

- **El bound de `choices` es 64.** Ya está declarado en ADR-0040 §5. ADR-0019 §5 sólo permite una
  colección en `jsonb` con un bound *declarado y forzado por el dominio*; el VO debe forzarlo — esa
  es la deuda que BL-47 registra.
- **`validation_*` va aplanado con prefijo `<vo>_<field>`**, que es lo que ya hace el esquema.
  `choices` se queda en `jsonb` porque es la única colección genuinamente variable.
- **`choices` sólo aplica a `DROPDOWN` / `RADIO`.** Decide si eso es invariante del agregado (mi
  recomendación) o se admite en cualquier tipo.
- **Los bounds de string son invariantes de dominio, no del DTO.** ADR-0019 §5 lo dice
  explícitamente. Ojo: la revisión ya señaló que `label` y `anchor_text` tienen su límite **sólo**
  en `AddFieldRequest`, así que cualquier llamador que no pase por HTTP los evita. No repitas el
  patrón con `validation_pattern` — el límite va en el VO.

### Superficie a cablear (en este orden)

1. `Contract/Type/FieldValidation.php` — `CompositeValueObject`, los cuatro miembros nullable.
2. `Contract/Type/FieldChoice.php` — wrapper (`value`, `label`), y la lista acotada a 64.
3. `Domain/Entity/Field.php` — `create()` / `rehydrate()` / accessors.
4. `Domain/Aggregate/Envelope.php` — `addField()`.
5. `Application/Command/Authoring/AddField.php` + `AddFieldUseCase`.
6. `UI/Http/Request/AddFieldRequest.php` — `options: {choices, validation}` (esa es la forma del
   contrato) + `AddFieldController` mapeando a los VOs.
7. `Infrastructure/.../DbalEnvelopeRepository.php` — `upsertField()` y `loadFields()`.
8. `Infrastructure/.../Read/DoctrineEnvelopeReadRepository.php` + `Contract/View/FieldView.php` +
   `UI/Http/EnvelopeJsonPresenter.php`.
9. `config/packages/nelmio_api_doc.yaml` — el componente `Field` ya existe; añadir `options`.

**Ojo con el JSON de `choices`:** ADR-0019 §5 exige JSON plano y neutral, mapeado explícitamente
por el dominio. Nada de `serialize()` ni de JSON acoplado a la clase.

## Trampas del entorno que ya costaron tiempo

- **El stack de infra monta `../f5sign-backend`.** `f5sign-infra/docker-compose.override.yml` está
  *trackeado* y alguien puede haberlo repuntado a `f5sign-backend-develop` — si los tests salen
  raros o las migraciones no cuadran, comprueba eso **primero**. Se levanta con `make up` desde
  `f5sign-infra`.
- **Loop de tests** (desde `f5sign-infra`):
  `docker compose exec -T php-fpm php bin/phpunit --filter X --no-coverage`.
  Gate completo: `docker compose exec -T php-fpm composer qa`.
- **Tras cambiar de rama o añadir migración:** `make test-db-reset` y luego `make test-db-setup`.
- **`config/reference.php` se regenera solo** al arrancar el contenedor. Revertirlo siempre antes
  de commitear.
- **`GenericValidationException` NO es de la familia kernel `DomainException`** → llega a HTTP como
  **500**, no 422. El borde tiene que validar forma antes de construir el VO. Es la razón por la que
  el tope de página vive en el DTO *y* en `FieldPlacement`.
- **cspell no está en `composer qa`.** Correr a mano:
  `npx cspell lint --config .cspell.json <ficheros>`. Insertar palabras **dentro del array
  `words`** — un script que reordene el fichero entero lo rompe.
- **Números de ADR: verificar contra TODAS las ramas remotas**, no sólo los checkouts locales.
  `git ls-tree --name-only origin/<rama> docs/adr/`. Esta sesión reclamó 0039 y estaba cogido.

## Trinquetes que van a saltar

- `AuthoringLoadsUnderRowLockTest` — si tocas los use-cases de Authoring, hay un roster que falla
  si uno nuevo no carga bajo lock o no se registra.
- `SchemaConformanceTest` — descubre tablas solo; no hay censo que editar. Si añades migración,
  valida sola.
- `NoRawDeleteRule` — a **cero** en `src/` desde que aterrizó. No lo rompas por código muerto.
- **Atribución de cobertura:** `#[UsesClass]` **no** acredita. Los VOs nuevos necesitan test propio
  con `#[CoversClass]` o Infection los marcará *Not Covered*. Ya pasó con `Field` en esta sesión.
- `tests/README.md` manda: `Unit/` y `Application/` son herméticos (nada de kernel ni BD).

## Findings de la revisión que siguen abiertos

No son de esta slice, pero no los pierdas de vista:

- **BL-46** — re-check en `send()` de que cada campo `SIGNATURE` conserva el grant `signs`. Va con
  la superficie de eliminación (BL-45).
- **BL-48** — `MoveField`/`UpdateField` para el editor visual. Cuando llegue, `Field::moveTo()`
  **debe limpiar `anchorText`** (las dos modalidades son exclusivas) y eso necesita test propio; en
  esta slice se quitó `moveTo()` porque no lo llamaba nadie.
- **BL-49 — el más urgente en el tiempo.** `envelope.field.value` va a llevar PII (NIF, nombres,
  PNG de firma) en `jsonb` plano. Hay que clasificarlo **antes** de que aterrice la escritura en
  commit: cifrar una columna ya poblada es expand/backfill/contract. Ver ADR-0032/ADR-0033.
- **BL-44** — retirar `document_assignment_placement` con la reescritura de call sites. La
  migración actual es aditiva a propósito: soltar la tabla antes rompe el camino de firma que
  `VisibleSignatureMarkTest` protege contra un EU DSS vivo.

## Contexto que evita reabrir debates

- **La fuente de verdad del contrato somos nosotros**, no el proyecto `f5sign-signer`. Publicamos
  `placement: {page, origin_x, origin_y, width, height}`; el signer usa `position: {x, y}` y la
  reconciliación la debe él. Está escrito en el Context del ADR-0040.
- **`FieldType` tiene 11 miembros** (`INITIALS`, `EUDI_WALLET`, con `RADIO` y `ATTACHMENT`). El
  domain model in-repo aún lista 9 y tiene banner fechado; se reconcilia cuando se acuñe (BL-43).
- **La guarda de `SIGNATURE` pregunta por el grant `signs`**, no por si existe fila. Desde ADR-0039
  una fila `visible`-only es un estado legítimo (el anexo que alguien lee y nunca firma).
