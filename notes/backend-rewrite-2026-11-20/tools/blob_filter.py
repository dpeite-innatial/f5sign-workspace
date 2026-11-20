#!/usr/bin/env python3
"""Phase 1a: rewrite the CONTENT of every kept blob in history, with literal replacements only.

Run with the python of git-filter-repo's pipx venv (where the module lives), from a throwaway clone:
    ~/.local/share/pipx/venvs/git-filter-repo/bin/python blob_filter.py <repo-dir> <units.rewritten.jsonl> <report-dir>

What it does, in order, to each text blob of a kept path:
  1. the sentence units rewritten by hand/model (old -> new, longest first);
  2. markdown links whose target resolves into a removed doc path become their plain link text;
  3. the glyphs ⚑ ⛔ ⚠ ⛑ (and the emoji variation selector after them) are removed with one following space;
  4. Innasign -> F5Sign (three casings) and the old image namespace -> factorcinco.
Paths: removes .claude/, CLAUDE.md and the process docs; renames src/Innasign and tests/Innasign.
No regular expressions anywhere: every search is str.find / str.replace.
"""
import json
import os
import posixpath
import sys

import git_filter_repo as fr

repo, report_dir = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[3])
units_file = ','.join(os.path.abspath(u) for u in sys.argv[2].split(','))
os.makedirs(report_dir, exist_ok=True)

REMOVED = ('docs/tasks/', 'docs/frontend-handoff/', 'docs/infra-handoff/', 'docs/tooling-handoff/',
           'docs/BACKLOG.md', 'CLAUDE.md', '.claude/')
RENAMES = (('src/Innasign/', 'src/F5Sign/'), ('tests/Innasign/', 'tests/F5Sign/'))
BINARY_SUFFIX = ('.lock', '.ttf', '.otf', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.zip', '.p12', '.der',
                 '.ico', '.woff', '.woff2')

UNITS = []
DROP_LINES = {'CLAUDE.md', '.claude', '.claude/', '/CLAUDE.md', '/.claude/'}
for line in (ln for uf in units_file.split(',') for ln in open(uf, encoding='utf-8')):
    row = json.loads(line)
    if row['action'] == 'rewrite' and row['new'] != row['unit']:
        UNITS.append((row['unit'], row['new']))
    elif row['action'] == 'drop_line':
        DROP_LINES.add(row['unit'])
UNITS.sort(key=lambda p: -len(p[0]))

GLYPHS = ['⚑', '⛔', '⚠', '⛑']
# a glyph used as a noun ("see the ⛔ below") becomes the word it stood for
GLYPH_REFS = [('the ⛔', 'the warning'), ('The ⛔', 'The warning'), ('the ⚑', 'the note'), ('The ⚑', 'The note'),
              ('the ⚠', 'the caveat'), ('The ⚠', 'The caveat'), ('the ⛑', 'the correction'), ('a ⛔', 'a warning')]
