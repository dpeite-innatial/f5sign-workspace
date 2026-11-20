#!/usr/bin/env python3
"""Phase 2, step 2: plan the restructured graph. Reads plan/commits.json, touches no repository.

Usage: python3 -I plan_graph.py <commits.json> <refs.tsv> <out-dir> [knob=value ...]
refs.tsv: '<ref>\t<commit sha>' for refs/heads/develop, refs/heads/master and every refs/tags/*.

Each node of the new graph is one of:
  normal       one or more consecutive original commits squashed into one (tree = the last one's);
  part         a slice of an oversized original commit, split by layer (tree built from a file subset);
  split-final  the last slice of such a commit (tree = the original commit's);
  fakemerge    a --no-ff merge closing a run of direct commits that now sit on a feature branch.
Writes <out-dir>/plan.json and <out-dir>/report.txt.
"""
import collections
import datetime as dt
import json
import random
import sys
from zoneinfo import ZoneInfo

commits_file, refs_file, out_dir = sys.argv[1:4]
K = {
    'LCAP': 1500, 'KMAX': 4, 'GAP_H': 4,
    'SPLIT': 5000, 'SPLIT_MAX': 14,
    'WEEK_LINES': 30000, 'WEEK_COMMITS': 55, 'DAY_COMMITS': 16, 'DAY_LINES': 8000,
    'BACK_DAYS': 14, 'FWD_DAYS': 3, 'MOVE_FACTOR': 130, 'SEED': 20261120,
}
for kv in sys.argv[4:]:
    k, v = kv.split('=')
    K[k] = int(v)
rnd = random.Random(K['SEED'])
MAD = ZoneInfo('Europe/Madrid')
HOLIDAYS = {dt.date(2026, 10, 12), dt.date(2026, 8, 15), dt.date(2026, 11, 2), dt.date(2026, 5, 1)}
DANIEL, MIGUEL = 'Daniel Vilar', 'Miguel Melon'

C = json.load(open(commits_file))
by = {c['sha']: c for c in C}
order = [c['sha'] for c in C]
idx = {s: i for i, s in enumerate(order)}
children = collections.defaultdict(list)
for c in C:
    for p in c['parents']:
        children[p].append(c['sha'])
refs = {}
for ln in open(refs_file):
    r, s = ln.split()
    refs[r] = s
ref_targets = set(refs.values())

nodes = {}
bucket_of = {}


def new_node(**kw):
    kw['id'] = len(nodes)
    nodes[kw['id']] = kw
    return kw


# ------------------------------------------------------------------ 1. squash linear runs
for s in order:
    c = by[s]
    if len(c['parents']) == 1:
        p = c['parents'][0]
        pc = by[p]
        n = nodes.get(bucket_of.get(p))
        if (n and n['kind'] == 'normal' and n['members'][-1] == p and len(pc['parents']) == 1
                and children[p] == [s] and p not in ref_targets and pc['author'] == c['author']
                and n['lines'] + c['lines'] <= K['LCAP'] and len(n['members']) < K['KMAX']
                and 0 <= c['at'] - pc['at'] <= K['GAP_H'] * 3600):
            n['members'].append(s)
            n['lines'] += c['lines']
            bucket_of[s] = n['id']
            continue
    n = new_node(kind='normal', members=[s], lines=c['lines'], author=c['author'], key=c['ct'],
                 branch=c.get('branch'), merge=len(c['parents']) > 1, merged_branch=c.get('merged_branch'))
    bucket_of[s] = n['id']
for n in list(nodes.values()):
    n['parents'] = [bucket_of[p] for p in by[n['members'][0]]['parents']]


def week_of(epoch):
    d = dt.datetime.fromtimestamp(epoch, MAD).isocalendar()
    return f'{d[0]}-W{d[1]:02d}'


# ------------------------------------------------------------------ 2. move whole branches to Miguel
branch_nodes = collections.defaultdict(list)
for n in nodes.values():
    br = n['branch']
    if br and br != 'develop' and not br.startswith('origin') and not n['merge']:
        branch_nodes[br].append(n['id'])
