#!/usr/bin/env python3
"""Inventory of AI traces across every blob reachable in a repo's history.

Literal substring search only (no regexes). Usage:
    python3 -I inventory.py <repo-dir> <out-dir>
Writes <out-dir>/summary.txt and one <token>.lines.tsv per token (count \t path \t line).
"""
import collections
import os
import subprocess
import sys

repo, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

# token -> list of literal needles (matched against the lowercased line)
TOKENS = {
    'claude': ['claude'],
    'anthropic': ['anthropic'],
    'models': ['opus', 'sonnet', 'haiku'],
    'subagent': ['subagent', 'sub-agent'],
    'agent-workflow': ['task-runner', 'slice-implementer', 'slice-reviewer', 'plan-runner', 'test-runner',
                       'replicator', 'skill', 'var/task-runner'],
    'agent-word': [' agent', 'agents'],
    'innasign': ['innasign', 'innatial', 'dpeite'],
    'devenv': ['scratchpad', 'workspace root', 'workspace-root', 'workspace repo', "workspace's", 'offrepo', 'innatial'],
    'glyphs': ['⚑', '⛔', '⚠', '⛑'],
}
REMOVED = ('docs/tasks/', 'docs/frontend-handoff/', 'docs/infra-handoff/', 'docs/tooling-handoff/',
           'docs/BACKLOG.md', 'CLAUDE.md', '.claude/')


def area_of(path):
    if path.startswith(REMOVED):
        return 'REMOVED'
    parts = path.split('/')
    return '/'.join(parts[:2]) if parts[0] == 'docs' and len(parts) > 1 else parts[0]


SKIP_SUFFIX = ('.lock', '.ttf', '.otf', '.pdf', '.png', '.jpg', '.zip', '.p12', '.der')

objs = subprocess.run(['git', '-C', repo, 'rev-list', '--objects', '--all'],
                      capture_output=True, text=True, check=True).stdout.splitlines()
path_of = {}
for row in objs:
    sha, _, path = row.partition(' ')
    if path and sha not in path_of:
        path_of[sha] = path
blobs = [s for s, p in path_of.items() if not p.endswith(SKIP_SUFFIX)]

proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
lines = {t: collections.Counter() for t in TOKENS}
blobs_hit = collections.Counter()
paths_hit = {t: collections.Counter() for t in TOKENS}
for sha in blobs:
    proc.stdin.write((sha + '\n').encode())
    proc.stdin.flush()
    header = proc.stdout.readline().split()
    if len(header) < 3 or header[1] != b'blob':
        if len(header) >= 3:
            proc.stdout.read(int(header[2]) + 1)
        continue
    data = proc.stdout.read(int(header[2]))
    proc.stdout.read(1)
    if b'\x00' in data[:8000] or len(data) > 3_000_000:
        continue
    text = data.decode('utf-8', 'replace')
    path = path_of[sha]
    for line in text.split('\n'):
        low = line.lower()
        for tok, needles in TOKENS.items():
            for n in needles:
                if n in low:
                    if tok == 'agent-word' and 'user agent' in low or tok == 'agent-word' and 'user-agent' in low:
                        break
                    lines[tok][(area_of(path), line.strip()[:400])] += 1
                    paths_hit[tok][path] += 1
                    break
proc.stdin.close()
proc.wait()

with open(os.path.join(out, 'summary.txt'), 'w') as s:
    s.write(f'blobs scanned: {len(blobs)}\n')
    for tok in TOKENS:
        s.write(f'{tok}: {sum(lines[tok].values())} line-occurrences, {len(lines[tok])} distinct lines, '
                f'{len(paths_hit[tok])} paths\n')
        top = collections.Counter()
        for (area, _), c in lines[tok].items():
            top[area] += c
        s.write('   by top dir: ' + ', '.join(f'{a}={c}' for a, c in top.most_common(8)) + '\n')
for tok in TOKENS:
    with open(os.path.join(out, f'{tok}.lines.tsv'), 'w') as f:
        for (area, line), c in lines[tok].most_common():
            f.write(f'{c}\t{area}\t{line}\n')