SIMPLE = [
    ('ghcr.io/dpeite-innatial/', 'ghcr.io/factorcinco/'),
    ('InnaSign', 'F5Sign'), ('Innasign', 'F5Sign'), ('innasign', 'f5sign'), ('INNASIGN', 'F5SIGN'),
    # "agent" as in an AI agent, in phrasings the sentence units did not catch
    (' (human or agent)', ''), (' (or agent)', ''), ('devs/agents', 'developers'),
    # two passages where a claude unit and a workspace unit overlapped, so neither matched whole
    ('workspace scratchpads `EA-EVIDENCE-CUSTODY-SEAM.md` / `EA-KMS-RESEARCH.md` / '
     '`EA-INCUMBENT-COMPLIANCE-REFERENCE.md` (not available from this repo)',
     'internal design notes (not available from this repo)'),
    ('The design trail lives in the workspace scratchpads `EA-PII-KERNEL-TYPES.md` (the Q1–Q4 modeling pass + '
     'the Carrier-B persistence caveats + the drift-elimination follow-up) and `EA-EVIDENCE-CUSTODY-SEAM.md` (the '
     'two-carrier, one-classification framing) — neither available from a backend-only checkout; this ADR is the '
     'self-contained in-repo home.',
     'This ADR is the self-contained home of its design.'),
    # the OFFREPO notes are gone, so the sentences pointing at them go too
    ('In-repo homes are authoritative — see the `OFFREPO:` note at the end of this file for why the design-repo '
     'ones are not followable.',
     'In-repo homes are authoritative; the design-repo sections are not reachable from this repository.'),
    ('In-repo homes are authoritative — see the `OFFREPO:` note after the [Pointers](#pointers) section for why '
     'the design-repo ones are not followable.',
     'In-repo homes are authoritative; the design-repo sections are not reachable from this repository.'),
]
MOVED_MARKERS = ('docs/tasks/', 'tasks/TASK-', 'BACKLOG.md', 'frontend-handoff/', 'infra-handoff/',
                 'tooling-handoff/')

stats = {'blobs': 0, 'changed': 0, 'units': 0, 'links': 0, 'glyphs': 0, 'simple': 0, 'offrepo': 0}
unresolved_links = {}


def is_removed(path):
    return path.startswith(REMOVED)


def strip_removed_links(text, path):
    """[label](target) -> label, when target resolves into a removed path. Scans with str.find only."""
    out = []
    i = 0
    base = posixpath.dirname(path)
    while True:
        k = text.find('](', i)
        if k == -1:
            out.append(text[i:])
            break
        close = text.find(')', k + 2)
        open_ = text.rfind('[', i, k)
        nl = text.find('\n', k + 2)
        if close == -1 or open_ == -1 or (nl != -1 and nl < close) or '\n' in text[open_:k]:
            out.append(text[i:k + 2])
            i = k + 2
            continue
        target = text[k + 2:close].strip()
        bare = target.split('#', 1)[0].split(' ', 1)[0]
        removed = False
        if bare and '://' not in bare:
            resolved = posixpath.normpath(posixpath.join(base, bare)) if not bare.startswith('/') else bare.lstrip('/')
            removed = is_removed(resolved) or is_removed(resolved + '/')
            # A link with the wrong ../ depth resolves nowhere, yet still names a doc that is leaving:
            # judge it by the name it carries, and keep a record of each such case.
            if not removed and any(m in bare for m in MOVED_MARKERS):
                unresolved_links[f'{path} -> {bare}'] = resolved
                removed = True
        if removed:
            out.append(text[i:open_])
            out.append(text[open_ + 1:k])
            stats['links'] += 1
        else:
            out.append(text[i:close + 1])
        i = close + 1
    return ''.join(out)


def strip_offrepo(text):
    """Remove the OFFREPO markers: an HTML comment `<!-- OFFREPO ... -->` goes whole (and its line, when
    nothing else is left on it); a bare `OFFREPO: ` tag inside a code comment loses only the tag."""
    out = []
    i = 0
    while True:
        k = text.find('<!-- OFFREPO', i)
        if k == -1:
            out.append(text[i:])
            break
        end = text.find('-->', k)
        if end == -1:
            out.append(text[i:])
            break
        end += 3
        line_start = text.rfind('\n', 0, k) + 1
        line_end = text.find('\n', end)
        line_end = len(text) if line_end == -1 else line_end
        before = text[line_start:k]
        after = text[end:line_end]
        stats['offrepo'] += 1
        if before.strip(' *#/') == '' and after.strip() == '':
            out.append(text[i:line_start])
            i = line_end + 1 if line_end < len(text) else line_end
        else:
            out.append(text[i:k].rstrip(' ') if after.strip() == '' else text[i:k])
            i = end
    text = ''.join(out)
    if 'OFFREPO: ' in text:
        stats['offrepo'] += text.count('OFFREPO: ')
        text = text.replace('OFFREPO: ', '')
    return text