merge_node_of = {n['merged_branch']: n['id'] for n in nodes.values() if n['merge'] and n.get('merged_branch')}


def load(author):
    w = collections.Counter()
    for n in nodes.values():
        if n['author'] == author and not n['merge']:
            w[week_of(n['key'])] += n['lines']
    return w


moved = []
dan, mig = load(DANIEL), load(MIGUEL)
cap = K['WEEK_LINES'] * K['MOVE_FACTOR'] / 100
for week, lines in dan.most_common():
    if lines <= cap:
        break
    cands = []
    for br, ids in branch_nodes.items():
        if all(nodes[i]['author'] == DANIEL for i in ids) and week_of(nodes[ids[-1]]['key']) == week:
            cands.append((sum(nodes[i]['lines'] for i in ids), br))
    for size, br in sorted(cands, reverse=True):
        if dan[week] <= cap:
            break
        if mig[week] + size > cap or sum(mig.values()) + size > sum(dan.values()) - size:
            continue
        for i in branch_nodes[br]:
            nodes[i]['author'] = MIGUEL
        if br in merge_node_of:
            nodes[merge_node_of[br]]['author'] = MIGUEL
        dan[week] -= size
        mig[week] += size
        moved.append((week, br, size))

# ------------------------------------------------------------------ 3. split oversized commits by layer
LAYERS = [
    ('docs', lambda f: f.startswith('docs/') or f.endswith('.md')),
    ('schema and config', lambda f: f.startswith(('migrations/', 'config/', 'deptrac', 'phpstan', '.env',
                                                  'composer.', 'Dockerfile', 'docker/', 'bin/', '.github/'))),
    ('domain', lambda f: f.startswith('src/') and ('/Domain/' in f or '/Contract/' in f or '/Kernel/' in f)),
    ('application', lambda f: f.startswith('src/') and '/Application/' in f),
    ('adapters', lambda f: f.startswith(('src/', 'templates/', 'assets/'))),
    ('tests', lambda f: f.startswith('tests/')),
    ('rest', lambda f: True),
]
splits = []
for n in list(nodes.values()):
    if n['kind'] != 'normal' or n['merge'] or len(n['members']) != 1 or n['lines'] <= K['SPLIT']:
        continue
    c = by[n['members'][0]]
    groups = collections.OrderedDict((name, []) for name, _ in LAYERS)
    for f in c['files']:
        for name, test in LAYERS:
            if test(f):
                groups[name].append(f)
                break
    parts = []
    for name, fs in groups.items():
        if not fs:
            continue
        ln = sum(c['file_lines'].get(f, 0) for f in fs)
        if ln <= K['SPLIT'] * 0.8:
            parts.append((name, fs, ln))
            continue
        # one layer is itself too big: cut it by bounded context (the third path segment), in order
        by_ctx = collections.OrderedDict()
        for f in sorted(fs):
            seg = f.split('/')
            by_ctx.setdefault('/'.join(seg[:4]) if len(seg) > 4 else '/'.join(seg[:3]) if len(seg) > 3 else seg[0],
                              []).append(f)
        chunk, chunk_l, label = [], 0, []
        for ctx, cf in by_ctx.items():
            cl = sum(c['file_lines'].get(f, 0) for f in cf)
            if chunk and chunk_l + cl > K['SPLIT'] * 0.6:
                parts.append((name + ' (' + ', '.join(label) + ')', chunk, chunk_l))
                chunk, chunk_l, label = [], 0, []
            chunk += cf
            chunk_l += cl
            label.append('/'.join(ctx.split('/')[2:]) or ctx)
        if chunk:
            parts.append((name + ' (' + ', '.join(label) + ')', chunk, chunk_l))
    merged = []
    for name, fs, ln in parts:
        if merged and ((merged[-1][2] + ln <= K['SPLIT'] * 0.6 and ln < 0.12 * n['lines'])
                       or len(merged) >= K['SPLIT_MAX']):
            pn, pf, pl = merged[-1]
            merged[-1] = (pn + ' + ' + name, pf + fs, pl + ln)
        else:
            merged.append((name, fs, ln))
    if len(merged) > 1 and merged[0][2] < 0.12 * n['lines'] and merged[0][2] + merged[1][2] <= K['SPLIT'] * 0.6:
        a, b = merged[0], merged[1]
        merged[0:2] = [(a[0] + ' + ' + b[0], a[1] + b[1], a[2] + b[2])]
    if len(merged) < 2:
        continue
    prev = n['parents']
    made = []
    for i, (name, fs, ln) in enumerate(merged[:-1]):
        p = new_node(kind='part', members=[n['members'][0]], files=fs, layer=name, part=i, parts=len(merged),
                     lines=ln, author=n['author'], key=n['key'] - (len(merged) - 1 - i) * 5400,
                     branch=n['branch'], merge=False, parents=list(prev))
        prev = [p['id']]
        made.append(p['id'])
    n['parents'] = prev
    n['layer'], n['part'], n['parts'], n['lines'] = merged[-1][0], len(merged) - 1, len(merged), merged[-1][2]
    n['kind'] = 'split-final'
    splits.append((n['id'], made))

