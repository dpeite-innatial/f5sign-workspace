# Auditoría del backlog — 2026-11-04

Propuesta sobre `f5sign-backend/docs/BACKLOG.md` en `develop` @ `12f654fc`. **No se ha aplicado nada.**

## Método

1. **Fusiones:** 14 agentes leyeron las filas por tema (solapados a propósito), solo el texto.
2. **Caducidad:** 14 agentes contrastaron las 417 filas abiertas contra el código.
3. **Validación:** 8 + 1 agentes a ciegas (sin ver el primer veredicto) rehicieron 107 filas; 3 agentes intentaron refutar 21 propuestas de fusión en el código.
4. **Segunda pasada:** 15 + 1 agentes a ciegas rehicieron las otras 306 filas y anotaron dónde caería cada arreglo. **Las 417 filas tienen ya dos opiniones independientes.**
5. **Desacuerdos que cambian la decisión:** resueltos en la sesión principal mirando código e infra.

Sin ejecutar tests, Infection ni nada en vivo: todo es lectura de código.

## Resultado

| | filas |
|---|---:|
| Abiertas hoy | 417 |
| Cerrar (resueltas u obsoletas) | −47 |
| Absorbidas en fusiones | −18 |
| **Quedarían** | **352** |
| De ellas, a reescribir porque son parciales | 42 |

## Lo que sigue sin estar cubierto

- **La segunda pasada encontró menos de lo estimado.** La muestra apuntaba a unas 24 filas resueltas sin detectar; sobre las 306 salieron 4 cierres y 18 parciales nuevos.
- **Un mal parser mío afectó a 12 filas.** Se cortaron 6 por un `|` interno (BL-167, BL-385 a 389) y 6 llegaron vacías a la segunda pasada (BL-401, 402, 404, 405, 415, 416). Todas se repitieron con el texto íntegro, pero la pasada de fusiones de BL-385 a 389 leyó el texto cortado.
- **Agrupar por sitio del arreglo cubre solo las 306 filas de la segunda pasada,** no las 111 de la validación. No aportó ninguna fusión nueva: las parejas que coinciden en sitio ya estaban propuestas, ya estaban descartadas o parecen defectos distintos. Solo BL-370/371 y BL-407/408 se leyeron enteras; el resto se juzgó por título, sin agente adversario.
- **Nada se ha ejecutado.** Lo que depende de una medición (Infection, flakes, DSS en vivo) sigue sin decidir.

## Intento de refutar 14 cierres (Opus, adversario)

Las pasadas neutrales con Sonnet daban estas 14 filas por cerradas. Atacadas con otro modelo: **3 se cierran, 6 se cierran con puntero y 5 no se pueden cerrar.**

