#!/usr/bin/env python3
"""Phase 2, step 1: describe every commit of the cleaned history as JSON, for the planner.

Usage: python3 -I graph_extract.py <repo-dir> <out.json>
Per commit: sha, parents, author, email, author/committer epoch and tz, subject, body,
lines (added+deleted, lock files excluded), files, first-parent membership of develop and master,
the branch a merge brought it in from, and the task id its subject or body names.
Literal parsing only.
"""
import json
import subprocess
import sys

repo, out = sys.argv[1], sys.argv[2]
SEP = '\x1e'
FMT = SEP.join(['%H', '%P', '%an', '%ae', '%at', '%ai', '%ct', '%s', '%b']) + '\x1f'


def git(*args):
    return subprocess.run(['git', '-C', repo] + list(args), capture_output=True, text=True, check=True).stdout


commits = {}
for rec in git('log', '--all', '--topo-order', '--reverse', '--format=' + FMT).split('\x1f'):
    rec = rec.strip('\n')
    if not rec:
        continue
    f = rec.split(SEP)
    sha, parents, an, ae, at, ai, ct, subject, body = f[:9]
    commits[sha] = {
        'sha': sha, 'parents': parents.split() if parents else [], 'author': an, 'email': ae,
        'at': int(at), 'tz': ai[-5:], 'ct': int(ct), 'subject': subject, 'body': body.strip(),
        'lines': 0, 'files': [],
    }
cur = None
for ln in git('log', '--all', '--format=@%H', '--numstat', '--no-renames').split('\n'):
    if ln.startswith('@'):
        cur = commits[ln[1:]]
        continue
    parts = ln.split('\t')
    if cur is not None and len(parts) == 3:
        cur['files'].append(parts[2])
        n = 0 if parts[0] == '-' else int(parts[0]) + int(parts[1])
        cur.setdefault('file_lines', {})[parts[2]] = n
        if not parts[2].endswith('.lock'):
            cur['lines'] += n

for ref in ('develop', 'master'):
    for sha in git('rev-list', '--first-parent', ref).split():
        commits[sha].setdefault('first_parent_of', []).append(ref)


def task_of(text):
    for key in ('task-', 'TASK-'):
        i = text.find(key)
        while i != -1:
            j = i + 5
            digits = ''
            while j < len(text) and text[j].isdigit() and len(digits) < 3:
                digits += text[j]
                j += 1
            if len(digits) == 3:
                return 'TASK-' + digits
            i = text.find(key, i + 1)
    return None


for c in commits.values():
    c['task'] = task_of(c['subject']) or task_of(c['body'][:400])

# Which merge brought a commit in: walk each merge's second parent back to the merge base.
for m in commits.values():
    if len(m['parents']) != 2:
        continue
    name = m['subject']
    if name.startswith('Merge '):
        rest = name[6:]
        if rest.startswith("branch '"):
            rest = rest[8:]
            name = rest[:rest.find("'")] if "'" in rest else rest
        else:
            cut = min([k for k in (rest.find(':'), rest.find(' ')) if k != -1] or [len(rest)])
            name = rest[:cut]
    m['merged_branch'] = name
    for sha in git('rev-list', m['parents'][1], '^' + m['parents'][0]).split():
        commits[sha].setdefault('brought_by', m['sha'])
        commits[sha].setdefault('branch', name)

with open(out, 'w') as fh:
    json.dump(list(commits.values()), fh)
print('commits', len(commits), 'merges', sum(1 for c in commits.values() if len(c['parents']) > 1))
