# Get started with Claude Code

## 1. Open the project

```bash
cd ~/flyball
claude
```

(If you extracted the delivered archive, git is already initialised with an initial commit. If you're starting from loose files instead, run the manual git setup at the bottom first.)

## 2. Paste this as your first message

Claude Code auto-reads `CLAUDE.md`, but give it an explicit kickoff so it starts on the right milestone:

> Read `README.md`, `CLAUDE.md`, and `docs/01`–`docs/05`. This is a two-Raspberry-Pi art machine (Spark = fast Unicorn controller, Slate = slow Inky canvas + state authority). We build in **macOS simulation first**, no hardware.
>
> Start with **Milestone M0 then M1** from `docs/05-roadmap.md`:
> 1. Scaffold the repo (`conductor/`, `controller/`, `shared/`) as a runnable Python project.
> 2. Implement the `Bus` abstraction over **WebSocket + JSON**, with the Conductor (Slate) as the single state authority and the Controller (Spark) as a thin client. Get `hello` / `state` / `button` / `ping`–`pong` round-tripping over `localhost:8765`.
> 3. Port the channel/option state machine (Subject / Context / Style / Engine; prev / next / commit / shift) from the described model, loading options from `shared/data/word_blocks.json`.
> 4. Render both **mocks**: the Spark as a 17×7 terminal matrix (colour bar + position pips + scrolling candidate), the Slate via an `InkyMock` PIL image (sideways left menu strip + sentence ribbon). Map keyboard `a/b/x/y` (Spark) and `a/b/c/d` (Slate) to buttons.
>
> Keep `Bus`, `Display`, `Buttons`, `ImageBackend`, and `Evolver` behind swappable interfaces exactly as specced. **Before writing code, give me a short plan and the file tree you intend to create**, and flag any of the "open questions" at the end of `docs/05-roadmap.md` that you need me to decide.

## 3. One-liner alternative

To feed the kickoff without pasting, keep the prompt above in a file and pipe it:

```bash
cd ~/flyball
claude "$(cat GET-STARTED.md | sed -n '/^> /,$p' | sed 's/^> //')"
```

(Or just run `claude` and paste — simpler.)

---

## Manual git setup (only if the archive's git wasn't used)

```bash
cd ~/flyball
git init -b main
git add .
git commit -m "Flyball: initial spec, docs, and project scaffold"
```

Set your identity if git prompts you:

```bash
git config user.name  "Your Name"
git config user.email "you@example.com"
```

When you're ready to push:

```bash
git remote add origin <your-repo-url>
git push -u origin main
```