# ------------------------------------------------------------------ 4. fake feature branches
def scope(subject):
    i, j = subject.find('('), subject.find(')')
    return subject[i + 1:j] if 0 < i < j < 40 else subject.split(':')[0][:20]


first_parent_line = set()
for ref in ('refs/heads/develop', 'refs/heads/master'):
    s = refs[ref]
    while s:
        first_parent_line.add(s)
        ps = by[s]['parents']
        s = ps[0] if ps else None
child_nodes = collections.defaultdict(list)
for n in nodes.values():
    for p in n['parents']:
        child_nodes[p].append(n['id'])


def direct(nid):
    n = nodes[nid]
    return not n['merge'] and not n.get('branch') and n['members'][-1] in first_parent_line


def tag_of(n):
    c = by[n['members'][-1]]
    return c['task'] or scope(c['subject'])


runs, seen = [], set()
for n in sorted(nodes.values(), key=lambda n: (idx[n['members'][-1]], n.get('part', 0))):
    if n['id'] in seen or n['kind'] == 'part' or not direct(n['id']):
        continue
    head_parts = []
    cur = n
    while cur['parents'] and nodes[cur['parents'][0]]['kind'] == 'part':
        head_parts.insert(0, cur['parents'][0])
        cur = nodes[cur['parents'][0]]
    run = head_parts + [n['id']]
    seen.add(n['id'])
    nxt = n
    while n['kind'] != 'split-final':
        kids = [k for k in child_nodes[nxt['id']] if nodes[k]['parents'][0] == nxt['id'] and direct(k)
                and nodes[k]['kind'] == 'normal' and k not in seen]
        if len(kids) != 1:
            break
        k = nodes[kids[0]]
        if k['author'] != n['author'] or tag_of(k) != tag_of(n) or k['members'][-1] in ref_targets:
            break
        run.append(k['id'])
        seen.add(k['id'])
        nxt = k
    if len(run) >= 2:
        runs.append((run, tag_of(n)))

fake_merges = []
kept_runs = []
for run, tag in runs:
    while run and not nodes[run[0]]['parents']:
        run = run[1:]          # the root commit has no base to branch from
    if len(run) < 2:
        continue
    kept_runs.append((run, tag))
    first, last = nodes[run[0]], nodes[run[-1]]
    kind = 'fix' if by[last['members'][-1]]['subject'].startswith('fix') else 'feat'
    slug = (tag or 'work').lower().replace(' ', '-').replace(',', '-').replace('/', '-')[:40]
    m = new_node(kind='fakemerge', members=[last['members'][-1]], lines=0, author=last['author'],
                 key=last['key'] + 300, branch=None, merge=True, parents=[first['parents'][0], last['id']],
                 merged_branch=f'{kind}/{slug}', run=run)
    for k in list(child_nodes[last['id']]):
        if k != m['id'] and nodes[k]['parents'] and nodes[k]['parents'][0] == last['id']:
            nodes[k]['parents'][0] = m['id']
    fake_merges.append(m['id'])