| Fila | Veredicto | Qué queda |
|---|---|---|
| BL-14 | KEEP_NARROWED | The row's exact scenario, a CAS loser's locked object, is gone. Three things survive. (1) Promotion can leave a locked retained copy with no row, and a retried sweep adds another at a new key, with no test and no remedy. (2) No reaper exists for any unrecorded bytes: staged orphans stay indefinitely and are only reported. (3) The row makes correcting the record part of the item, and docs/LOAD-BEARING.md and docs/ddd/envelope-domain-model.md:820 still state the old mechanism. |
| BL-22 | CLOSE_WITH_POINTER | A decided mechanism exists, is accepted and is exercised, so the row's core is gone. Residual worth keeping: a document that cannot be prepared carries no reservation on the PDF and no durable record of the omission, only a log line. |
| BL-42 | CLOSE_WITH_POINTER | Nothing is broken. The capability the row wanted landed in another shape, but no record says the authored lock_config is retired, and three surfaces still promise it in the future or present tense: ADR-0040 Decision 5 ('lands with the v2 locking work'), ADR-0041 ('BL-42's lock_config names fields') and docs/ddd/signature-execution-domain-model.md:237 ('FieldMDP preparation → the external f5sign/pdf-tools service (v2)'). |
| BL-88 | CLOSE | Nothing survives from the row. Minting over a terminal envelope still succeeds, but that is published in the route's 409 text and decided at the open (ADR-0059), so it is not this row's defect. Not traced: I found no HTTP-level test that mints with another tenant's envelope on this route. That case rests on the port's contract and on RLS, plus the fake-based unit test. A grep shows the BL-97 row mentions BL-88; I did not read it, so sweep it for tense when closing. |
| BL-146 | CLOSE_WITH_POINTER | The defect is gone. What survives is that the row's named home of truth, TASK-014 section 7 item 12, now states something false in the present tense, and the two later narrowings (reopens, copy reads) are recorded only as a trail limitation and a task note. |
| BL-159 | CLOSE | The defect is gone: no proof waits between requests, so holding the session no longer lets anyone spend it. B now needs the code itself. Three things remain next to it, all outside this row. (1) A second link holder can still burn the shared attempt budget or retire the code with a resend; that is sabotage, not transfer, and ADR-0075 §7.7 and §7.5 discuss it. (2) BL-367 records the machine route trusting a human-opened session with no signing gate, by maintainer decision. (3) Commit coverage of the second-holder ca |
| BL-162 | CLOSE | Nothing survives for an ordinary recipient. AUTH_NO_DESTINATION is still reachable only through a declared unclaimed slot on the machine twin, which is BL-176's finding and not this row's defect. |
| BL-168 | KEEP_NARROWED | Keep the row, narrowed. Closed: the row's worst case, a third party holding link and code, when the corrected contact is a declared notification channel, because the link and credentials are retired. Still broken, at a live 15-minute TTL: (a) when no declared channel covers the corrected contact, including notification_channels [] and gate-only contacts, the link and the old code both stay valid; (b) the code is never invalidated on any path; (c) a corrected recipient who only ensures inside the TTL receives nothin |
| BL-176 | KEEP_NARROWED | The decision and the authoring/claim path are sound, but the deferral rests on 'an unclaimed slot reaches no gate', and the machine surface walks past that. Walk 1, step active, slot declaring OTP_EMAIL with no contact: machine key POST .../auth/otp/send passes gatePasses and the step check, recordRecipientOpening writes first_opened_at, startIfAbsent inserts the session, then 409 AUTH_NO_DESTINATION. That breaks ADR-0057 §2.4 ('no session row was ever created') and stamps the opening that ADR-0083 §2.1 uses to clo |
| BL-183 | CLOSE_WITH_POINTER | The row's main harm is gone for signing roles, delivered by the gate rule (ADR-0073 §2.3, ADR-0074), not by a dedicated change. What survives: (1) the informational-role gap above, latent because the population is empty; (2) the destination change at the signer is unverified, so the owner should confirm LEG_CLOSED lands on /unavailable; (3) closing would orphan live forcing text. The RecipientOutcome::DELEGATED docblock tells the next author to read BL-183 and its body is now FALSE ('carries envelopeIsAlive ... not |
| BL-185 | CLOSE_WITH_POINTER | The evidence gap is closed by the fact the row itself pointed to, and the trail reads it. No ADR records the decision not to emit AUTH_GATE_PASSED, and two live surfaces will read as an open gap once the row is gone: the AuthGatePassed docblock (with a dangling link) and TASK-034 section 7. |
| BL-204 | KEEP_NARROWED | ADR-0096 does answer decision 8's sub-decision as written for clear text and removes the refusal mechanism. It does not answer this row's own case: an identity ABSENT from a fact that decision 7, still standing, says should carry it. A claim is not one of the five members, so the clean slate does not cover it, and §2.6 distinguishes clear from encrypted, not absent. So the row's question stays unanswered: either retire decision 7 for RecipientClaimed and accept ROW_CURRENT identity as final, or require identity on  |
| BL-205 | KEEP_NARROWED | The ordinary path is fixed and tested, but the row's resolution rests on 'an unclaimed slot cannot have opened one', and that is false on the machine surface. One machine key call to the OTP send or answer twin on an unclaimed slot stamps first_opened_at, even when the call then fails with no destination. After that the gate cannot be amended and the claim cannot pass, so the row's original deadlock is back with void() or the wrong-phone claim as the way out; a step deadline may also release the slot. It takes an i |
| BL-308 | CLOSE_WITH_POINTER | The defect is gone and the row's ask is met. One residual is by design: a recipient declaring no signing gate over a link-only access gate can be declined by anyone holding the link. It is symmetric with signing, but a decline by a blocking recipient voids for everyone, and no record states that consequence for the neutral pair; ADR-0075 only says the act asks for nothing. Stale surface: an ADR-0073 list of what it leaves out still names 'a decline's weaker gate (BL-308)'. |

**Las otras 38 filas de A no han pasado este ataque.** 13 ya se declaraban cerradas o `Landed` en su propio texto (BL-172, 173, 188, 194, 227, 228, 273, 286, 301, 302, 406, 444, 469). Las 25 restantes solo tienen opiniones neutrales: no cerrarlas sin refutarlas.

## Posible defecto nuevo: un slot sin reclamar en las rutas de máquina

Dos agentes llegaron a él por separado. Confirmado leyendo el código, **no ejecutado**. `IssueAuthChallengeUseCase`, `SubmitAuthResponseUseCase` y `CommitDelegatedSignatureUseCase` no preguntan `isUnclaimedSlot()`, mientras la acuñación del token y la copia sí lo hacen. Con una API key:

- `POST /envelopes/{id}/recipients/{slot}/auth/otp/send` registra la apertura y crea la sesión aunque luego falle sin destino.
- Con `first_opened_at` escrito, `guardRecipientAuthChangeable()` responde `alreadyEntered`: vuelve el atasco que BL-205 daba por resuelto.
- Si el slot se creó con contacto, se envía un código a una parte que el sistema registra como sin nombre.
- La firma delegada sobre un slot ya estaba medida (BL-266). **La mitad de OTP no tiene fila.**

Si se confirma, además incumple ADR-0057 §2.4 («no session row was ever created»).

## Comprobaciones limpias

- Signer: el commit de BL-50, los tipos de BL-59 y `AUTH_PENDING` de BL-156 están en `origin/develop`. Su trabajo sin publicar no afecta.
- Infra: el fichero modificado es un comentario y un puerto de desarrollo.
- Ninguna rama por delante de `develop` toca `BACKLOG.md`.
- `resolving-commits.json`: 47 de 52 commits encontrados, con Haiku y por introductor del texto. Revisar al escribir cada cierre.

## A. Cerrar (47)

### Coinciden los dos agentes (36)

| Fila | Estado | Qué dice | Prueba (revisión a ciegas) |
|---|---|---|---|
| BL-10 | Open | [`CommitSignatureController`](../src/F5Sign/Session/UI/Http/CommitSignatureController.php)'s co | tests/F5Sign/Session/Unit/UI/Http/CommitSignatureControllerTest.php: self::assertCount(1, $bus->dispatched); self::assertInstanceOf(CommitSignature::class, $bus->dispatched[0]); |
| BL-11 | Open | draft-guard is unexercised at all five of its sites | tests/F5Sign/Envelope/Acceptance/EnvelopeHttpTest.php assertNotDraftConflict(); AddFieldHttpTest.php:297 |
| BL-24 | Open | domain value objects have no dedicated test and ~68 mutants between them | tests/F5Sign/Envelope/Unit/Domain/ValueObject/SettingsTest.php; tests/F5Sign/Envelope/Unit/Contract/Type/FieldPlacementTest.php |
| BL-39 | Open | This release is MIGRATE-BEFORE-DEPLOY, and the documented operator default is the reverse — the | ../f5sign-infra/Makefile migrate-prod comment: 'If the release brings a NON-additive one (RENAME...) this target goes BEFORE deploy-prod'; deploy.md:595 table row |
| BL-42 | Folded | `lock_config` / FieldMDP field locking. | FormRevisionPlanner.php:182 $locked = array_map(static fn(FieldFill $fieldFill): string => $fieldFill->name, $fill); new SignatureFieldDefinition(..., $locked) |
| BL-59 | Open | The signer wire contract changed, and the frontend has not been told. | f5sign-signer/app/composables/api/types.ts 'occurrences: FieldOccurrence[]'; rg 'field\.document_id/\.placement' f5sign-signer/app -> none. |
| BL-88 | Open | `POST /api/v1/signing-tokens` mints a token over an unvalidated envelope/recipient pair, and th | SigningTokenIssuance.php: `$context = $this->envelopes->getContextForRecipient(new GetEnvelopeContextForRecipient(...))` and `if ($context->sentAt === null) throw SigningTokenNotIssuableException::envelopeNotYetSent`; SigningCerem |
| BL-109 | Open | `CLAUDE.md`'s "Current state" is a version behind the architecture it instructs about. | CLAUDE.md: 'populated BC trees (Envelope, Session, SignatureExecution, Notification, IdentityAccess, Storage, KeyManagement)'; rule 4 (A) list with 'IDENTITY_DATABASE_URL, PROVISIONING_DATABASE_URL' |
| BL-112 | Open | From a git worktree, every main-stack tooling target validates a DIFFERENT checkout and reports | ../f5sign-infra/scripts/wt-validate.sh: GATES="${WT_GATES:-lint arch phpstan test}"; Makefile wt-backend target |
| BL-146 | Open | Nothing records that a recipient ACCESSED the envelope — opening a signing session emits no fac | src/F5Sign/Session/Domain/Aggregate/SigningSession.php: $session->record(new SigningSessionStarted(...)); src/F5Sign/Session/Contract/Event/SigningSessionStarted.php |
| BL-156 | Folded | `f5sign-signer`'s idle-recovery path stops working for gated envelopes, and it stops working wi | StartSessionController: 'if ($refresh === null) { return new JsonResponse($body, Response::HTTP_OK); }'; ../f5sign-signer/app/stores/useSessionStore.ts: 'if (!next.access_credential && !next.refresh_credential) return' |
| BL-159 | Open until `fi | A verified signing-gate proof is transferable | git merge-base --is-ancestor fix/signing-gate-on-the-act HEAD -> yes; SigningSession.php: '$challenge->markVerified($now); $this->answeredOnThisAct = $challenge;'; SubmitAuthResponseUseCase: 'if ($gate === AuthGate::SIGNING) { thr |
| BL-162 | Landed | A sender can declare a DELIVERED auth method on a recipient with no destination, and nothing te | AddRecipientUseCase.php:67 '$this->destinations->guard($command->authRequirement, $command->email, $command->phone);'; DeclaredMethodDestinations::guardMethod 'throw RecipientCannotReceiveMethodException::forSlot($slot, $method, $ |
| BL-172 | Landed | A recipient's phone number can be written and can never be read back, so the dashboard has no w | EnvelopeJsonPresenter.php: `'phone' => $recipient->phone,`; nelmio_api_doc.yaml: `phone: { type: string, example: '+34600123456', nullable: true }`; EnvelopeHttpTest: assertSame('+34600123456', $recipients[0]['phone'], 'in the cle |
| BL-173 | Closed — built | Closed on `feat/channel-selection` 2026-10-14 (pending merge): the text below describes the sta | src/F5Sign/Notification/Application/UseCase/NotifyActivatedStepRecipientsUseCase.php: $this->envelopeFacts->recordInvitationNotSent($envelope->id, $recipient->id, $unsentKind, ...) |
| BL-175 | Open | An unset `SENTRY_ENVIRONMENT` does not fail and does not read as unset — the SDK seals the even | config/packages/sentry.yaml: environment: '%env(SENTRY_ENVIRONMENT)%'; .env has only SENTRY_DSN= |
| BL-183 | Open | A recipient whose leg was DELEGATED or SKIPPED is invisible to both pre-credential routes, so t | IssueAuthChallengeUseCase: 'if (!$auth->gatePasses) { throw $auth->envelopeIsAlive ? SigningSessionUnavailableException::legClosed() : ...'; RecipientView::legIsClosed 'return $this->admittedAct !== null // $this->outcome->isTermi |
| BL-188 | Closed 2026-10 | A recipient who has signed cannot get their sealed copy back, and the refusal that stops them w | config/routes/api/copy.php exists; docs/adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md; CLAUDE.md Authn::COPY_LINK description |
| BL-194 | Closed — [TASK | Closed on `feat/channel-selection` 2026-10-14 (pending merge): [TASK-031](tasks/TASK-031-channe | NotifyActivatedStepRecipientsUseCase: if ($recipient->isUnclaimedSlot()) { continue; } |
| BL-211 | Folded | Two branches can mint the same migration version, and the merge conflict is the harmless half o | tests/F5Sign/Foundation/Unit/Architecture/MigrationVersionTest.php LAST_HAND_NUMBERED = '20260925000001' |
| BL-227 | Closed — built | Closed on `feat/channel-selection` 2026-10-14 (pending merge): the text below describes the sta | CorrectRecipientUseCase.php: $this->notificationChannels->guardContacts($recipient->notificationChannels(), $command->email ?? $recipient->email(), ...); NotifyCorrectedRecipientUseCase comment 'Since 2026-10-13 CorrectRecipientUs |
| BL-228 | Closed — built | Closed on `feat/channel-selection` 2026-10-14 (pending merge): the text below describes the sta | src/F5Sign/Envelope/Domain/Aggregate/Envelope.php resendInvitation(..., ResolvedNotificationChannels $reach, ...); RecipientNotResendableException.php:155,169 |
| BL-258 | Open | A linked git worktree lives INSIDE the main checkout, the workspace rules forbid exactly that s | git worktree list (4 entries, none inside f5sign-backend); ls -la worktrees: only . and ..; gitStatus clean |
| BL-273 | Landed | `trusted_proxies` was not configured, so the day anything sat in front of the PHP container, `s | config/packages/framework.yaml:9-10; .env:56 'SYMFONY_TRUSTED_PROXIES='; tests/F5Sign/Session/Integration/ObservedClientAddressTest.php requestUnder() |
| BL-286 | Landed | A decline recorded no browser-side evidence of its own | DeclineSignatureUseCase: '$session->decline(... signerIp: $command->sourceIp, signerUserAgent: $command->userAgent, signerAcceptLanguage: $command->acceptLanguage, reportedEvidence: $reported)'; DbalSigningSessionRepository: 'sign |
| BL-301 | Landed | `SignatureReadBack::signaturesIn()` promises to throw nothing, and a malformed response body es | src/F5Sign/SignatureExecution/Infrastructure/Pdf/DssHttpAdapter.php decoded(): catch (TransportExceptionInterface / DecodingExceptionInterface $e) { throw new DssUnavailableException(...) |
| BL-302 | Landed | The audit trail's gathering holds every signed document's final bytes in memory at once. | AuditTrailSources.php: `$finalDigests[$documentId] = $bytes->map(... PrefixDigests::of($read, $lengths)); ... unset($bytes);` |
| BL-308 | Open | A decline asks less of the recipient than a signature. | SigningSession::decline: if ($signingGateDeclared) { $this->consumeAnsweredSigningChallenge(SigningAct::DECLINE, $now); } |
| BL-319 | Open | Tests and the dev workers share the broker's vhost `/`, and the traffic goes both ways. | ../f5sign-infra/docker-compose.override.yml: RABBITMQ_TEST_VHOST: ${RABBITMQ_TEST_VHOST:-f5sign_test}; .env.test: .../f5sign_test |
| BL-406 | Closed | The relay ordered each slice by the TEXT of the transaction id, so a slice straddling a power o | src/F5Sign/Foundation/EventLog/EventRelay.php:347 and :481 'ORDER BY event_log.sys_transaction_id, sys_global_position' |
| BL-444 | Closed | The class docblock of `Version20261021095351` said a delegated or unclaimed recipient was "neve | migrations/Version20261021095351.php docblock: '`[]`, delegated, unclaimed slot — whatever the row held ..., never read: their refusals fire before the interval is checked.' |
| BL-469 | Closed 2026-10 | The receipt's `DECLARED_NONE` reservation sentence uses "destinatario" for two people, and a se | assets/evidence-audit/receipt.typ:237 [La parte declaró no formular reservas. Si firmó como destinatario en la entrega, la Ley 15/2009 (art. 60.1) ...] |
| BL-476 | Open | Production must inject `COPY_READ_CREDENTIAL_SECRET`, and the repo's authoring store still omit | ../f5sign-infra/docker-compose.prod.yml: COPY_READ_CREDENTIAL_SECRET: ${COPY_READ_CREDENTIAL_SECRET:?falta ...}; ../ai/f5sign-backend/CLAUDE.md rule 4 (A) lists it |

### Difieren solo en la etiqueta RESOLVED/OBSOLETE (3)

| Fila | Qué dice | Prueba |
|---|---|---|
| BL-22 | The eCMR reservation has no legal path onto the signed PDF, and its ownership is circular. | FormRevisionPlanner.php: `FieldType::TEXT, FieldType::DATE, FieldType::RESERVATIONS => FormFieldKind::TEXT` and `FieldType::RESERVATIONS === $field->type ? $owner->reservations : $field->value` |
| BL-135 | The ad-hoc container a worktree must use starts with a quarter of the memory the documented rou | ../f5sign-infra/docker-compose.wt.backend.yml:262 'Above the memory_limit of zz-wt-infection.ini (1536M)'; .claude/skills/task-runner/SKILL.md:110 only mkdir docker run |
| BL-185 | Passing a NEUTRAL access gate leaves no fact in the permanent log, so the commonest ceremony th | TrailAssembler.php:286 `$gates === [] && $atOpen->isSomeAnd(... === ExecutedAuthMethod::DIRECT_LINK) => ... LINK_POSSESSION_ONLY`; TrailJson.php:101 'access_method_at_open' |

### Desacuerdo real, resuelto en sesión principal (13)

| Fila | Qué dice | 1.ª / 2.ª | Decisión |
|---|---|---|---|
| BL-43 | Type-vocabulary reconciliation. | STILL_VALID / RESOLVED | La lista del modelo DDD sigue siendo la única discrepante, con banner fechado; enum y spec coinciden en 12. Cerrar corrigiendo esa línea (`docs/ddd/envelope-domain-model.md:90`). |
| BL-100 | A payload-shape change poisons messages already queued on the broker, and the drain meant to cl | RESOLVED / STILL_VALID | `f5sign-infra/docs/operations/deploy.md` §5 ya escribe la regla y cita BL-100; el agente a ciegas buscó con otras palabras y no lo vio. |
| BL-134 | The task-runner runs its phase-3 validations in parallel, and several of those skills work by S | PARTIAL / OBSOLETE | Comprobado: `doctrine-guard`, `contract-check-backend`, `task-validate-backend` y `security-audit-core` tienen 0 pasos de sabotaje, y solo `task-validate` usa el lane. La premisa desapareció. |
| BL-141 | `config/reference.php` means two different things and the written rule only covers one, so the  | STILL_VALID / OBSOLETE | Ninguna instrucción dice ya «reference.php sucio → revertir». Baja importancia: si se quiere la regla como tal, es decisión del owner. |
| BL-147 | Pulling any branch that registered a service makes PHPStan report that service as *"not registe | PARTIAL / RESOLVED | `make phpstan`, `make qa` y `wt-validate.sh` calientan el contenedor. Residuo menor: `composer phpstan` directo no; no es la ruta canónica. |
| BL-154 | A RabbitMQ *policy* is the escape hatch for setting `x-dead-letter-exchange` on the four event  | RESOLVED / PARTIAL | La vía de la policy ya está escrita donde mira un operador (`rabbitmq.md:63`), junto a `rabbit-check-dlx`. No hay comando `set_policy` literal: añadirlo sería una mejora, no el defecto de la fila. |
| BL-167 | `deptrac.yaml`'s `Vendor` collector reads like an allowlist and is not one, so the framework-in | STILL_VALID / RESOLVED | Lista `Vendor` cerrada y `composer arch` con `--fail-on-uncovered`. El «STILL_VALID» de la primera pasada venía de mi truncado; dos agentes con el texto la dan por resuelta. |
| BL-67 | The fields HTTP write edge is invisible to Infection, so its mutants are never attempted. | STILL_VALID / RESOLVED | `AddFieldControllerTest` existe con `#[CoversClass(AddFieldController::class)]`, justo el remedio que la fila nombra, y sus dos hermanos también lo tienen. |
| BL-126 | A new `RecipientOutcome` case cannot be added until the Session BC decides what a signing sessi | STILL_VALID / OBSOLETE | `DELIVERY_FAILED` ya no es un `RecipientOutcome`: la entrega pasó a su propia dimensión (ADR-0065). El `match` exhaustivo sigue, pero la pregunta que bloqueaba desapareció. |
| BL-289 | `CERTIFIED_DELIVERY` may decline (TASK-046 §4 D2: yes), but that role has no interactive read m | STILL_VALID / OBSOLETE | Un `CERTIFIED_DELIVERY` no puede llegar a un sobre enviado: `RoleStanding` lo marca `NOT_BUILT` y el envío lo rechaza. La pregunta volverá cuando se construya ese rol. |
| BL-288 | A recipient who declined cannot re-enter a `VOIDED` envelope once their session credential laps | STILL_VALID / OBSOLETE | ADR-0073 §2.15 y ADR-0088 lo responden: nunca se re-acuña sesión; la lectura posterior va por el par de copia, y un decliner solo ve su recibo. |

## B. Fusionar (16 grupos, −18 filas)

Todas confirmadas en el código por el agente adversario. `Debe conservar` es lo que no puede perderse al reescribir.

| Superviviente | Absorbe | Por qué es una sola | Debe conservar |
|---|---|---|---|
| BL-133 | BL-84 | Mismo defecto y sitio: eventos de IdentityAccess sin binding. | The disposition BL-133 reached (no queue until a consumer exists, binding in the same change as that consumer; no Reactor consumes IdentityAccess events) AND BL-84's filter-at-relay option and its category-(d) argument; the BL-32 registry-vs-bindings completeness check as the durable fix, with the e |
| BL-414 | BL-479 | La misma columna `notification.requested_at`, con precisión de segundos. | Both consequences (history order of two same-second notices falls to the random id; same-second older invitation stays PENDING and is sent beside the new one); the alternative fix for BL-414 (key the cancellation on the invitation's cause) and the fact that the invitation revocation is also compared |
| BL-344 | BL-345 | Falta el mismo acto `clocks` en el mismo arnés de carrera. | Both scenarios and their asserted outcomes: opening recorded => release reason OPENED_NO_ACT and credential minted, or not recorded and gate refuses with no credential, never the mix; commit admitted before the deadline counts and is not released, reverse order refuses the commit; both orders in eac |
| BL-209 | BL-388 | El mismo gate por ruta, visto desde el otro lado. | BL-209's design: per-route reachable-code set from collaborators followed transitively (including through the bus), red for reachable-but-unnamed, warning for named-but-unreachable, the 'enumerates at all' trigger (backticked UPPER_SNAKE), CorrectRecipientController as the discriminating fixture, th |
| BL-180 | BL-438 | Misma ruta y mismo `declares()` ausente; BL-438 es un redescubrimiento. | BL-180's predicate over BOTH slots (access and signing declares(ACCESS_CODE), as in AddRecipientController::generatedCodeFor and ChangeRecipientAuthRequirementController, Envelope.php ~2070), the disagreeing-slots test (access OTP_EMAIL + signing ACCESS_CODE => 200), the 200 => 422 behaviour change  |
| BL-182 | BL-435 | Mismo callback y misma lectura de dos slots; BL-435 es un redescubrimiento. | BL-182 whole (singular 201 vs plural 422, the stale message naming only singular fields, the equivalence broken against AuthRequirementRequest's 'two spellings of one declaration', the one-member-list-only reach due to ADR-0054 section 2.2, build the AuthRequirement once and ask declares(), the cens |
| BL-472 | BL-439 | Misma cabecera `no-store` y misma forma de test. | All 3 Envelope routes with a test per route, and the signing-side list: session open, session receipt, MintSigningTokenController, copy OTP send. ALSO add SubmitAuthResponseController: it mints access_credential/refresh_credential (OA text says so) and has no no-store, yet BL-472 does not list it (r |
| BL-55 | BL-382 | BL-382 es la ruta de commit de la tabla de límites por ruta. | BL-55's measured ~13x body-to-peak-memory ratio and the prod OOM argument (php-fpm 1g, pm.max_children=5, two concurrent bodies exceed the cgroup; rate limiter exists now but only for OTP sends, so nothing throttles these routes: the 'not installed' phrase in BL-55 is stale); BL-382's per-route targ |
| BL-390 | BL-118, BL-224 | Una sola costura de entrada de acuses (email y SMS). | Email side (async MTA bounce feed, TASK-025 note that only synchronous refusals are recoverable) and SMS side (Twilio status callback keyed on provider_reference); the route + signature verification + mapping onto Delivery and trace; the ordered-fallback consequence (ADR-0077 §2.6 only covers immedi |
| BL-161 | BL-482 | Mismo sitio y defecto; la copia viaja bajo la clave `link`. | Fix: redact Notification::SECRET_BEARING_VARIABLES (['link','code'], Notification.php:93) in render before composing the summary; this covers the copy link too since it uses key 'link', so state that. Keep the empty-exempted-set framing (authoring rule 5: DefaultChannelSelector never routes to LOG,  |
| BL-394 | BL-426 | Misma decisión del catálogo de ADR-0064. | The ADR-0078 facts to place (invitation outcomes, per-destination refusals, channel changes), the 'never says which destination' gap in recipient_delivery_failed, and BL-426's requirement that the sender need not poll the notification history; if the decision excludes delivery facts from the set, th |
| BL-217 | BL-226 | Un único filtro de suscripción; retitular sobre el filtro. | The filter-not-second-tier rule (no resolution order between levels); never key on ApiKey (revokedAt/rotation); never resolve from the event actor (2 of 11 census); deliver-on-missing-projection-row (no ordering, §2.8); the open decisions (projection vs other mechanism, backfill from Envelope read p |
| BL-171 | BL-49, BL-460 | BL-171 ya es el registro de columnas en claro. | Per-column entries, each with its own fact: BL-49 = maintainer declined encipherment 2026-09-21 (TASK-044 D9), Pii classification covers only the Sentry path while raw arrays on CommitSignature::$filledFields and FieldView::$value stay unredacted; BL-460 = recipient.reservations is written at admiss |
| BL-29 | BL-145 | Tras corregir BL-29, lo que queda en ambas es el log. | Rewrite BL-29 to its true residual: log path (RequestContextProcessor allow-list unenforced; Monolog not routed through SensitiveDataRedactor, ADR-0009 part 6 'logs'), plus OTel/span processors if adopted; keep 'closes when the LAST off-box sink calls the redactor'; fix the docblock in RequestContex |
| BL-130 | BL-275 | BL-275 es un subconjunto, con la misma realización de ADR-0096. | Update BL-130 to the remaining members (reservations x4, title, name, void reason; decline reason done). Carry from BL-275: the maintainer's 2026-09-21 decision to keep plaintext for now, options (a) inline cipher / (b) take text out of payloads and keep a commitment (sys_commitment forbids rewritin |
| BL-160 | BL-481 | Mismo sitio; ampliar a «variables con secreto de notification». | Window = creation to settlement; mechanism = SECRET_BEARING_VARIABLES + forgetSecretsOnceSettled; the pointer-to-closed-BL-113 rationale; the code is dead in 15 min while the copy link is long-lived (so the residual is more serious for the link); BL-481's 'ten purposes', AC-16 and TASK-071 W1 proven |

**Hallazgo nuevo en M8:** `SubmitAuthResponseController` también acuña credenciales sin `no-store` y no aparece en ninguna de las dos filas.


## C. Propuestas descartadas

| Propuesta | Decisión | Motivo |
|---|---|---|
| BL-303 + BL-351 | No fusionar | El agente confirmó, pero débil: es un censo columna a columna con disparadores distintos y una lista de columnas intocables. La fila fusionada sería las dos pegadas. |
| BL-413 + BL-446 | No fusionar | BL-413 no tiene tope; BL-446 está acotado por construcción (un contacto no se puede borrar). |
| BL-183 + BL-190 | No fusionar | BL-183 ya está resuelta; BL-190 sigue viva con otra premisa (rol, no resultado). |
| BL-159 + BL-197 | Sin objeto | BL-159 se cierra; BL-197 ya está en Closed. |
| BL-343 + BL-339 | Sin objeto | BL-339 ya está cerrada como la misma cosa; BL-343 sigue. |

Se revisaron además unas 110 parejas parecidas que se quedan separadas; están en la salida de la pasada de fusiones.

## D. Reescribir porque solo siguen vigentes en parte (42)

| Fila | Qué dice | Qué queda |
|---|---|---|
| BL-3 | design-repo path | Links in phpstan/README.md, phpstan/AUTHORING.md and docs/tasks/TASK-003 still point at ../../Arquitectura; either repoint or retire per the in-repo-only policy. |
| BL-4 | Add an early guard in [`DssHttpAdapter::seal()`](../src/F5Sign/SignatureExecution/Infrastructur | Guard (admit B-B and B-T, reject LT/LTA locally) not written; row's 'B-B only' wording is outdated. |
| BL-6 | [`UuidGenerator::v5()`](../src/F5Sign/Foundation/Identity/UuidGenerator.php) has **no test** (i | No direct byte-level v5 test in UuidGeneratorTest (known vectors); only one golden pin through SigningSessionId. Call-site count in row is stale. |
| BL-7 | The capture rule for this very file has no forcing function | Generated index and capture forcing function not built; section 9 lints not built. |
| BL-12 | [`AssignSigningController`](../src/F5Sign/Envelope/UI/Http/AssignSigningController.php) has **z | CAS-conflict through EnvelopeCommandAdapter seam is untested; the controller half of the row is stale (controller now has a unit test and an HTTP acceptance hit). |
| BL-17 | Nothing bounds the lock-across-DSS window | No cap on the holder's transaction (statement/idle-in-transaction timeout) nor on total window across N documents x DSS latency. |
| BL-18 | `WORKER_REPLICAS=1` is the latent bite condition for two open risks at once | The row names two bite conditions; one (BL-14) is gone. The lock-across-DSS half and the missing scaling warning remain; the row text should be cut down to BL-17 only. |
| BL-29 | The redaction layer now exists and nothing calls it, which is a narrower gap than before and a  | Solo la vía del log (Monolog no pasa por el redactor); Sentry ya está cubierto. |
| BL-50 | Nothing checks that a stored `validation.pattern` is a regular expression we can safely run — a | doc |
| BL-69 | Six write-edge authoring methods answer a replayed request six different ways, and the aggregat | addDocument y addRecipient siguen sin comprobar el id; addStep ya no ignora un minSignatures divergente. |
| BL-70 | No abuse control exists anywhere in the request path, and D4's 178 bits of credential entropy a | Abuse control on credential probing and the general edge/request path. |
| BL-93 | Two guards on the route-authn seam cannot fire as written. | (a) decide arm removal vs keep (docblock leans keep); (b) unverified whether assertion is discriminating; needs a sabotage run. |
| BL-97 | Test fixtures reach around the application with a privileged credential to fake preconditions,  | general fixture policy in tests/README.md; per-test cleanup for accumulating rows; the 'should shrink' premise is outdated |
| BL-98 | `DomainEventPayloadTest` claims to round-trip *"every transported DomainEvent"* while its provi | DomainEventPayloadTest's own provider still not tied to the registry discovery; the roster case it asks for is not built (the golden-bytes census guards a different property). |
| BL-130 | Six free-text fields across 8 of the 23 event types are neither pseudonymous nor references, in | reservations, title, name and the rest of the free text still in clear; no erasure path |
| BL-142 | Five signing routes the client already calls are classified by nothing, and the moment one is b | ADR-0049 §2.3 amendment classifying the four unbuilt routes (stated answer: session credential). |
| BL-144 | The session credential belongs to a LINK, and no server-side check can notice when a client for | Mitigation (echoed envelope_id) landed; row still describes it as uncosted and keeps the hazard open; could be closed or reworded. |
| BL-179 | No harness in this suite can prove that a MIGRATED row means what an authored one means, so [TA | Applying that replay pattern (expose statements, seed TEXT rows, replay, assert) to Version20260820000003; row's 'nothing does that today' wording is stale. |
| BL-181 | The published spec documents error STATUSES and almost never the `code`, so the one member cons | Per-route code documentation on sender routes still bare for many 4xx/5xx (ask 1). |
| BL-189 | A ceremony driven from a server is capped at ten SMS an hour for the whole integration, and the | Decision whether the per-API-client ceiling (100 SMS/h) is right and whether the row closes; token-route server-driven ceremonies still hit otp_sms_source. |
| BL-190 | A recipient whose ROLE has no ceremony — `CERTIFIED_DELIVERY`, `IN_PERSON_HOST` — is invited, o | Non-signing sendable roles (REVIEWER, VIEWER, EDITOR, and APPROVER's 'signing' copy) still get an OTP minted at routes 2 and 3 and the 'you are signing' sentence; role not crossed into RecipientAuthContext. The two non-interactive roles are now blocked at send, so the original trigger is gone until  |
| BL-200 | Presigned-direct download needs a tenant check where the URL is MINTED, and [ADR-0016](adr/ADR- | The directional rule (storage key never accepted from outside, only read from an authorised row) as an enforced check; mint-time tenant check when presigned-direct lands |
| BL-201 | Dos «30 días» independientes mantienen firmable un envelope, por coincidencia y con margen cero | PendingCustodySweep remedy (staging has no lifecycle rule); Pilar 7 B.2 alignment (off-repo) |
| BL-202 | Seis de los once `EnvelopeStatus` no los escribe nadie, y `expiresAt` no hace nada. | decide which of SEALING, CORRECTING, ROUTING_FAILED, SEALING_FAILED are real states and drop the rest |
| BL-215 | The delegated commit takes a row lock and nothing proves it does. | Two-concurrent-calls test for bars 13/18 not built; the lock itself is now probed. |
| BL-234 | UNA TRANSACCIÓN LARGA EN CUALQUIER SITIO PARA LA PUBLICACIÓN DE EVENTOS DE TODOS LOS TENANTS, y | Monitoring + time ceiling (the row's first-priority remedies) unbuilt; revocation fan-out unbounded; signing-with-DSS-in-transaction stall remains. |
| BL-236 | `config/` is PHP, it is what boots the process, and NOT ONE of the three static gates reads it  | config/ (and public/) not scanned by any static gate; migrations/ and config/ not in php-cs-fixer's finder (PSR-12/@see convention unenforced there); CLAUDE.md ad-hoc re-check recommendation unchanged. |
| BL-261 | A recipient who signed out of turn BEFORE this fix is now permanently refused their own signed  | Still refused while the envelope is open; the operational census/repair of the incident envelope (TASK-042 section 7) is not something the repo can show; row's 'permanent' wording is stale for ended envelopes. |
| BL-267 | Signing-ceremony responses promise no member: objects in published responses declare no `requir | 201 of POST /api/v1/signing-tokens and nested objects of GET /api/v1/signing/session 200 still lack required; the commit 200 part was not independently verified. |
| BL-311 | SignatureExecution's signing act and annulment seal recognise a redelivery only after doing the | A recipient who committed no signature image still has their redelivery redo DSS work before ArtifactAlreadyAppendedException. |
| BL-316 | Comments in config, tests and code, and `CLAUDE.md`, state facts that the tree contradicts. | Items 1, 2, 5, 7 (stale comments in RouteCollisionTest, routes.yaml, services.yaml, OnSessionCompletedHandler/OnSessionCompleted). |
| BL-323 | Nothing reports an issued audit trail that the custodian did not conserve. | Per-trail detector of issued trails not at their ceiling; row text claim of 'nothing says so' is outdated for job outage |
| BL-324 | `ConserveTrailsCommand`'s per-tenant failure branch has no test. | A test where the trail repository's unconserved() throws for one tenant. |
| BL-341 | The official TASK-050 handoffs do not yet cover the veto end causes. | The integrator handoff still lacks the RECIPIENT_VETOED end cause (the decline-by-vetoer path); the row closes only when both handoffs carry both causes. |
| BL-366 | Nothing checks that a placement fits its page, and a seal that cannot succeed reads as done. | (1),(2),(3),(5) remain; (4) done for envelope documents only. |
| BL-395 | `Envelope::markRecipientDeliveryFailed()` stamped `invitation_failed_at` before the closed-leg  | Unconditional save in the markRecipientDeliveryFailed adapter path (low-severity, no write correctness issue shown). |
| BL-461 | Edge cases of the form engine left at low confidence by the closing review. | (b) redelivery without a committed image still re-runs engine+DSS; (d) both docblocks narrower than behaviour; (e) no end-to-end case through the real script for AC-16a/b. |
| BL-14 | (ver la tabla de refutación) | If the row is narrowed: 'BL-14 (narrowed): the CAS-loser orphan is gone. Open: CustodyObligationService::strengthen failing after bytes->copy leaves a COMPLIANCE-locked retained object with no row, and the next sweep copies again under a new placement; unrecorded bytes in staging or retained have de |
| BL-168 | (ver la tabla de refutación) | Keep the row, narrowed. Closed: the row's worst case, a third party holding link and code, when the corrected contact is a declared notification channel, because the link and credentials are retired. Still broken, at a live 15-minute TTL: (a) when no declared channel covers the corrected contact, in |
| BL-176 | (ver la tabla de refutación) | Row text to keep: 'The contradiction is decided (option a). Open: an unclaimed slot is refused at the mint and the copy link but not at machine_auth_otp_send, machine_auth_submit or commit_delegated_signature; the last publishes RECIPIENT_SLOT_NOT_CLAIMED and never throws it (TASK-033 §6 bar 20 has  |
| BL-204 | (ver la tabla de refutación) | Row text to keep: 'Decision 8's clear-text half is answered by ADR-0096 §2.1, §2.6. Open: ADR-0032 decision 7 still stands while RecipientClaimed carries no identity. Decide before the first deployment with real data, because each claim logged then lacks it for good: retire decision 7 for this event |
| BL-205 | (ver la tabla de refutación) | The ordinary path is fixed and tested, but the row's resolution rests on 'an unclaimed slot cannot have opened one', and that is false on the machine surface. One machine key call to the OTP send or answer twin on an unclaimed slot stamps first_opened_at, even when the call then fails with no destin |

## E. No decidibles desde el código (se quedan)


BL-9, BL-21, BL-30, BL-31, BL-34, BL-139, BL-140, BL-174, BL-238, BL-292, BL-356, BL-389, BL-404, BL-409, BL-433, BL-440. Requieren una ejecución en vivo, un dato externo, legal u otro repo.


## Al aplicar

- Los ids no se renumeran: una fila absorbida pasa a Closed con `Merged into BL-N`.
- Por cada fila cerrada o fusionada, `rg 'BL-NNN' src tests migrations config docs` leído por tiempo verbal. BL-14 y BL-183 están citadas en 13 y 14 ficheros.
- BL-18 pierde la mitad de BL-14 al cerrarse esta. BL-234 se mantiene la primera, y su nota de cabecera sigue siendo cierta.
- Comprobar antes que `develop` no se ha movido: tres worktrees siguen abiertos y pueden traer filas nuevas.


Datos crudos junto a este fichero: `first-pass.json`, `blind-recheck.json`, `second-pass.json`, `closure-refutation.json`, `resolving-commits.json`, `merge-review.json`, `near-misses.json`.
