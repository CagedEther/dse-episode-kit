# Making a good motion clip from a still

Image-to-video models treat your still as frame one and invent everything after it. They are good at small, continuous motion that the picture already implies. They fail when the prompt asks for something the picture cannot support, when the prompt is ambiguous, or when the clip runs long enough to drift. Most bad clips (heads that spin, faces that melt, objects that appear) trace back to one of those three.

This guide is general. The last section shows how the DSE agents apply it.

## 1. Start with a still that can move

The still decides most of the outcome. Before writing any motion:

- **Pick an angle that supports the motion.** A three-quarter face can turn a little either way. A strict profile, especially in flat line art, gives the model no depth cues, so it may "solve" a head turn by rotating the head the wrong way or all the way round. If a shot needs a head turn, draw it in three-quarter view.
- **Draw the pose the action starts from.** The clip begins in the still and can only move a short way from it. A hand already in the hair can scratch. It will not cleanly become both arms thrown overhead. If the action needs a different pose, redraw the still.
- **Leave room for the motion.** A hand that will rise needs space above it. Cloth that will sway needs a clear hem.
- **Keep hands simple or out of frame.** Interlocked fingers, hands touching faces, and hands holding small objects are where anatomy breaks first.
- **Make the silhouette readable.** If a person and the background merge, the model can't tell where the body ends.
- **Avoid ambiguous objects.** If it's unclear whether a laptop is open or closed, the model may change it. Draw it unmistakably.
- **Match the output aspect ratio.** Cropping or padding a still to fit a different ratio invites the model to fill the gap.

## 2. Write the motion, not the picture

The model can already see the picture. The prompt only says what changes.

**Structure:** subject, then one action with its size and direction, then what holds still, then the camera. "What holds still" is the mouth, the other figures, and the props. Do not tell the person who must move to hold still. Stacking "jaw holds still, lips pressed, everything holds" cancels the action.

> The woman on the left, in three-quarter view facing right, lifts her eyes slowly toward the window. Her head and shoulders hold still. Locked-off camera, minimal motion.

Rules that matter most:

1. **Phrase everything positively.** Video models don't follow negatives. "She does not turn her head" puts *turn her head* into the prompt and makes it more likely. Say what holds instead: "Her head stays in left-facing profile."
2. **One action per clip.** "She blinks, then smiles, then looks up" gets you a muddle. Split it into shots.
3. **Give the size and speed.** Words like *slightly*, *a few degrees*, *once*, *slowly*, *a fraction* keep motion small. Without them, models exaggerate.
4. **Anchor direction to the frame.** Use *left*, *right*, *toward the window*, *toward the woman on the right*. "She turns" alone leaves the direction open.
5. **Name the people by what's visible.** Use "the woman on the left in the black vest", not a character name. The model has never heard of your characters.
6. **Never contradict the still.** If the prompt says the laptop is closed and the image shows it open, the model will try to reconcile the two, often badly. Describe only what's in the frame.
7. **Keep it short.** Two or three sentences. Long prompts dilute the instruction that matters.
8. **Keep a short positive style line** ("black ink line art on warm cream paper, matching the source image"). Stylized images drift toward the model's default look: shading, color, photographic detail. A positive style anchor holds them. A list of "no color, no text" does not.
9. **Keep the mouth a drawn mark.** Voice-over carries the words, so a character rarely speaks on screen. Describe the mouth as it is drawn: "Her mouth stays one short horizontal line." Do not write "does not talk." That names talking.
   A gesture people make while speaking will open the mouth anyway. Pointing, presenting, explaining, sighing, and reacting all read as speech, and "lips stay closed" does not override them. Prefer a blink, a shift of the eyes, cloth, or a hand motion that does not read as conversation. If the shot must point or present, say the mouth line stays as drawn, generate several takes, and watch the mouth for the whole clip. A closed mouth in the first seconds often opens in the middle.

## 3. Camera

- Default to a **locked-off camera** and say so in the prompt. An unspecified camera tends to wander.
- If the shot is a camera move (push-in, pan), let the camera be the only motion. Subject motion plus camera motion doubles the chance of artifacts.
- One camera move per clip, slow and steady.

## 4. Length

Drift grows with time, so most artifacts appear in the second half of a clip.

- Generate the shortest duration that covers the cut.
- If the model only offers fixed lengths (Runway: 5 or 10 seconds), plan to trim. A 10-second generation for a 7-second cut gives you 3 seconds of slack to discard, usually from the end.
- For long beats, cut to a second framing instead of asking one clip to hold for longer.

## 5. Generate takes, keep seeds

