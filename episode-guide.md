# Make one episode with the DSE agents

You are producing one episode, not a season. Call the agents in order. Review each result before the next call. Stop after the clips. The edit happens in Canva by a person.

The agents are private and free. Call them with the Blocks caller below. Input ids must match the card exactly.

1. `dse_episode_script` — https://app.blocks.ai/agents/dse_episode_script
2. `dse_visual_bible` — https://app.blocks.ai/agents/dse_visual_bible
3. `dse_episode_stills` — https://app.blocks.ai/agents/dse_episode_stills
4. `dse_episode_clips` — https://app.blocks.ai/agents/dse_episode_clips

Call the visual bible after the script is accepted, and only when that script puts a character, wardrobe look, location, or prop on screen that the library does not already have. Then stills, then clips.

## Setup

### Blocks caller

Every call goes through the Blocks caller skill: https://github.com/CagedEther/blocks-caller-skill. If `~/blocks-caller/call-blocks-agent.mjs` does not exist, install that skill and run its one-time setup first. It installs `@blocks-network/sdk`, writes the caller, and stores the user's key in `~/blocks-caller/.env`. Do not print the key, paste it into a chat, or commit `.env`.

You also need an invite to each agent you will call. If an inspect call returns `Agent not found`, the user has not been invited yet.

### Project folder

Work in the user's series folder. It must contain:

```text
<series>/
  visual-bible/        clone of https://github.com/CagedEther/dse-visual-bible
  scripts/             library.py and the two review-page builders
  story/episode-NN/    one folder per episode
```

If the folder is empty, clone https://github.com/CagedEther/dse-episode-kit into it, then clone https://github.com/CagedEther/dse-visual-bible into `visual-bible/` inside it. Python 3 is needed for `scripts/`. After cloning, run `python3 scripts/library.py registry` once. The registry records which episodes use each entity, so it has to be rebuilt for this folder's episodes before `check` passes.

For each episode, save files under `story/episode-NN/`:

| File | From |
| --- | --- |
| `brief.md` | The user's brief, from `episode-brief-template.md` |
| `episode.md` | `episode_script` from step 1 |
| `shot-prompts.json` | `shot_prompts` from step 1 |
| `motion-prompts.json` | `motion_prompts` from step 1 |
| `frames/` | The unzipped stills from step 3 |
| `clips/` | The unzipped clips and `clips-report.md` from step 4 |
| `results/` | Raw agent output, as returned |

Run the caller from the series folder. Paths in `--parts` and `--output-dir` are relative to it:

```bash
CALLER="$HOME/blocks-caller/call-blocks-agent.mjs"
ENV="$HOME/blocks-caller/.env"
```

Before the first call to an agent, inspect its card. That command does not submit a task:

```bash
node --env-file="$ENV" "$CALLER" \
  --agent "https://app.blocks.ai/agents/dse_episode_script" \
  --inspect
```

Repeat `--inspect` for `dse_visual_bible`, `dse_episode_stills`, and `dse_episode_clips`. Use the declared input ids from the card.

Every real call uses `--billing-mode free` and `--parts`. Each part has `partId` plus exactly one of `text` or `filePath`. Save artifacts with `--output-dir` set to a directory you create for that episode.

```bash
node --env-file="$ENV" "$CALLER" \
  --agent "https://app.blocks.ai/agents/dse_episode_script" \
  --billing-mode free \
  --output-dir "story/episode-01/results" \
  --parts '[{"partId":"brief","text":"..."},{"partId":"episode_number","text":"01"},{"partId":"notes","text":"About 110 seconds. Voice-over only."}]'
```

For a long brief or a JSON file, write the parts array to `story/episode-NN/results/parts.json` and pass `--parts @story/episode-NN/results/parts.json`. For the clips zip, use `filePath` and `contentType` `application/zip` on the `frames` part. `filePath` may be relative to the series folder.

If the wait times out, do not send the task again. Inspect the returned task id first. Reuse `--idempotency-key` only when retrying that same intended task after a transport failure. These agents are free. Do not switch billing mode to `paid`.

## 1. Script

Send:

- `brief` (required): who the episode follows, what happens, and how it ends. One episode. Name only people who should appear.
- `episode_number` (optional): `01`, `2`, or `02`. Shot ids use this number.
- `notes` (optional): length, tone, or things to leave out. Default shape is about 90–120 seconds, voice-over only, no on-screen dialogue.

You get three files:

- `episode_script`: markdown. Read this. After the shot list it has a Visual bible section with three subsections: Characters, Scenes, and Items. A scene is a place. An item is a prop. Each table row is one plate to create before stills. `None` means that group is already in the library. The columns match the visual bible agent: id, name, identity, required marks, forbidden marks, and the shots that show it.
- `shot_prompts`: a JSON array. Pass this text through to stills. Change it only to point a shot at a plate added in the visual-bible step.
- `motion_prompts`: a JSON object. Pass this text through unchanged.

Before stills, check the markdown:

- Third-person voice-over. It tells the story. It does not describe hair, clothes, furniture, or props.
- Beats are hook, setup, development, turn, cliffhanger.
- Every shot is one small action, 3–8 seconds. Two people may share a frame. They do not touch or speak.
- The shot ids in the markdown, `shot_prompts`, and `motion_prompts` are the same list.

If the agent refuses, the brief was not a story. Rewrite the brief. Do not invent a plot to replace a refusal. If the draft is wrong, change `brief` or `notes` and call the script agent again. Do not hand-edit the JSON unless you are fixing a plate path the stills report rejected, or pointing a shot at a plate you just added to the library.

## 2. Visual bible

