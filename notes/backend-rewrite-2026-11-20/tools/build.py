#!/usr/bin/env python3
"""Phase 2, step 4: build the new history from the plan, with git plumbing only.

Usage: python3 -I build.py <repo> <plan.json> <msgs-dir> <sha_cites.json> <report.json>
<repo> is a throwaway clone of the cleaned history (its objects are the source of every tree and blob);
the new commits are written into it and its develop/master/tags are moved onto them at the end.

Per plan node:
  tree    normal / real merge / fakemerge: the tree of its last original commit; split-final: the tree of
          the original oversized commit; part: the previous slice's tree plus this slice's files.
          Then every blob citing a commit hash gets the hash of that commit's new counterpart.
  message the rewritten message, with commit hashes it cites mapped the same way.
  author  name and e-mail of Daniel or Miguel; committer = author; both dates = the planned instant.
No regular expressions: hash tokens are found by scanning characters.
"""
import json
import os
import subprocess
import sys
import tempfile

repo, plan_file, msgs_dir, cites_file, report_file = sys.argv[1:6]
EMAIL = {'Daniel Vilar': 'daniel.vilar@innatial.com', 'Miguel Melon': 'miguel.melon@innatial.com'}
HEX = set('0123456789abcdef')
ALNUM = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
idx_file = tempfile.mktemp(prefix='build-idx-')


