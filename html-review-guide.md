# Review stills or clips in one HTML page

Build one self-contained HTML file in the episode folder. A person opens it in a browser, walks the shot list, and marks what needs to change. The same page reviews stills or clips. The ledger stays the same. Only the picture on the left, and which prompt sits in front, changes with the pass.

Episode 05 is the reference. Its pages are `story/episode-05/stills-review.html` and `story/episode-05/clips-review.html`. They cover 17 shots across six scenes, 110 seconds, from `episode.md`.

The file sits next to `frames/` and `clips/` so the pictures load by relative path. It needs no server, no framework, and no network beyond the typefaces. All shot data is written into the page. Notes stay in the browser.

## Build the page

From the repo root:

```bash
python3 scripts/build_review.py story/episode-05
python3 scripts/build_clips_review.py story/episode-05
```

The first writes `stills-review.html`. The second writes `clips-review.html`. Run the one that matches the pass you are handing over. Run it again after stills, clips, prompts, or the shot list change. Rebuilding replaces the HTML and leaves the reviewer’s notes in place, as long as the storage key below stays the same.

Both scripts read the episode number and title from the `# Episode NN — Title` heading in `episode.md`, and use them for the page title and the storage key.

Open the file from the episode folder. `frames/E05-SC01-SH01.png` and `clips/E05-SC01-SH01.mp4` must resolve next to the HTML.

## What the page reads

| File | Stills page | Clips page |
| --- | --- | --- |
| `episode.md` | Title, scenes, shot list, voice-over | Same |
| `shot-prompts.json` | The still prompt, under a collapsed row | Unused on the page |
| `motion-prompts.json` | The motion line, collapsed | The motion line, unless a corrected line exists |
| `frames/SHOT_ID.png` | The picture on the left | Poster frame, and the still in the comparison row |
| `clips/SHOT_ID.mp4` | Unused | The clip on the left |
| `clips/clips-report.md` | Unused | Seed, from a line `- SHOT_ID seed N: ok` |
| `clips/motion-used.json` | Unused | The motion line actually sent, when it differs from `motion-prompts.json` |
| `clips/first-pass/SHOT_ID.mp4` | Unused | An earlier take, shown beside the still |
| `clips/first-pass/motion-used.json` | Unused | The line that made that earlier take |

Shot ids in `episode.md` and `motion-prompts.json` are uppercase (`E05-SC01-SH01`). Ids in `shot-prompts.json` are lowercase. Match them case-insensitively.

A shot with no clip still appears on the clips page. The left side shows the still and the line “No clip yet. Showing the still.”

## One ledger

Both pages are a contact sheet. Ink on warm paper. One row per shot, grouped under scene headings, in shot-list order.

Sticky bar at the top:

- Title: `Episode 05 · The Crew · Stills review` or `Episode 05 · The Crew · Clips review`.
- A count. Stills: `17 shots · 1:50 · 0 flagged`. Clips: `17 of 17 clips · 1:50 · 0 flagged`. The middle number is the sum of the shot durations. The last number is how many rows are flagged in this browser.
- **Flagged only.** Hides every row that is not flagged, and hides the scene headings with them. The flagged rows stay in shot order.
- **Copy fix list.** Copies one line per flagged shot, for pasting back into the thread.
- **Clear all.** Asks for a second click within three seconds, then wipes the notes for this page.

Under the bar, one short intro. For stills, say that each row is a still beside its shot-list guidance and the voice-over estimated over it, and that the estimate can land a beat early or late once the read is recorded. For clips, say that each row is a clip beside the motion prompt that made it, its seed, and the voice-over, and that the marker under the clip is where the cut lands.

Scene heading: the code in small caps mono (`SC01`), then the scene title in italic serif (`Opening hook (0:00–0:18)`).

Each row is two columns. The picture is 220px wide, 9:16, cropped to fill. The notes column is the rest. A flagged row gets a solid ink bar on its left edge. Below 640px the columns stack and the picture caps at 260px.

Shared fields, in this order after the picture:

1. Shot id in mono, then the timeline range (`0:00–0:06`).
2. Chips for duration, framing, and motion level. Write the level with the underscore turned into a space (`very low`).
3. **Visual guidance.** The sentence after the last `·` on the shot-list line.
4. **Voice-over.** The sentences estimated to play during the shot. If none overlap, write “No voice-over over this shot.”
5. **Needs fix**, a checkbox, and a note box.

Typing in the note box flags the row. Unchecking the box keeps the note. Notes save on every change to `localStorage`.

## Stills on the left

The left cell is the still. Clicking it opens the frame large, with the shot id and timeline range as the caption. Close returns to the row. If the file is missing, the cell reads `Missing frames/E05-SC01-SH01.png`.

Chips: `6s`, the framing (`medium shot`), `motion: low`.

