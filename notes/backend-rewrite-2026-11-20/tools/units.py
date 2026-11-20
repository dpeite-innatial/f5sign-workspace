#!/usr/bin/env python3
"""Extract rewrite units (the sentence around each hit) from every kept blob in history.

Literal search only: needles are plain substrings, sentence edges are found with str.rfind/str.find.
Usage: python3 -I units.py <repo-dir> <out.jsonl>
Each output row: {"unit": <exact text>, "kind": <needle group>, "count": n, "paths": [...up to 3]}
"""
import collections
import json
import subprocess
import sys

repo, out = sys.argv[1], sys.argv[2]

REMOVED = ('docs/tasks/', 'docs/frontend-handoff/', 'docs/infra-handoff/', 'docs/tooling-handoff/',
           'docs/BACKLOG.md', 'CLAUDE.md', '.claude/')
SKIP_SUFFIX = ('.lock', '.ttf', '.otf', '.pdf', '.png', '.jpg', '.zip', '.p12', '.der')
PROSE = ('docs/', 'README.md', 'tests/README.md', 'phpstan/README.md', 'phpstan/AUTHORING.md')

GROUPS = {
    'claude': ['claude'],
    'agent': [' agent ', ' agent,', ' agent.', ' agent-', ' agents', 'agent-only', 'agent-reachable',
              'agent-facing', 'agent work', 'an agent'],
    'workflow': ['skill', 'task-runner', 'var/task-runner', 'subagent'],
}
# session-of-an-agent phrasings; only looked for in prose files, where the domain's signing session is rarer
SESSION = ['this session', 'a session th', 'the session that', 'peer session', 'another session', 'two sessions',
           'a later session', 'fresh session', 'next session', 'same session that', 'sessions at once',
           'one session', 'the session which']

objs = subprocess.run(['git', '-C', repo, 'rev-list', '--objects', '--all'],
                      capture_output=True, text=True, check=True).stdout.splitlines()
path_of = {}
for row in objs:
    sha, _, path = row.partition(' ')
    if path and sha not in path_of:
        path_of[sha] = path
blobs = [s for s, p in path_of.items() if not p.endswith(SKIP_SUFFIX) and not p.startswith(REMOVED)]


def sentence(text, pos):
    """The sentence holding text[pos]: it starts on the hit's own line and may run on for up to three
    more lines, so a citation wrapped across a comment's line break stays in one unit."""
    line_start = text.rfind('\n', 0, pos) + 1
    start = line_start
    for edge in ('. ', '| ', '; '):
        k = text.rfind(edge, line_start, pos)
        if k != -1 and k + 2 > start:
            start = k + 2
    limit = pos
    for _ in range(4):
        nl = text.find('\n', limit)
        if nl == -1:
            limit = len(text)
            break
        limit = nl + 1
    end = limit
    for edge in ('. ', '.\n', ' |', '; ', '\n\n', '*/'):
        k = text.find(edge, pos, limit)
        if k != -1 and k + 1 < end:
            end = k + 1
    return text[start:end].rstrip('\n')


units = {}
proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for sha in blobs:
    proc.stdin.write((sha + '\n').encode())
    proc.stdin.flush()
    header = proc.stdout.readline().split()
    size = int(header[2]) if len(header) >= 3 else 0
    data = proc.stdout.read(size)
    proc.stdout.read(1)
    if len(header) < 3 or header[1] != b'blob' or b'\x00' in data[:8000] or size > 3_000_000:
        continue
    path = path_of[sha]
    groups = dict(GROUPS)
    if path.startswith(PROSE) or path.endswith('.md'):
        groups['session'] = SESSION
    text = data.decode('utf-8', 'replace')
    offset = 0
    for line in text.split('\n'):
        low = line.lower()
        line_offset = offset
        offset += len(line) + 1
        if 'user agent' in low or 'user-agent' in low or 'useragent' in low:
            low = low.replace('user agent', ' ' * 10).replace('user-agent', ' ' * 10).replace('useragent', ' ' * 9)
        for kind, needles in groups.items():
            for n in needles:
                pos = low.find(n)
                if pos != -1:
                    u = sentence(text, line_offset + pos).strip(' ')
                    if u:
                        e = units.setdefault(u, {'unit': u, 'kind': kind, 'count': 0, 'paths': []})
                        e['count'] += 1
                        if path not in e['paths'] and len(e['paths']) < 3:
                            e['paths'].append(path)
                    break
proc.stdin.close()
proc.wait()
with open(out, 'w') as f:
    for e in sorted(units.values(), key=lambda e: (e['kind'], -e['count'])):
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
c = collections.Counter(e['kind'] for e in units.values())
print('units:', len(units), dict(c))