def git(*a, inp=None, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(['git', '-C', repo] + list(a), input=inp, capture_output=True, env=e)
    if r.returncode != 0:
        raise RuntimeError(f'git {a[:3]} failed: {r.stderr.decode()[:400]}')
    return r.stdout


plan = json.load(open(plan_file))
msgs = {}
for f in sorted(os.listdir(msgs_dir)):
    if f.startswith('batch_') and f.endswith('.out.jsonl'):
        for ln in open(os.path.join(msgs_dir, f), encoding='utf-8'):
            row = json.loads(ln)
            msgs[row['id']] = row['message']
missing = [p['id'] for p in plan if p['id'] not in msgs]
if missing:
    sys.exit(f'messages missing for {len(missing)} nodes, e.g. {missing[:5]}')
cites = json.load(open(cites_file))
token_to_clean = cites['token_to_clean']          # token in a blob -> cleaned-history commit
blob_tokens = cites['blobs']                       # blob id -> tokens it contains

# which node stands for a cleaned commit: the node holding its full tree
node_of_clean = {}
for p in plan:
    if p['kind'] in ('normal', 'split-final'):
        for m in p['members']:
            node_of_clean[m] = p['id']
clean_shas = sorted(node_of_clean)
by_prefix = {}
for s in clean_shas:
    by_prefix.setdefault(s[:7], []).append(s)

new_sha = {}       # node id -> new commit
src_tree = {}      # node id -> tree before hash rewriting
stats = {'commits': 0, 'blobs_rewritten': 0, 'tokens_mapped': 0, 'tokens_unmapped': 0, 'msg_tokens': 0}
unmapped = {}


def scan(text):
    i, n, out = 0, len(text), []
    while i < n:
        if text[i] in HEX and (i == 0 or text[i - 1] not in ALNUM):
            j = i
            while j < n and text[j] in HEX:
                j += 1
            if 7 <= j - i <= 40 and (j == n or text[j] not in ALNUM):
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def map_clean(clean):
    nid = node_of_clean.get(clean)
    return new_sha.get(nid) if nid is not None else None


def remap_text(text, resolver):
    pieces, last, changed = [], 0, False
    for i, j in scan(text):
        tok = text[i:j]
        target = resolver(tok)
        if target:
            pieces.append(text[last:i])
            pieces.append(target[:len(tok)])
            last = j
            changed = True
    pieces.append(text[last:])
    return ''.join(pieces), changed


def blob_resolver(tok):
    clean = token_to_clean.get(tok)
    if not clean:
        return None
    new = map_clean(clean)
    if new:
        stats['tokens_mapped'] += 1
    else:
        stats['tokens_unmapped'] += 1
        unmapped[tok] = clean
    return new


def msg_resolver(tok):
    cands = [s for s in by_prefix.get(tok[:7], []) if s.startswith(tok)]
    if len(cands) != 1 or not any(c.isalpha() for c in tok) or not any(c.isdigit() for c in tok):
        return None
    new = map_clean(cands[0])
    if new:
        stats['msg_tokens'] += 1
    return new


blob_cache = {}


def rewrite_tree(tree):
    entries = git('ls-tree', '-r', '-z', tree).decode('utf-8', 'surrogateescape').split('\0')
    updates = []
    for e in entries:
        if not e:
            continue
        meta, path = e.split('\t', 1)
        mode, kind, blob = meta.split()
        if kind != 'blob' or blob not in blob_tokens:
            continue
        if blob in blob_cache:
            nb = blob_cache[blob]
        else:
            text = git('cat-file', 'blob', blob).decode('utf-8', 'surrogateescape')
            new, changed = remap_text(text, blob_resolver)
            nb = git('hash-object', '-w', '--stdin', inp=new.encode('utf-8', 'surrogateescape')).decode().strip() \
                if changed else blob
            if all(map_clean(token_to_clean[t]) for t in blob_tokens[blob] if token_to_clean.get(t)):
                blob_cache[blob] = nb
        if nb != blob:
            updates.append(f'{mode} {nb}\t{path}')
    if not updates:
        return tree
    env = {'GIT_INDEX_FILE': idx_file}
    git('read-tree', tree, env=env)
    git('update-index', '--index-info', inp=('\n'.join(updates) + '\n').encode('utf-8', 'surrogateescape'), env=env)
    stats['blobs_rewritten'] += len(updates)
    return git('write-tree', env=env).decode().strip()


def part_tree(base_tree, original, files):
    env = {'GIT_INDEX_FILE': idx_file}
    git('read-tree', base_tree, env=env)
    lines = []
    present = {}
    out = git('ls-tree', '-z', original, '--', *files).decode('utf-8', 'surrogateescape').split('\0') if files else []
    for e in out:
        if e:
            meta, path = e.split('\t', 1)
            mode, kind, blob = meta.split()
            present[path] = (mode, blob)
    for f in files:
        if f in present:
            lines.append(f'{present[f][0]} {present[f][1]}\t{f}')
        else:
            lines.append(f'0 {"0" * 40}\t{f}')   # deleted in the original commit
    git('update-index', '--index-info', inp=('\n'.join(lines) + '\n').encode('utf-8', 'surrogateescape'), env=env)
    return git('write-tree', env=env).decode().strip()


for p in plan:
    nid = p['id']
    for par in p['parents']:
        if par not in new_sha:
            sys.exit(f'node {nid} built before its parent {par}')
    if p['kind'] == 'part':
        base = src_tree[p['parents'][0]]
        src_tree[nid] = part_tree(base, p['members'][0], p['files'])
    else:
        src_tree[nid] = git('rev-parse', p['members'][-1] + '^{tree}').decode().strip()
    tree = rewrite_tree(src_tree[nid])
    message, _ = remap_text(msgs[nid].strip() + '\n', msg_resolver)
    name, email = p['author'], EMAIL[p['author']]
    when = f"{p['epoch']} {p['tz']}"
    env = {'GIT_AUTHOR_NAME': name, 'GIT_AUTHOR_EMAIL': email, 'GIT_AUTHOR_DATE': when,
           'GIT_COMMITTER_NAME': name, 'GIT_COMMITTER_EMAIL': email, 'GIT_COMMITTER_DATE': when}
    args = ['commit-tree', tree]
    for par in p['parents']:
        args += ['-p', new_sha[par]]
    new_sha[nid] = git(*args, inp=message.encode('utf-8'), env=env).decode().strip()
    stats['commits'] += 1

# move the refs
for t in git('tag').decode().split():
    git('tag', '-d', t)
for p in plan:
    for t in p['tags']:
        git('tag', t, new_sha[p['id']])
    for h in p['heads']:
        git('update-ref', f'refs/heads/{h}', new_sha[p['id']])
for r in git('for-each-ref', '--format=%(refname)').decode().split():
    if not (r in ('refs/heads/develop', 'refs/heads/master') or r.startswith('refs/tags/')):
        git('update-ref', '-d', r)
os.path.exists(idx_file) and os.remove(idx_file)
json.dump({'stats': stats, 'unmapped': unmapped, 'new_sha': new_sha}, open(report_file, 'w'))
print(json.dumps(stats))
