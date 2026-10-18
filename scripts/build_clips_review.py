"""Build clips-review.html for an episode: each clip beside the motion prompt that made it.

Usage: python3 scripts/build_clips_review.py story/episode-05

Reads from the episode folder:
  episode.md, shot-prompts.json, motion-prompts.json   shot list, voice-over, original motion lines
  clips/SHOT_ID.mp4                                     the clips
  clips/clips-report.md                                 seeds ("- SHOT_ID seed N: ok")
  clips/motion-used.json (optional)                     the motion lines actually sent, if they differ
  clips/first-pass/SHOT_ID.mp4 (optional)               earlier takes, shown for comparison
  clips/first-pass/motion-used.json (optional)          lines used for those (default: motion-prompts.json)
"""
import json, re, sys
from pathlib import Path

ep = Path(sys.argv[1])
template = Path(__file__).with_name('clips-review-template.html')
md = (ep / 'episode.md').read_text()
clips = ep / 'clips'


def motion_lines(path: Path) -> dict:
    return {s['id']: s for s in json.loads(path.read_text())['shots']} if path.exists() else {}


original = motion_lines(ep / 'motion-prompts.json')
used = {**original, **motion_lines(clips / 'motion-used.json')}
first = clips / 'first-pass'
first_used = {**original, **motion_lines(first / 'motion-used.json')}
seeds = {}
for report in [clips / 'clips-report.md']:
    if report.exists():
        for m in re.finditer(r'^- (E\d\d-SC\d\d-SH\d\d) seed (\d+): ok', report.read_text(), re.M):
            seeds[m.group(1)] = int(m.group(2))

title = re.search(r'^# Episode (\d+)\s*[—-]\s*(.+)$', md, re.M)
number, name = (title.group(1), title.group(2).strip()) if title else ('', ep.name)


def secs(t):
    m, s = t.split(':')
    return int(m) * 60 + int(s)


episode_len = sum(int(x) for x in re.findall(r'^- \*\*E\d\d-SC\d\d-SH\d\d\*\* · (\d+)s', md, re.M))
vo = [(secs(m.group(1)), m.group(2).strip()) for m in re.finditer(r'^\[(\d\d:\d\d)\]\s*(.+)$', md, re.M)]
spans = []
for i, (a, text) in enumerate(vo):
    b = vo[i + 1][0] if i + 1 < len(vo) else episode_len
    sents = re.findall(r'[^.!?]+[.!?]+', text) or [text]
    words = [len(x.split()) for x in sents]
    total, t0 = sum(words), a
    for x, w in zip(sents, words):
        t1 = t0 + (b - a) * w / total
        spans.append((t0, t1, x.strip()))
        t0 = t1

scenes, shots, scene = {}, [], None
for line in md.split('\n'):
    m = re.match(r'^### (SC\d\d) · (.+)$', line)
    if m:
        scene = m.group(1)
        scenes[scene] = m.group(2)
        continue
    m = re.match(r'^- \*\*(E\d\d-SC\d\d-SH\d\d)\*\* · (\d+)s · ([^·]+) · ([^·]+) · (.+)$', line)
    if m:
        shots.append(dict(id=m.group(1), scene=scene, dur=int(m.group(2)), framing=m.group(3).strip(),
                          level=m.group(4).strip(), guide=m.group(5).strip()))

t = 0
for s in shots:
    s['start'], s['end'] = t, t + s['dur']
    t += s['dur']
    s['vo'] = [dict(start=round(a), text=x, cont=a < s['start'] - 0.5)
               for a, b, x in spans if min(b, s['end']) - max(a, s['start']) >= 0.75]
    shot = used.get(s['id'], {})
    s['motion'] = shot.get('motion', '')
    s['original'] = original.get(s['id'], {}).get('motion', '')
    s['gen'] = shot.get('generate_seconds', 5 if s['dur'] <= 5 else 10)
    s['seed'] = seeds.get(s['id'])
    s['img'] = f"frames/{s['id']}.png"
    s['clip'] = f"clips/{s['id']}.mp4" if (clips / f"{s['id']}.mp4").exists() else None
    if (first / f"{s['id']}.mp4").exists():
        s['previous'] = dict(clip=f"clips/first-pass/{s['id']}.mp4", motion=first_used.get(s['id'], {}).get('motion', ''))

data = dict(scenes=scenes, shots=shots, total=t)
html = (template.read_text()
        .replace('/*TITLE*/', f'E{number} Clips Review')
        .replace('/*HEADING*/', f'Episode {number} · {name} · Clips review')
        .replace("/*KEY*/''", json.dumps(f'dse-e{number}-clips-review-v1'))
        .replace('/*DATA*/null', json.dumps(data, ensure_ascii=False)))
(ep / 'clips-review.html').write_text(html)
print(sum(1 for s in shots if s['clip']), 'of', len(shots), 'clips,', t, 's')