ref_node = {}
closing = {nodes[m]['parents'][1]: m for m in fake_merges}
for r, s in refs.items():
    nid = bucket_of[s]
    ref_node[r] = closing.get(nid, nid)

# ------------------------------------------------------------------ 5. dates
def workday(d):
    return d.weekday() < 5 and d not in HOLIDAYS


ids = sorted(nodes, key=lambda i: (nodes[i]['key'], i))
t0 = dt.datetime.fromtimestamp(nodes[ids[0]]['key'], MAD).date()
t1 = dt.datetime.fromtimestamp(max(n['key'] for n in nodes.values()), MAD).date()
wdays = [d for d in (t0 + dt.timedelta(k) for k in range((t1 - t0).days + 1)) if workday(d)]
weight = {i: (0.2 if nodes[i]['merge'] else 1 + nodes[i]['lines'] / 400) for i in nodes}
total_w = sum(weight.values())
target = {}
acc = 0.0
for i in ids:
    acc += weight[i]
    pos = acc / total_w * len(wdays)
    d = wdays[min(int(pos), len(wdays) - 1)]
    eq = dt.datetime.combine(d, dt.time(9, 0), MAD) + dt.timedelta(hours=9.5 * (pos - int(pos)))
    orig = dt.datetime.fromtimestamp(nodes[i]['key'], MAD)
    target[i] = min(max(eq, orig - dt.timedelta(days=K['BACK_DAYS'])), orig + dt.timedelta(days=K['FWD_DAYS']))

deadline = {}
for r, nid in ref_node.items():
    if not r.startswith('refs/tags/'):
        continue
    limit = dt.datetime.fromtimestamp(nodes[nid]['key'], MAD) + dt.timedelta(days=1)
    stack, seen_d = [nid], set()
    while stack:
        x = stack.pop()
        if x in seen_d:
            continue
        seen_d.add(x)
        if x not in deadline or limit < deadline[x]:
            deadline[x] = limit
        stack.extend(nodes[x]['parents'])
for i, lim in deadline.items():
    target[i] = min(target[i], lim - dt.timedelta(days=1))

WINDOWS = [(dt.time(9, 0), dt.time(14, 15)), (dt.time(15, 15), dt.time(18, 45))]


def next_slot(t):
    while True:
        d = t.date()
        if workday(d):
            for a, z in WINDOWS:
                start, end = dt.datetime.combine(d, a, MAD), dt.datetime.combine(d, z, MAD)
                if t < start:
                    return start + dt.timedelta(minutes=rnd.randint(0, 25))
                if t < end:
                    return t
        t = dt.datetime.combine(d + dt.timedelta(1), dt.time(9, 0), MAD)


