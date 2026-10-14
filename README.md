# bmxpartsdepot.com

BMX Parts Depot is a static site hosted on GitHub Pages. The repository includes
the website, generated fitment guides, and two games. Read `CLAUDE.md` for the
existing architecture, content rules, and project history. Those notes apply
whether working in ChatGPT, Codex, or Claude.

## Set up on a Mac

Install Git and Python 3.10 or newer. Authenticate GitHub CLI as `joe-mission` if you need to
push changes. Browser sign-in alone does not authenticate the CLI.

```sh
gh auth login --hostname github.com --git-protocol https --web
mkdir -p ~/Documents/Codex/Projects
cd ~/Documents/Codex/Projects
git clone https://github.com/joe-mission/bmxpartsdepot.com.git
cd bmxpartsdepot.com
python3 -m venv .venv
source .venv/bin/activate
```

If the checkout already exists, use it instead of cloning again. Add that folder
as a local project in the desktop app. Each computer needs its own checkout and
GitHub authorization. Git synchronizes committed files, not chat history.

## Start each work session

```sh
git remote get-url origin
git status --short
git branch --show-current
git pull --ff-only
```

Confirm that origin is `joe-mission/bmxpartsdepot.com`. Pull only after checking
for local work. If there are uncommitted changes or diverging history, reconcile
them before editing. Do not discard work or force-push to make a pull succeed.
Finish and push work on one computer before continuing it on the other.

## Build and preview

Activate `.venv` at the start of each terminal session. This work Mac's checkout
has a Python 3.12 environment because the system Python is too old for the build.

```sh
source .venv/bin/activate
python3 build.py
python3 schema_terms.py
python3 -m http.server 8000
```

Open http://localhost:8000. The project uses the Python standard library and has
no Node dependency installation. Edit guide sources in `content/`, then regenerate
the HTML. Do not hand-edit generated guides, sitemap, robots, or llms files.
Run `python3 test_autolink.py` when changing the auto-linker.

## Publish to GitHub Pages

The existing project notes specify the `main` branch and repository root as the
Pages source. A push to `main` publishes changes, including generated HTML.
Preserve `CNAME` and the current hosting configuration.

After reviewing the diff and completing the checks appropriate to the change,
stage the specific intended files and commit them. Then:

```sh
git pull --ff-only origin main
git push origin main
```

Use these publishing commands only from `main` with the intended changes committed.
Check the GitHub Pages deployment result and https://bmxpartsdepot.com afterward.
A successful push alone does not establish that deployment succeeded.

## Repository boundaries

This project is only `joe-mission/bmxpartsdepot.com`. Do not access or change
OCvibe repositories, projects, organization settings, or deployment services.
The separate `joe-mission/danaloverde.com` site uses Vercel, not this publishing
process. Keep credentials and recovery codes out of the repository.
