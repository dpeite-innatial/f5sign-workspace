#!/usr/bin/env python3
"""Phase 2, step 3: the input for writing each new commit's message.

Usage: python3 -I msg_inputs.py <plan.json> <commits.json> <out-dir> <batch-size> [sample-size]
Writes <out-dir>/batch_NN.jsonl. With a sample size, writes only <out-dir>/sample.jsonl with a varied pick.
"""
import collections
import datetime as dt
import json
import random
import sys
from zoneinfo import ZoneInfo

plan_file, commits_file, out_dir, batch = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sample = int(sys.argv[5]) if len(sys.argv) > 5 else 0
MAD = ZoneInfo('Europe/Madrid')
P = json.load(open(plan_file))
C = {c['sha']: c for c in json.load(open(commits_file))}
by_id = {p['id']: p for p in P}


def msg(sha):
    c = C[sha]
    body = c['body']
    lines = [ln for ln in body.split('\n')]
    return {'subject': c['subject'], 'body': '\n'.join(lines[:60]) + ('\n[…]' if len(lines) > 60 else '')}


def dirs(files):
    cnt = collections.Counter('/'.join(f.split('/')[:3]) for f in files)
    return [f'{d} ({n})' for d, n in cnt.most_common(8)]


rows = []
for p in P:
    r = {'id': p['id'], 'kind': p['kind'], 'author': p['author'],
         'date': dt.datetime.fromtimestamp(p['epoch'], MAD).strftime('%Y-%m-%d'), 'lines': p['lines']}
    if p['kind'] in ('normal',) and not p['merge']:
        r['sources'] = [msg(s) for s in p['members']]
    elif p['kind'] in ('part', 'split-final'):
        r['sources'] = [msg(p['members'][0])]
        r['part'] = f"{p['part'] + 1} of {p['parts']}"
        r['layer'] = p['layer']
        r['files_in_this_part'] = dirs(p['files']) if p.get('files') else 'the remaining files of the commit'
    elif p['kind'] == 'fakemerge':
        r['branch_commits'] = [C[by_id[n]['members'][-1]]['subject'] for n in p['run']]
        r['suggested_branch'] = p['merged_branch']
    else:  # a real merge
        r['sources'] = [msg(p['members'][-1])]
        r['merged_branch'] = p.get('merged_branch')
    rows.append(r)

if sample:
    rnd = random.Random(7)
    kinds = collections.defaultdict(list)
    for r in rows:
        k = r['kind'] + ('-squash' if len(r.get('sources', [])) > 1 else '')
        kinds[k].append(r)
    pick = []
    quota = {'normal': sample // 2, 'normal-squash': sample // 5, 'part': 3, 'split-final': 2, 'fakemerge': 2}
    for k, rs in kinds.items():
        pick += rnd.sample(rs, min(len(rs), quota.get(k, 3)))
    with open(f'{out_dir}/sample.jsonl', 'w') as f:
        for r in sorted(pick, key=lambda r: r['id']):
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('sample rows', len(pick), collections.Counter(r['kind'] for r in pick))
else:
    for i in range(0, len(rows), batch):
        with open(f'{out_dir}/batch_{i // batch:02d}.jsonl', 'w') as f:
            for r in rows[i:i + batch]:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('rows', len(rows), 'batches', (len(rows) + batch - 1) // batch)