def transform(text, path):
    if DROP_LINES and path in ('.dockerignore', '.gitignore'):
        kept = [ln for ln in text.split('\n') if ln.strip() not in DROP_LINES]
        text = '\n'.join(kept)
    if path == '.cspell.json':
        text = '\n'.join(ln for ln in text.split('\n') if ln.strip() not in ('"Inna",', '"Innatial",', '"OFFREPO",'))
    if path == 'README.md':
        for section in ('\n## Licencia\n\nPropietario — Innatial / F5Sign.\n', '\n## License\n\nProprietary — Innatial.\n',
                        '\nProprietary — Innatial.\n', '\nPropietario — Innatial / F5Sign.\n'):
            text = text.replace(section, '\n')
    if 'OFFREPO' in text:
        text = strip_offrepo(text)
    for old, new in UNITS:
        if old in text:
            stats['units'] += text.count(old)
            text = text.replace(old, new)
    if '](' in text:
        text = strip_removed_links(text, path)
    for old, new in GLYPH_REFS:
        if old in text:
            text = text.replace(old, new)
    for g in GLYPHS:
        if g in text:
            text = text.replace(' ' + g + '\ufe0f\n', '\n').replace(' ' + g + '\n', '\n')
            stats['glyphs'] += text.count(g)
            for variant in (g + '️ ', g + ' ', g + '️', g):
                text = text.replace(variant, '')
    for old, new in SIMPLE:
        if old in text:
            stats['simple'] += text.count(old)
            text = text.replace(old, new)
    return text


def file_info_callback(filename, mode, blob_id, value):
    p = filename.decode('utf-8', 'replace')
    if is_removed(p):
        return (None, mode, blob_id)
    for a, b in RENAMES:
        if p.startswith(a):
            p = b + p[len(a):]
    if mode in (b'120000', b'160000') or p.endswith(BINARY_SUFFIX):
        return (p.encode(), mode, blob_id)
    # The callback runs once per file of every commit; a blob is transformed once per path.
    key = (blob_id, p)
    if key in seen:
        return (p.encode(), mode, seen[key])
    seen[key] = blob_id
    data = value.get_contents_by_identifier(blob_id)
    stats['blobs'] += 1
    if b'\x00' in data[:8000]:
        return (p.encode(), mode, blob_id)
    text = data.decode('utf-8', 'surrogateescape')
    new = transform(text, p)
    if new != text:
        # a removed glyph or link must not leave trailing whitespace on a line it changed
        old_lines = set(text.split('\n'))
        new = '\n'.join(ln if ln in old_lines else ln.rstrip(' \t') for ln in new.split('\n'))
    if new == text:
        return (p.encode(), mode, blob_id)
    stats['changed'] += 1
    seen[key] = value.insert_file_with_contents(new.encode('utf-8', 'surrogateescape'))
    return (p.encode(), mode, seen[key])


seen = {}


os.chdir(repo)
# Path removal and renames go through filter-repo's own options: they apply to every kind of change,
# deletions included, which file_info_callback never sees (a file created under src/Innasign and
# deleted later survived as a ghost under src/F5Sign when the rename lived only in the callback).
path_args = ['--invert-paths']
for r in REMOVED:
    path_args += ['--path', r]
for a, b in RENAMES:
    path_args += ['--path-rename', f'{a}:{b}']
args = fr.FilteringOptions.parse_args(['--force', '--quiet'] + path_args)
fr.RepoFilter(args, file_info_callback=file_info_callback).run()

with open(os.path.join(report_dir, 'stats.json'), 'w') as f:
    json.dump(stats, f, indent=1)
with open(os.path.join(report_dir, 'unresolved-links.txt'), 'w') as f:
    for k, v in sorted(unresolved_links.items()):
        f.write(f'{k}\t{v}\n')
print(json.dumps(stats))
