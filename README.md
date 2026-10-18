# DSE episode kit

Everything an AI coding assistant (Claude, Codex, Cursor, and so on) needs to produce one short AI-animated episode with the DSE agents on [Blocks](https://app.blocks.ai). Here is a finished episode: [YouTube Short](https://youtube.com/shorts/F4liNjnaUCE?feature=share).

Using this kit doesn't require any technical knowledge. Open this folder in your AI assistant and say:

> Read episode-guide.md and set up this folder.

## What's here

| File | For |
| --- | --- |
| [`episode-guide.md`](episode-guide.md) | The step-by-step guide the assistant follows: script → visual bible → stills → clips |
| [`episode-brief-template.md`](episode-brief-template.md) | The template for your episode brief |
| [`motion-clip-guide.md`](motion-clip-guide.md) | Why some clips animate well and others drift |
| [`html-review-guide.md`](html-review-guide.md) | How the stills and clips review pages work |
| `scripts/` | Visual-bible library tool and review-page builders (Python 3) |
| `story/episode-05/` | A worked example: brief, script, prompts, stills, and review pages |

## Related

- Visual bible (clone into `visual-bible/`): https://github.com/CagedEther/dse-visual-bible
- Blocks caller skill (used for every agent call): https://github.com/CagedEther/blocks-caller-skill
