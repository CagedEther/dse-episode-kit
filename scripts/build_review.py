import json, re, sys, html
from pathlib import Path
ep = Path(sys.argv[1])
md = (ep/'episode.md').read_text()
title = re.search(r'^# Episode (\d+)\s*[—-]\s*(.+)$', md, re.M)
number, name = (title.group(1), title.group(2).strip()) if title else ('', ep.name)
prompts = {s['id'].upper(): s for s in json.load(open(ep/'shot-prompts.json'))}
motion = {s['id']: s for s in json.load(open(ep/'motion-prompts.json'))['shots']}

def secs(t): m, s = t.split(':'); return int(m)*60+int(s)
vo = [(secs(m.group(1)), m.group(2).strip()) for m in re.finditer(r'^\[(\d\d:\d\d)\]\s*(.+)$', md, re.M)]
end = sum(int(d) for d in re.findall(r'^- \*\*E\d\d-SC\d\d-SH\d\d\*\* · (\d+)s', md, re.M)) or 110
vo_spans = []
for i, (a, text) in enumerate(vo):
    b = vo[i+1][0] if i+1 < len(vo) else end
    sents = re.findall(r'[^.!?]+[.!?]+', text) or [text]
    words = [len(x.split()) for x in sents]; total = sum(words); t0 = a
    for x, w in zip(sents, words):
        t1 = t0 + (b - a) * w / total
        vo_spans.append((t0, t1, x.strip(), a)); t0 = t1

scenes, shots, scene = {}, [], None
for line in md.split('\n'):
    m = re.match(r'^### (SC\d\d) · (.+)$', line)
    if m: scene = m.group(1); scenes[scene] = m.group(2); continue
    m = re.match(r'^- \*\*(E\d\d-SC\d\d-SH\d\d)\*\* · (\d+)s · ([^·]+) · ([^·]+) · (.+)$', line)
    if m:
        shots.append(dict(id=m.group(1), scene=scene, dur=int(m.group(2)), framing=m.group(3).strip(), level=m.group(4).strip(), guide=m.group(5).strip()))
t = 0
for s in shots:
    s['start'], s['end'] = t, t+s['dur']; t += s['dur']
    hits = [(a, b, x, para) for a, b, x, para in vo_spans if min(b, s['end']) - max(a, s['start']) >= 0.75]
    s['vo'] = [dict(start=round(a), para=para, text=x, cont=a < s['start'] - 0.5) for a, b, x, para in hits]
    s['prompt'] = prompts[s['id']]['prompt']
    s['motion'] = motion.get(s['id'], {}).get('motion', '')
    s['img'] = f"frames/{s['id']}.png"
data = dict(scenes=scenes, shots=shots, total=t)
tpl = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).with_name('review-template.html')).read_text()
tpl = (tpl.replace('__NUMBER__', number).replace('__NAME__', html.escape(name))
          .replace('__KEY__', f'dse-e{number}-stills-review-v2'))
(ep/'stills-review.html').write_text(tpl.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False)))
print(len(shots), 'shots,', t, 's')
