# F5Sign — Workspace (repo interno)

Repo **privado e interno** que ensambla el workspace de F5Sign y centraliza toda la
configuración de IA (Claude). **Nunca se entrega al cliente.** Los subrepos de producto
son independientes y NO deben contener rastro de IA.

## Estructura

```
f5sign/                  ← este repo (interno/privado)
├─ ai/                   ← FUENTE DE VERDAD de la config IA
│  ├─ shared/            ← skills idénticas en todos los repos que las usan
│  └─ f5sign-*/          ← CLAUDE.md + .claude/ propios de cada subrepo
├─ bin/
│  ├─ bootstrap.sh       ← clona los subrepos (repos.manifest) + sincroniza IA
│  ├─ sync-ai.sh         ← crea los symlinks de IA en cada subrepo (idempotente)
│  ├─ unlink-ai.sh       ← revierte: quita symlinks y restaura ficheros reales
│  ├─ import-ai-from-repos.py  ← (one-shot) reconstruye ai/ desde los subrepos
│  └─ purge-ai-history.sh      ← (FASE 4, destructiva) purga IA del historial
├─ notes/                ← handoffs y notas internas de trabajo
├─ repos.manifest        ← lista de subrepos (nombre/url/rama) para bootstrap
└─ f5sign-*/             ← subrepos (ignorados por este repo)
```

## Montar el workspace de cero

```bash
git clone <este-repo> f5sign && cd f5sign
bin/bootstrap.sh          # clona subrepos + distribuye la IA por symlink
```

## Día a día

- **Una tarea = un repo.** `cd f5sign-<repo>` y trabaja ahí (lanza `/task-runner T…`).
  Cada subrepo lee su `CLAUDE.md` y sus skills vía los symlinks al store `ai/`.
- **Editar config IA:** se edita el store `ai/` (a través del symlink desde el repo o
  directamente). `ai/shared/<skill>` cambia para todos los repos que la enlazan.
- **Tras clonar/actualizar un subrepo:** re-ejecuta `bin/sync-ai.sh`.

## Secreto (sin rastro de IA en los subrepos)

- Los ficheros IA llegan a los subrepos como **symlinks** ignorados vía
  `.git/info/exclude` (local, no commiteado → no se autodelata).
- `includeCoAuthoredBy: false` evita firmar commits con rastro de Claude.
- **Pendiente (FASE 4):** los `.claude/`/`CLAUDE.md` siguen *trackeados* en el historial
  de los subrepos (silenciados con `skip-worktree`). `bin/purge-ai-history.sh` los purga
  del historial + limpia mensajes de commit. Es destructivo y se ejecuta aparte.
