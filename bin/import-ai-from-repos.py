#!/usr/bin/env python3
"""One-shot: importa la config IA (CLAUDE.md + .claude/) de cada subrepo al store
central `ai/`, y deduplica en `ai/shared/` las skills que son byte-idénticas entre
repos. NO toca los subrepos. Re-ejecutable (reconstruye `ai/` desde cero).

Uso:  python3 bin/import-ai-from-repos.py
"""
import os
import shutil
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent.parent
AI = ROOT / "ai"
REPOS = [
    "f5sign-backend",
    "f5sign-dashboard",
    "f5sign-docs",
    "f5sign-infra",
    "f5sign-signer",
]


def dir_hash(p: Path) -> str:
    """Hash estable del contenido de un directorio (ficheros, symlinks y estructura)."""
    h = hashlib.sha256()
    for f in sorted(p.rglob("*")):
        rel = f.relative_to(p).as_posix()
        if f.is_symlink():
            h.update(b"L" + rel.encode() + b"\0" + os.readlink(f).encode() + b"\0")
        elif f.is_file():
            h.update(b"F" + rel.encode() + b"\0")
            h.update(f.read_bytes())
        elif f.is_dir():
            h.update(b"D" + rel.encode() + b"\0")
    return h.hexdigest()


# 1) Copiar cada repo al store
for repo in REPOS:
    src = ROOT / repo
    dst = AI / repo
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    claude_md = src / "CLAUDE.md"
    if claude_md.is_file():
        shutil.copy2(claude_md, dst / "CLAUDE.md")
    claude_dir = src / ".claude"
    if claude_dir.is_dir():
        shutil.copytree(claude_dir, dst / ".claude", symlinks=True)
    print(f"importado {repo}: CLAUDE.md={'sí' if claude_md.is_file() else 'NO'} .claude={'sí' if claude_dir.is_dir() else 'NO'}")

# 2) Hash de cada skill por repo
skill_hashes = defaultdict(dict)  # skill -> {repo: hash}
for repo in REPOS:
    sk = AI / repo / ".claude" / "skills"
    if sk.is_dir():
        for d in sorted(sk.iterdir()):
            if d.is_dir():
                skill_hashes[d.name][repo] = dir_hash(d)

# 3) Deduplicar: por cada skill, el hash más común entre repos que lo tienen;
#    si >=2 repos comparten ese hash exacto -> a ai/shared/ + symlink relativo.
SHARED = AI / "shared"
if SHARED.exists():
    shutil.rmtree(SHARED)
SHARED.mkdir(parents=True)
print("\n=== DEDUP DE SKILLS ===")
for skill, rh in sorted(skill_hashes.items()):
    cnt = Counter(rh.values())
    canon_hash, freq = cnt.most_common(1)[0]
    # Compartir SOLO si es byte-idéntico en TODOS los repos que tienen la skill
    # (y al menos 2). Si diverge front/back, se queda per-repo en cada repo.
    if len(rh) >= 2 and freq == len(rh):
        src_repo = next(iter(rh))
        shared_dst = SHARED / skill
        if not shared_dst.exists():
            shutil.copytree(AI / src_repo / ".claude" / "skills" / skill, shared_dst, symlinks=True)
        for r in rh:
            tgt = AI / r / ".claude" / "skills" / skill
            shutil.rmtree(tgt)
            rel = os.path.relpath(shared_dst, tgt.parent)
            os.symlink(rel, tgt)
        print(f"  SHARED   {skill:32} <- {', '.join(sorted(rh))}")
    elif len(rh) >= 2:
        print(f"  per-repo {skill:32} <- {', '.join(sorted(rh))}  (VARIANTES: {len(set(rh.values()))} distintas)")
    else:
        print(f"  per-repo {skill:32} <- {', '.join(sorted(rh))}")

print("\nStore construido en", AI)