After voice-over, two collapsed rows: **Shot prompt** (from `shot-prompts.json`) and **Motion prompt** (from `motion-prompts.json`). The motion row reads “None.” when that shot has no line.

Note placeholder: “What should change in this still?”

Copy line: `E05-SC01-SH04: brow reads as a smile; redraw it gathered.` A flagged shot with an empty note copies as `E05-SC01-SH04: (no note)`.

Storage key for episode 05: `dse-e05-stills-review-v2`. A new episode starts at `dse-eNN-stills-review-v1`. Keep an existing key so notes already in a reviewer’s browser survive a rebuild. Change the key only when the note shape changes, which discards the old notes.

## Clips on the left

The left cell is a `<video>`: controls on, looped, muted, inline, poster set to the still, preload metadata. It does not autoplay.

Under it, a checkbox **Loop the cut (3s of 5s)**, on by default. While it is on, playback jumps back to the start once `currentTime` reaches the shot’s cut length (`dur`), so the reviewer watches the part that will be used. Turning it off plays the full generation (`gen` seconds). A 3-second cut from a 5-second generation is the usual case. A 6-second cut from a 10-second generation is the long case. `gen` comes from `generate_seconds` on the motion line that was sent, or 5 when the cut is 5 seconds or under and 10 when it is longer.

Chips: `cut 3s`, `generated 5s`, `motion: low`, and `seed 323098730` when `clips-report.md` has a seed for that shot.

**Motion prompt** is open, not collapsed. Show the line from `clips/motion-used.json` when that file has this shot, otherwise the line from `motion-prompts.json`. When those two strings differ, add “This clip used a corrected line, not the one in motion-prompts.json.” and put the original line in a collapsed row labeled **Line in motion-prompts.json**.

After voice-over, a collapsed comparison. With no earlier take, the summary is **Still** and the thumbnail is the first frame. When `clips/first-pass/SHOT_ID.mp4` exists, the summary is **Still and earlier take**, the second thumbnail plays that file, and the caption under it is “Earlier take, old line”, followed by the motion line from `clips/first-pass/motion-used.json` (or from `motion-prompts.json` when that file has no line).

Note placeholder: “What should change in this clip or its motion prompt?”

Copy line includes the seed: `E05-SC01-SH04 (seed 323098730): head turns the wrong way in the last second.` Omit the seed parenthesis when the report has none.

Storage key: `dse-e05-clips-review-v1`, and `dse-eNN-clips-review-v1` for a new episode. Same rule as stills: keep the key across rebuilds.

## How to place the voice-over

The shot list is the clock. Walk the `- **E05-SC…** · Ns ·` lines from the top and give each shot a start and end. Episode 05 begins at 0 and ends at 110.

Voice-over paragraphs are the `[mm:ss]` lines. Each paragraph runs from its mark until the next mark, or until the episode length for the last one.

Split each paragraph into sentences. Give each sentence a slice of that paragraph’s duration in proportion to its word count. A sentence belongs to a shot when the overlap is at least 0.75 seconds. If the sentence started more than half a second before the shot, mark it as continuing from the previous shot.

Stills cite the paragraph mark: `≈0:00 · from the [0:00] paragraph`. Add `· starts in the previous shot` when the sentence continues. Clips cite the sentence start only: `≈0:00`, plus the continuation note. Round the displayed second.

Say in the intro that this is an estimate. The recorded read will not hit these boundaries exactly.

## Look

Warm paper, black ink, hairline rules. IBM Plex Sans for the UI, IBM Plex Serif for voice-over and motion lines, IBM Plex Mono for ids, times, chips, and prompts.

| Token | Light | Dark |
| --- | --- | --- |
| paper | `#fbfaf7` | `#121211` |
| ink | `#111111` | `#ecebe6` |
| muted | `#5d5c58` | `#a09e97` |
| rule | `#d9d7d0` | `#33322f` |
| wash | `#f0eee8` | `#1c1c1a` |

Dark follows the system. The column measure for prose is about 68 characters. The page column is 1100px. Buttons are ink-filled; the secondary button (Clear all) is a ghost. Focus rings are a 2px ink outline. Honor `prefers-reduced-motion`.

Write every string into the page as text. Prompts and voice-over contain characters that must not be treated as HTML.

## Check it

Open the file and confirm:

- The shot count and the total time match `episode.md`. Episode 05 is 17 shots and 1:50.
- Scene order matches the `### SC` headings.
- A still enlarges and closes. A clip plays, stays muted, and restarts at the cut while **Loop the cut** is on.
- A missing file shows the missing line, and the rest of the page still renders.
- Flagging a row, writing a note, copying the list, and reloading keeps the note. **Flagged only** leaves that row and hides the rest.
- On the clips page, a shot whose sent line differs from `motion-prompts.json` shows the corrected line in front and the original line collapsed. Episode 05 does this wherever `clips/motion-used.json` rewrote a line.