Do this after the script is accepted and before stills. Skip it when the Visual bible section of the script is `None` under Characters, Scenes, and Items, and every person, place, outfit, and object on screen is already an approved id in `visual-bible/registry.json`.

Read that section first. Each row is a character, location, or prop the episode should recognize again, and who is not in the library yet. The shot prompts leave that id out of `entities` until the plate exists. A crowd, a judge panel, or passersby stay unmarked figures. They do not get a row. A new wardrobe look is not in that section: add one when the episode puts the lead in clothes the library does not have.

Call `dse_visual_bible` once for each new entry. Send:

- `kind` (required): `character`, `wardrobe`, `location`, or `prop`.
- `name` (required): what the picture calls them, such as `a woman in her forties` or `the fan`.
- `identity` (required): one or two sentences. What it is, and how it should read. Black ink only. No color, no text.
- `required_marks` (required): semicolon-separated marks this plate must show. A character needs two or three marks that nobody else already owns. Check `visual-bible/marks.md` first.
- `forbidden_marks` (optional): semicolon-separated marks the plate must never show. For a character, the agent also forbids the lead's spiral earring, teardrop pendant, and black vest.
- `id` (optional): folder id, lowercase with hyphens. Derived from the name when omitted.
- `wearer` (required for wardrobe): the approved character id who wears the look, such as `lead`.
- `episode` (optional): label for the spec, such as `E06`.
- `candidates` (optional): `1` to `3`. Default `3`.

This agent draws the first plate only: `front` for a character, `look` for wardrobe, `establishing` for a location, `insert` for a prop.

You get `plates_zip`, `spec`, and `report`. Look at every candidate and pick one. File it the way the report says: unzip into `visual-bible/_drafts/<id>/`, save `spec.md` beside the images, rename the chosen file to the anchor name (`front.png`, `look.png`, `establishing.png`, or `insert.png`), then run:

```bash
python3 scripts/library.py promote <id>
```

Promote moves the draft into the library and rebuilds the registry. Run `python3 scripts/library.py check` before stills. Episodes never reference anything in `_drafts/`.

Then put the new id on the shots that show it. In `shot_prompts`, set `entities` to that id. If the image prompt still describes a stand-in, or leaves the new person off screen, change that description so the still matches the new plate. Leave the voice-over as it is. The stills agent rejects an id that is not approved.

## 3. Stills

Send:

- `shot_prompts`: the JSON array from step 1, as text.
- `only` (optional): comma-separated shot ids, such as `e01-sc01-sh02`. Leave empty the first time.

You get `frames_zip` and `report`. Each image is named like `E01-SC01-SH01.png`. The files may be JPEG data with a `.png` name. Keep those names.

Unzip the frames into `story/episode-NN/frames/`. Then build the review page and open it for the person:

```bash
python3 scripts/build_review.py story/episode-NN
```

This writes `story/episode-NN/stills-review.html`: each still beside its shot-list guidance and the voice-over over it. The person flags shots and uses **Copy fix list** to paste one line per flagged shot back to you. Rebuild the page after every rerun. [html-review-guide.md](html-review-guide.md) describes the page.

Read the report. The person looks at every frame before any clip is made. Reject a frame that has text, color, a second design of a locked character, or the wrong person. Rerun only the bad ids:

`only`: `e01-sc02-sh01, e01-sc04-sh02`

At most 16 shots per call. If the report says a plate path is missing, fix that path in `shot_prompts` and rerun those ids. Do not ask this agent to invent prompts.

## 4. Clips

Send only frames you accept.

- `frames`: a zip of those stills, filenames unchanged. Under 25MB.
- `motion_prompts`: the JSON object from step 1, as text.
- `only` (optional): shot ids to animate, such as `E01-SC01-SH02`. Leave empty to animate every still in the zip.
- `takes` (optional): seeded variants per shot, 1 to 4. Default 1.
- `seed` (optional): base seed. Take k uses seed+k. Leave empty for random seeds.

You get `clips_zip` and `report`. With one take, each clip is `{SHOT_ID}.mp4`. With more, each take is `{SHOT_ID}/seed-{SEED}.mp4`. The report lists the seed of every clip.

Unzip the clips into `story/episode-NN/clips/` and save the report there as `clips-report.md`. When there are several takes, copy the chosen take to `clips/{SHOT_ID}.mp4`. Then build the review page and open it for the person:

```bash
python3 scripts/build_clips_review.py story/episode-NN
```

This writes `story/episode-NN/clips-review.html`: each clip beside its motion line, seed, and voice-over. The person flags clips and pastes the fix list back to you.

The motion line is the only change. The still already defines the picture. The clip can only move a short way from the pose in that still. A gesture people make while speaking, such as pointing or presenting, will open the mouth even when the line says the lips stay closed. Telling that person to hold still will cancel the gesture. See [motion-clip-guide.md](motion-clip-guide.md).

If a clip turns a head too far, morphs the face, adds objects, talks, or does a second action, keep the current file and rerun that id with `takes` set to 3. Watch each take all the way through, especially the mouth, and replace the file only when a new take is better. To reproduce a clip, rerun its id with its seed and `takes` 1. If every take fails the same way, the still or the motion line is the problem. If the report lists motion lines to rewrite, fix them before rerunning. If the report says a shot was not started because the time budget ran out, call again with `only` set to the remaining ids. Takes run side by side, but more takes still use more of the budget, so use `only` for takes runs.

## Stop

Hand the person the markdown script, the approved stills, and the mp4s. They record the voice-over and assemble the episode themselves. Do not edit the episode, add music, or call another agent.