new_time, last = {}, {}
day_c, day_l, week_c, week_l = (collections.Counter() for _ in range(4))
violations = []
queue = sorted(nodes, key=lambda i: (target[i], i))
placed = set()
while queue:
    rest = []
    for i in queue:
        n = nodes[i]
        if not set(n['parents']) <= placed:
            rest.append(i)
            continue
        a = n['author']
        crunch = i in deadline and target[i] >= deadline[i] - dt.timedelta(days=4)
        gap = dt.timedelta(minutes=rnd.randint(2, 15) if n['merge'] else rnd.randint(3, 12) if crunch
                           else max(6, int(rnd.triangular(8, 95, 26))))
        t = max([target[i]] + [new_time[p] + dt.timedelta(minutes=rnd.randint(3, 20)) for p in n['parents']]
                + ([last[a] + gap] if a in last else []))
        for _ in range(400):
            t = next_slot(t)
            if n['merge'] or (i in deadline and t >= deadline[i] - dt.timedelta(days=3)):
                break
            dk, wk = (a, t.date()), (a, week_of(t.timestamp()))
            if day_c[dk] >= K['DAY_COMMITS'] or (day_l[dk] + n['lines'] > K['DAY_LINES'] and day_c[dk] > 0):
                t = dt.datetime.combine(t.date() + dt.timedelta(1), dt.time(9, 0), MAD) + \
                    dt.timedelta(minutes=rnd.randint(0, 90))
                continue
            if week_c[wk] >= K['WEEK_COMMITS'] or (week_l[wk] + n['lines'] > K['WEEK_LINES'] * 1.15
                                                    and week_c[wk] > 0):
                monday = t.date() + dt.timedelta(7 - t.weekday())
                t = dt.datetime.combine(monday, dt.time(9, 0), MAD) + dt.timedelta(minutes=rnd.randint(0, 90))
                continue
            break
        t = t + dt.timedelta(seconds=rnd.randint(0, 59))
        new_time[i] = t
        last[a] = t
        if not n['merge']:
            day_c[(a, t.date())] += 1
            day_l[(a, t.date())] += n['lines']
            week_c[(a, week_of(t.timestamp()))] += 1
            week_l[(a, week_of(t.timestamp()))] += n['lines']
        placed.add(i)
        if i in deadline and t > deadline[i]:
            violations.append(('deadline', i, t.isoformat(), deadline[i].isoformat()))
    if len(rest) == len(queue):
        violations.append(('cycle', len(rest), rest[:5]))
        break
    queue = rest

# ------------------------------------------------------------------ outputs
plan = []
for i in sorted(nodes, key=lambda i: (new_time.get(i, dt.datetime.max.replace(tzinfo=MAD)), i)):
    n = dict(nodes[i])
    n['epoch'] = int(new_time[i].timestamp()) if i in new_time else None
    n['tz'] = new_time[i].strftime('%z') if i in new_time else None
    n['tags'] = [r[10:] for r, nid in ref_node.items() if nid == i and r.startswith('refs/tags/')]
    n['heads'] = [r[11:] for r, nid in ref_node.items() if nid == i and r.startswith('refs/heads/')]
    plan.append(n)
json.dump(plan, open(f'{out_dir}/plan.json', 'w'))

with open(f'{out_dir}/report.txt', 'w') as r:
    nm = [p for p in plan if not p['merge']]
    r.write(f'knobs {K}\n')
    r.write(f"new commits: {len(plan)} ({len(nm)} non-merge, {len(plan) - len(nm)} merges) from {len(C)}\n")
    for a in (DANIEL, MIGUEL):
        r.write(f"{a}: {sum(1 for p in nm if p['author'] == a)} non-merge, "
                f"{sum(p['lines'] for p in nm if p['author'] == a)} lines\n")
    r.write(f'branches moved to Miguel: {len(moved)}, {sum(m[2] for m in moved)} lines\n')
    r.write(f'giant commits split: {len(splits)} into {sum(len(m) + 1 for _, m in splits)} commits\n')
    r.write(f'fake feature branches: {len(fake_merges)} covering {sum(len(r_) for r_, _ in kept_runs)} commits\n')
    for (run, tag), m in zip(kept_runs, fake_merges):
        r.write(f"   {nodes[m]['merged_branch']}: {len(run)} commits\n")
    big = sorted((p['lines'] for p in nm), reverse=True)
    r.write(f'largest commits now: {big[:8]}\n')
    hours = collections.Counter(dt.datetime.fromtimestamp(p['epoch'], MAD).hour for p in plan if p['epoch'])
    r.write('hours: ' + ' '.join(f'{h}:{hours[h]}' for h in sorted(hours)) + '\n')
    shift = sorted((p['epoch'] - p['key']) / 86400 for p in plan if p['epoch'])
    r.write(f'shift days: min {shift[0]:.1f} median {shift[len(shift) // 2]:.1f} max {shift[-1]:.1f}\n')
    r.write(f'refs: {ref_node}\n')
    r.write(f'violations: {len(violations)}\n')
    for v in violations[:30]:
        r.write(f'   {v}\n')
print(open(f'{out_dir}/report.txt').read())
