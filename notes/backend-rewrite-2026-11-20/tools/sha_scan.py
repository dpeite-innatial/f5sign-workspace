#!/usr/bin/env python3
"""Find every citation of a commit hash inside the cleaned history's blobs (and messages).

Usage: python3 -I sha_scan.py <orig-repo> <clean-repo> <out.json>
A token is a run of 7-40 lowercase hex characters bounded by non-alphanumerics that is the prefix of an
ORIGINAL commit (the blobs were written before the rewrite, so they cite original hashes), or of a cleaned
commit (filter-repo already rewrote hashes inside commit messages). Scanned character by character; no regex.
Output: {"orig_to_clean": {orig: clean-or-ancestor}, "blobs": {blob: [token, ...]}, "stats": {...}}
"""
import json
import subprocess
import sys

orig_repo, clean_repo, out = sys.argv[1:4]
HEX = set('0123456789abcdef')
ALNUM = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')


def git(repo, *a):
    return subprocess.run(['git', '-C', repo] + list(a), capture_output=True, text=True, check=True).stdout


cmap = {}
for ln in open(f'{clean_repo}/.git/filter-repo/commit-map').read().split('\n')[1:]:
    if ln.strip():
        o, n = ln.split()
        cmap[o] = n
NULL = '0' * 40
# a pruned commit is cited as the nearest kept ancestor (its tree is what the citation meant, minus docs)
parents = {}
for ln in git(orig_repo, 'rev-list', '--all', '--parents').split('\n'):
    if ln:
        f = ln.split()
        parents[f[0]] = f[1:]


def resolve(o):
    seen = 0
    while o and cmap.get(o, NULL) == NULL and seen < 500:
        ps = parents.get(o) or []
        o = ps[0] if ps else None
        seen += 1
    return cmap.get(o) if o else None


orig_full = list(parents)
by_prefix = {}
for s in orig_full:
    by_prefix.setdefault(s[:7], []).append(s)


def tokens(text):
    found = []
    i, n = 0, len(text)
    while i < n:
        if text[i] in HEX and (i == 0 or text[i - 1] not in ALNUM):
            j = i
            while j < n and text[j] in HEX:
                j += 1
            if 7 <= j - i <= 40 and (j == n or text[j] not in ALNUM):
                tok = text[i:j]
                cands = [s for s in by_prefix.get(tok[:7], []) if s.startswith(tok)]
                if len(cands) == 1 and any(ch.isalpha() for ch in tok) and any(ch.isdigit() for ch in tok):
                    found.append((tok, cands[0]))
            i = j + 1
        else:
            i += 1
    return found


objs = git(clean_repo, 'rev-list', '--objects', '--all').split('\n')
blob_ids = sorted({ln.split(' ', 1)[0] for ln in objs if ' ' in ln and not ln.endswith(('.lock', '.ttf', '.pdf', '.png'))})
proc = subprocess.Popen(['git', '-C', clean_repo, 'cat-file', '--batch'], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE)
blobs = {}
used = {}
for b in blob_ids:
    proc.stdin.write((b + '\n').encode())
    proc.stdin.flush()
    h = proc.stdout.readline().split()
    size = int(h[2]) if len(h) > 2 else 0
    data = proc.stdout.read(size)
    proc.stdout.read(1)
    if len(h) < 3 or h[1] != b'blob' or b'\x00' in data[:8000]:
        continue
    ts = tokens(data.decode('utf-8', 'replace'))
    if ts:
        blobs[b] = sorted({t for t, _ in ts})
        for t, o in ts:
            used[t] = o
proc.stdin.close()
proc.wait()
orig_to_clean = {}
pruned = 0
for t, o in used.items():
    c = resolve(o)
    if cmap.get(o, NULL) == NULL:
        pruned += 1
    orig_to_clean[t] = c
json.dump({'token_to_clean': orig_to_clean, 'blobs': blobs,
           'stats': {'blobs_with_tokens': len(blobs), 'distinct_tokens': len(used), 'pruned_targets': pruned,
                     'unresolved': sum(1 for v in orig_to_clean.values() if not v)}}, open(out, 'w'))
print(json.load(open(out))['stats'])