The same prompt and image produce different results with different seeds. Treat generation as casting, not as a single shot.

- Generate 2–4 takes per shot with different seeds. Pick the best.
- Record the seed with every output. Same seed, image, and prompt reproduce the same result.
- When a take is close, keep its seed and change only the prompt. That isolates the effect of your wording. Watch the new clip before you replace the old one. The same seed with a rewritten prompt changes the good motion along with the bad.
- Keep every file you might go back to, and name it with its seed. If the new takes are worse, put the previous file back.
- When every take fails the same way, the problem is the still or the prompt, not luck. Go back to sections 1 and 2.

## 6. Review every clip

Watch each clip at full speed, then scrub it. Check:

- **Identity:** same face, hair, marks, and clothes in the last frame as in the first.
- **Anatomy:** head rotation, neck, hands, finger count, limbs that merge with furniture.
- **Objects:** nothing appears, disappears, opens, or closes.
- **Style:** the line work, paper, and palette hold to the end.
- **Action:** exactly one action, at the size you asked for.
- **Mouths:** the mouth stays the same drawn line for the whole clip, including the middle, unless the shot calls for speech.
- **Camera:** it stays put, or moves only as asked.
- **The tail:** the last 2 seconds, where drift lands.

## 7. Symptom, cause, fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Head turns far or spins | Profile view in flat art; "turn" in the prompt, even negated | State the facing direction; limit to "a few degrees"; redraw the still in three-quarter view |
| Face morphs or changes identity | Clip too long; large motion; small face in frame | Shorter clip; smaller motion; tighter framing |
| Objects appear or change | Prompt contradicts or mentions the object state; ambiguous drawing | Describe the object as it is in the still, or leave it out; redraw it clearly |
| Second, unwanted action | Several actions in the prompt; vague prompt | One action; name what holds still |
| Character seems to talk or mumble | Mouth left unspecified, or the action is one people do while speaking (pointing, presenting, explaining) | Describe the mouth as one short line that stays as drawn. If it is a speaking gesture, change the action or pick the take whose mouth stays a line the whole way |
| The gesture you asked for never happens | The prompt also tells that person to hold still, or the still's pose cannot do the action | Hold the mouth, the other figures, and the props. Let the actor move. Redraw the still if the pose does not support the action |
| A new take loses a motion the previous take had | A rewritten prompt, even on the same seed, changes the good part along with the bad | Keep the previous file. Replace it only after the new clip is better |
| Style drifts to shading or color | No style anchor; long clip | Short positive style line; shorter clip |
| Camera wanders | Camera unspecified | "Locked-off camera" |
| Hands mangle | Complex hand pose in the still | Simplify or hide hands in the still |
| Fine until the last seconds | Normal drift | Trim; freeze the last good frame |

## 8. Salvaging a nearly good clip

- **Trim** before the artifact starts.
- **Freeze** the last good frame for the remaining time. Slow, illustrated pieces hide this well.
- **Pin the last frame** to your still, if the model supports a last-frame keyframe. The clip then has to return to the drawing.
- **Edit only the bad stretch** with a video-to-video model, if you have one.
- **Regenerate** with the good take's seed and an adjusted prompt. Keep the previous file until the new one is better, then put it back if it is not.

## 9. Runway API notes

- Endpoint: `POST /v1/image_to_video` with `model`, `promptImage`, `promptText`, `ratio`, `duration`, and `seed`.
- `promptText` is at most 1000 characters. `seed` is an integer from 0 to 4294967295. Without a seed you get a random one and can't reproduce the result.
- Poll `GET /v1/tasks/{id}`. `PENDING`, `THROTTLED`, and `RUNNING` mean keep waiting. Submitting above your concurrency limit queues tasks as `THROTTLED` rather than rejecting them.
- Download outputs right away; the URLs are temporary.
- `promptImage` can be a list of `{uri, position}` keyframes on some models. Check that the model you use supports a `last` position before relying on it.

## 10. How the DSE agents apply this

- **`dse_episode_script`** writes each image prompt and motion line as a pair. Both state which way each face points. Motion lines are positive, one action, sized, and end with a camera instruction. The agent rejects and rewrites any motion line that uses *not*, *no*, *never*, *nothing*, or *without*. Shots that need a head turn are drawn in three-quarter view.
- **`dse_episode_clips`** sends a seed with every request and accepts `takes` (up to 4 seeded variants per shot) and `seed` (to reproduce a take). Every clip's seed is in the report. The report also flags motion lines with negative wording.
- **`scripts/animate_episode.py`** does the same locally with `--takes`, `--seed`, and `--pick`.
