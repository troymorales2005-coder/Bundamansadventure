# Meme Coin Radar — GitHub + VS Code + Codex Basics

## Goal

John and Troy should both be able to use Codex inside VS Code, make changes independently, and safely combine those changes into one shared Meme Coin Radar codebase.

The basic architecture is:

```text
                     GitHub
                       │
              meme-coin-radar
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
        John's PC           Troy's PC
          VS Code             VS Code
          Codex               Codex
             │                   │
        john/* branches      troy/* branches
             │                   │
             └──── Pull Requests ┘
                       │
                       ▼
                      main
```

`main` is the shared, stable version of Meme Coin Radar.

Neither developer should normally make Codex changes directly on `main`.

---

# 1. Install the basics

Both John and Troy need:

```text
Git
VS Code
OpenAI Codex VS Code extension
GitHub account
```

Verify Git from the VS Code terminal:

```bash
git --version
```

Configure your identity once.

John:

```bash
git config --global user.name "John"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

Troy does the same with his own information.

You can check it with:

```bash
git config --global user.name
git config --global user.email
```

Sign into GitHub through VS Code's Accounts menu or use GitHub authentication through the terminal.

---

# 2. Create the shared GitHub repository

One person should create:

```text
meme-coin-radar
```

on GitHub.

Because we already have local Meme Coin Radar files, create the GitHub repository **without adding a README, .gitignore, or license**. This avoids unnecessary conflicts during the first push.

Make the repository private if desired.

Then add the other developer as a collaborator:

```text
GitHub Repository
→ Settings
→ Collaborators
→ Add people
```

Both John and Troy should have write access.

---

# 3. Protect secrets BEFORE the first commit

The Meme Coin Radar will eventually contain things such as:

```text
Supabase credentials
API keys
Twitter/X credentials
RPC URLs
provider tokens
database configuration
```

These must not be committed.

Create:

```text
.gitignore
```

A reasonable Python starting point is:

```gitignore
# Environment variables
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# VS Code
.vscode/

# Testing/cache
.pytest_cache/
.coverage

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Local databases
*.db
*.sqlite
*.sqlite3
```

Instead of committing `.env`, eventually commit:

```text
.env.example
```

containing only variable names:

```env
SUPABASE_URL=
SUPABASE_KEY=
X_API_KEY=
```

Never real credentials.

---

# 4. Connect the existing project to GitHub

The person currently holding the main Meme Coin Radar workspace opens that project in VS Code.

Open:

```text
Terminal → New Terminal
```

Then:

```bash
git init
```

Check:

```bash
git status
```

Stage the project:

```bash
git add .
```

Create the initial baseline:

```bash
git commit -m "chore: initial Meme Coin Radar baseline"
```

Set the primary branch:

```bash
git branch -M main
```

Connect GitHub:

```bash
git remote add origin https://github.com/OWNER/meme-coin-radar.git
```

Verify:

```bash
git remote -v
```

Push:

```bash
git push -u origin main
```

GitHub is now the shared source of truth.

---

# 5. Second developer clones the project

The other developer should **clone the GitHub repository instead of copying the folder manually**.

Example:

```bash
git clone https://github.com/OWNER/meme-coin-radar.git
```

Then:

```bash
cd meme-coin-radar
```

Open it in VS Code:

```bash
code .
```

Both developers now have independent local copies connected to the same GitHub repository.

---

# 6. Our branch naming system

John uses:

```text
john/<task>
```

Examples:

```text
john/supabase-schema
john/flask-dashboard
john/market-scanner
john/docker-compose
john/scoring-engine
```

Troy uses:

```text
troy/<task>
```

Examples:

```text
troy/ct-scanner
troy/radar-ui
troy/narrative-engine
troy/coin-detail-page
```

This makes GitHub history immediately understandable.

Do **not** use one permanent `john` branch and one permanent `troy` branch.

Create a fresh branch for each meaningful piece of work.

---

# 7. The procedure BEFORE asking Codex to code

Every new coding session should begin here.

First:

```bash
git switch main
```

Then download the newest shared version:

```bash
git pull origin main
```

Now create a task branch.

Example:

```bash
git switch -c john/supabase-schema
```

Verify:

```bash
git branch --show-current
```

Expected result:

```text
john/supabase-schema
```

**Only now should Codex begin modifying the project.**

---

# 8. Using Codex safely

Codex works on whatever workspace and branch are currently open in VS Code.

So before giving Codex a large task, confirm:

```bash
git status
git branch --show-current
```

A good Codex instruction would be:

```text
We are working on the john/supabase-schema branch.

Implement the Supabase schema layer for Meme Coin Radar.

Do not commit, push, merge, or modify Git configuration.

