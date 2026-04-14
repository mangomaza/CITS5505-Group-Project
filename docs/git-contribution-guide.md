# Git Workflow Cheat Sheet

**Follow these steps every time you start new work on the repo.**

---

## Step 1 - Clean up your directory

> Remove any leftover files from previous testing so you're starting fresh.

```bash
# discard all changes to tracked files
git restore .

# remove untracked files & folders
git clean -fd
```

> **Heads up:** `git clean -fd` permanently deletes untracked files. Run `git clean -fd --dry-run` first to preview what gets removed.

---

## Step 2 - Switch to main

> Get back to the shared branch everyone works from.

```bash
git checkout main
```

---

## Step 3 - Pull the latest from the repo

> Someone on the team may have merged changes since you last worked. This keeps your local copy up to date.

```bash
git pull origin main
```

---

## Step 4 - Create your branch

> Never work directly on main. Every piece of work gets its own branch.

```bash
git checkout -b your-branch-name
```

**Branch naming convention:**
- `feature/login_page`
- `fix/header_bug`
- `chore/update_readme`

---

## Step 5 - Do your work

> Make your changes. Use these commands to check what you've done before committing.

```bash
# see which files changed
git status

# see the exact line-by-line changes
git diff
```

---

## Step 6 - Stage & commit

> Save your changes with a clear message so the rest of the team knows what you did.

```bash
# stage all your changes
git add .

# commit with a clear message
git commit -m "Add login form validation"
```

**Write commit messages that say *what* you did, not "fixed stuff" or "updates".**

---

## Step 7 - Pull main into your branch before pushing

> This is where you catch conflicts *before* they reach the repo. If anyone merged work while you were on your branch, this pulls those changes in so you can resolve conflicts on your machine.

```bash
git pull origin main
```

If there are conflicts, Git will flag them in the affected files. Open each one, resolve the conflict, then:

```bash
git add .
git commit -m "Resolve merge conflicts with main"
```

If there are no conflicts, you're good to move on.

---

## Step 8 - Push your branch

> Upload your branch to the repo so the team can see it.

```bash
git push origin your-branch-name
```

---

## Step 9 - Open a Pull Request

> Go to the repo on GitHub and get the team to review your changes before merging into main.

1. Go to the repo on **github.com**
2. Click **"Compare & pull request"**
3. Add a description of what you changed and why
4. Assign everyone on the team as a reviewer
5. Submit the PR

> **Never merge your own PR** without at least one approval from the team.

---

## The flow at a glance

```
clean > checkout main > pull > branch > work > commit > pull main > push > PR
```

---

## The golden rules

1. **Never commit directly to main.**
2. **Always pull before you branch.**
3. **Always pull main into your branch before you push.**
4. **One feature = one branch = one PR.**
5. **When in doubt, run `git status`.**
