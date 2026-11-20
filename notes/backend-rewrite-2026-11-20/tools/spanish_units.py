#!/usr/bin/env python3
"""Lines of Spanish prose (comments, docs) in every kept blob of history, product copy excluded.

Literal search only. Usage: python3 -I spanish_units.py <repo-dir> <out.jsonl>
"""
import json
import subprocess
import sys

repo, out = sys.argv[1], sys.argv[2]
REMOVED = ('docs/tasks/', 'docs/frontend-handoff/', 'docs/infra-handoff/', 'docs/tooling-handoff/',
           'docs/BACKLOG.md', 'CLAUDE.md', '.claude/')
# Spanish here is the product's own copy, or a test asserting it: never translated.
PRODUCT = ('assets/', 'templates/', 'translations/', 'tests/', 'src/Innasign/Notification/Infrastructure/Channel/',
           'src/F5Sign/Notification/Infrastructure/Channel/')
SKIP_SUFFIX = ('.lock', '.ttf', '.otf', '.pdf', '.png', '.jpg', '.zip', '.p12', '.der', '.json')
STRONG = [' porque ', 'también', ' está ', ' están ', 'según', ' aquí', 'propósito', ' sólo ', ' hay que ',
          ' ya existe', ' no tocan', 'contenedor', ' cuando ']
WEAK = [' que ', ' para ', ' los ', ' las ', ' una ', ' del ', ' sin ', ' pero ', ' con ', ' por ', ' el ', ' la ']

objs = subprocess.run(['git', '-C', repo, 'rev-list', '--objects', '--all'],
                      capture_output=True, text=True, check=True).stdout.splitlines()
path_of = {}
for row in objs:
    sha, _, path = row.partition(' ')
    if path and sha not in path_of:
        path_of[sha] = path
blobs = [s for s, p in path_of.items()
         if not p.startswith(REMOVED + PRODUCT) and not p.endswith(SKIP_SUFFIX)]
units = {}
proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for sha in blobs:
    proc.stdin.write((sha + '\n').encode())
    proc.stdin.flush()
    header = proc.stdout.readline().split()
    size = int(header[2]) if len(header) >= 3 else 0
    data = proc.stdout.read(size)
    proc.stdout.read(1)
    if len(header) < 3 or header[1] != b'blob' or b'\x00' in data[:8000]:
        continue
    for line in data.decode('utf-8', 'replace').split('\n'):
        low = ' ' + line.lower() + ' '
        strong = sum(1 for n in STRONG if n in low)
        weak = sum(1 for n in WEAK if n in low)
        if strong >= 1 and weak >= 1 or weak >= 4:
            u = line.strip(' ')
            e = units.setdefault(u, {'unit': u, 'count': 0, 'paths': []})
            e['count'] += 1
            if path_of[sha] not in e['paths'] and len(e['paths']) < 3:
                e['paths'].append(path_of[sha])
proc.stdin.close()
proc.wait()
with open(out, 'w') as f:
    for e in sorted(units.values(), key=lambda e: e['paths'][0]):
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
print('spanish units:', len(units))