When finished, summarize every file you changed and any tests I should run.
```

At least during the early development phase, **John and Troy should control Git operations themselves**.

Codex can:

```text
write code
change files
run tests
inspect the repository
explain diffs
help resolve conflicts
```

But we should manually approve:

```text
commits
pushes
pull requests
merges
```

That gives us an intentional checkpoint between AI-generated code and shared project history.

---

# 9. Review Codex's work before committing

After Codex finishes:

```bash
git status
```

Then:

```bash
git diff
```

Review what actually changed.

Run the appropriate tests.

Eventually this might be:

```bash
pytest
```

or:

```bash
docker compose up --build
```

Do not commit broken code just because Codex says the task is complete.

---

# 10. Commit the change

Stage the files.

For everything:

```bash
git add .
```

Or, preferably when appropriate:

```bash
git add app/
git add tests/
```

Then commit:

```bash
git commit -m "feat: add Supabase schema layer"
```

Useful prefixes:

```text
feat:     new functionality
fix:      bug fix
refactor: restructuring without changing behavior
test:     tests
docs:     documentation
chore:    tooling/configuration/maintenance
```

Examples:

```text
feat: add CT mention scanner
feat: add radar scoring service
fix: prevent duplicate coin snapshots
refactor: separate Flask routes from scanner workers
test: add radar scoring tests
docs: document local Docker setup
chore: configure Docker Compose
```

A commit should represent one understandable unit of work.

---

# 11. Push your branch

First push:

```bash
git push -u origin john/supabase-schema
```

After that:

```bash
git push
```

The branch now exists both locally and on GitHub.

---

# 12. Open a Pull Request

Go to GitHub.

You should see the recently pushed branch.

Choose:

```text
Compare & pull request
```

The pull request should be:

```text
john/supabase-schema
        ↓
main
```

Describe:

```text
What changed?

Why?

How was it tested?

Anything the other developer needs to know?
```

Example:

```text
Adds the initial Supabase database layer.

Changes:
- Adds Supabase client
- Adds repository classes
- Adds environment variable configuration
- Adds connection health check

Testing:
- Local import test passed
- Supabase connection tested
- Existing Flask startup still works
```

---

# 13. Other developer reviews

If John created the PR, Troy reviews it.

If Troy created the PR, John reviews it.

Look at:

```text
Files changed
```

Check what Codex actually modified.

The reviewer can:

```text
comment
request changes
approve
```

For significant architecture changes, discussion should happen here rather than silently pushing more code onto `main`.

---

# 14. Merge into main

Once the work is good:

```text
Pull Request
→ Merge
```

For this project, **Squash and merge** is a good default because one feature branch becomes one clean entry in `main` history.

After merging, delete the remote feature branch.

The completed flow looks like:

```text
main
 │
 ├──── john/supabase-schema
 │            │
 │       Codex changes
 │            │
 │         commits
 │            │
 │           PR
 │            │
 ◄────────── merge
 │
 main
```

---

# 15. Sync after someone else's PR is merged

Suppose Troy merges something while John is working.

Before John's next task:

```bash
git switch main
git pull origin main
```

John now has Troy's changes.

Then create the next branch:

```bash
git switch -c john/new-task
```

The rule is simple:

```text
UPDATE MAIN FIRST.
CREATE BRANCH SECOND.
ASK CODEX TO WORK THIRD.
```

---

# 16. Clean up old branches

After a PR is merged:

```bash
git switch main
git pull origin main
```

Delete your local branch:

```bash
git branch -d john/supabase-schema
```

This keeps local repositories understandable.

---

# 17. What if John and Troy change the same code?

Git may report a merge conflict.

Do not panic and do not force-push `main`.

While still on your feature branch:

```bash
git fetch origin
git merge origin/main
```

Git may show:

```text
CONFLICT
```

VS Code has a merge editor that shows both versions.

Resolve the conflict deliberately.

Then:

```bash
git add .
git commit -m "merge: resolve main branch conflicts"
git push
```

Run the tests again after resolving conflicts.

For our first version of the project, prefer a normal merge when syncing a feature branch. We can introduce rebasing later if we decide we need a cleaner advanced workflow.

---

# 18. The rules John and Troy should follow

1. `main` represents the stable shared project.
2. Never begin Codex work on `main`.
3. Pull the newest `main` before starting a task.
4. Create a new branch for every task.
5. John uses `john/*`; Troy uses `troy/*`.
6. Never share the same working branch.
7. Review `git diff` before committing AI-generated changes.
8. Run relevant tests before pushing.
9. Never commit `.env`, credentials, tokens, or API keys.
10. Push the feature branch, then open a PR.
11. The other developer reviews important PRs.
12. Merge into `main` only through the agreed workflow.
13. After a merge, update local `main` before doing new work.
14. Never use `git push --force` against `main`.

---

# Daily Cheat Sheet

### Start work

```bash
git switch main
git pull origin main
git switch -c john/my-new-feature
```

### Let Codex work

Then inspect:

```bash
git status
git diff
```

### Save work

```bash
git add .
git commit -m "feat: describe the feature"
```

### Share it

```bash
git push -u origin john/my-new-feature
```

Then:

```text
Open GitHub
→ Create Pull Request
→ Review
→ Merge
```

### After merge

```bash
git switch main
git pull origin main
git branch -d john/my-new-feature
```

---

# Mental model

Think of the system this way:

```text
CODEx
writes the code

      ↓

VS CODE
is where we work

      ↓

GIT
tracks every version

      ↓

BRANCH
isolates one person's/task's work

      ↓

GITHUB
shares that branch

      ↓

PULL REQUEST
reviews that work

      ↓

MAIN
becomes the accepted Meme Coin Radar
```

That is the basic collaboration system for Meme Coin Radar.