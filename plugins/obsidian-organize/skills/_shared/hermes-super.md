# hermes-wiki-super — target resolution and LLM-Wiki format

Shared reference for `add_wiki` and `process_clippings` when the target is the
`hermes-wiki-super` submodule constellation rather than a plain vault folder.

Read this before writing anything to a sub-repo.

## What the super repo is

`github.com/mybotagent/hermes-wiki-super` is a super repo: it holds no wiki
content of its own beyond `wiki-map.md`, and every knowledge domain is a
**separate GitHub repo mounted as a submodule** under `wiki/`.

```
hermes-wiki-super/
├── .gitmodules          the registry — one entry per domain repo
├── wiki-map.md          the top-level hub, grouped by category
├── wiki/
│   ├── hermes-wiki-claude-code/     ← its own repo, its own remote
│   ├── hermes-wiki-codex/
│   ├── harness-engineering-wiki/
│   └── …
├── scripts/
└── sync.sh              pull + submodule-foreach commit/push + ref bump
```

Consequences you must respect:

- A file under `wiki/<sub-repo>/` belongs to **that** repo. Committing it from
  the super repo only moves the submodule pointer; the content commit has to
  happen inside the submodule and be pushed to its own remote.
- Adding a domain means creating a repo **and** registering it in
  `.gitmodules` **and** adding a `wiki-map.md` row. Skipping any of the three
  leaves the domain invisible or unclonable.

## Step 1 — resolve the target sub-repo

Never guess from the topic name alone. Read the registry:

```bash
gh api repos/mybotagent/hermes-wiki-super/contents/.gitmodules \
  --jq '.content' | base64 -d
```

Match the topic against, in this order:

1. an existing submodule path — `wiki/<name>` where `<name>` relates to the topic
2. a `wiki-map.md` row whose hub or description covers the topic
3. the hub files themselves: a sub-repo whose `*-hub.md` already links related
   pages is the right home even when its repo name does not obviously match

Prefer an existing repo. A topic that is a *facet* of an existing domain
belongs inside it as a new page, not in a new repo — `claude-code-hooks` goes
into `hermes-wiki-claude-code`, it does not get its own repo.

Only when no sub-repo covers the domain do you create one (Step 4).

## Step 2 — the LLM-Wiki file format

Every page carries frontmatter and links by `[[wikilink]]`, never by relative
path — the vault resolves wikilinks across submodule boundaries, relative paths
break the moment a file moves.

A **hub** file (`<domain>-hub.md`), the entry point for a sub-repo:

```markdown
---
tags: ["wiki", "hub", "<domain>", "<category>"]
related: ["<other-hub>", "<other-hub>", "<domain>-log"]
---

# <Domain> Hub

> One line on what this domain covers — Karpathy-style LLM Wiki
> Last updated: <YYYY-MM-DD> | [[<domain>-log]] for change history.

## <Section>

- [[<page-slug>]] — one line on what the page holds
```

A **content** page:

```markdown
---
tags: ["wiki", "<domain>", "<subtopic>"]
related: ["<domain>-hub"]
source: <url or original filename>
updated: <YYYY-MM-DD>
---

# <Title>

> One-line summary.

<body>
```

Conventions that matter:

- Sections in a hub group pages by theme with a `## Heading`; a hub is a
  navigable index, not a flat list.
- Every content page links back to its hub via `related`, and the hub links
  down to it via a `[[wikilink]]` row. Both directions, or the graph breaks.
- `Last updated:` on the hub moves whenever you add a row.
- Korean prose in descriptions is normal here — match the register of the
  sub-repo you are writing into rather than translating it.

## Confirm before publishing

`--mode=super` writes content to **public** GitHub repos under `mybotagent/`.
Clippings and staged research are raw captures; they can hold private material
— an unpublished draft, a client name, a credential pasted into an article.
Before the first non-`--dry-run` push of a session, list what will be published
(each `filename -> owner/repo` and the resolved sub-repo) and get an explicit
go-ahead. `--dry-run` cannot be the brake: it is opt-in and not all writers
support it. The flag chooses the target; it does not authorize publishing a
specific set of files.

Skip the confirmation only when the operator already granted it for this batch
in the same session.

## Step 3 — write into an existing sub-repo


```bash
# work inside the submodule, not the super repo
cd wiki/<sub-repo>
```

1. Write or update the content page.
2. Add a `[[wikilink]]` row to the sub-repo's `*-hub.md` under the right
   section, and bump its `Last updated:`. Skip if a row for that page already
   exists — re-runs must not duplicate rows.
3. Commit **inside the submodule** and push to its own remote.
4. Return to the super repo, stage the moved submodule pointer, commit, push.

`sync.sh` at the super-repo root does steps 3-4 for **every dirty submodule at
once**, not only the ones this run touched. That makes it the right tool only
when this run changed several sub-repos AND the tree was clean beforehand — over
an unclean tree it will commit and push an operator's unrelated work-in-progress
to public repos. When in doubt, do the two-level commit by hand for the specific
sub-repos you changed.

## Step 4 — create a new sub-repo (only when no domain fits)

```bash
gh repo create mybotagent/<name> --public \
  --description "<domain> wiki (LLM-Wiki format)"
```

Then, from the super-repo root:

```bash
git submodule add https://github.com/mybotagent/<name>.git wiki/<name>
```

Seed the new repo with, at minimum:

- `<domain>-hub.md` — the hub, in the Step-2 format, with at least one row
- `README.md` — one paragraph on the domain's scope and a pointer to the hub

Then add a `wiki-map.md` row in the super repo, under the category heading it
belongs to (`## 🤖 AI Dev Tools`, `## ✍️ Content & Marketing`, …), creating the
heading only if genuinely new:

```markdown
- [[<domain>-hub]] — one line on the domain
```

Finally commit the `.gitmodules` + `wiki-map.md` + pointer change together.
A submodule added without its `wiki-map.md` row is unreachable from the graph.

## Guardrails

- Naming follows the neighbours. Most domain repos are `hermes-wiki-<domain>`
  or `<domain>-wiki`; read `.gitmodules` and match the dominant pattern rather
  than inventing a third.
- Never force-push a sub-repo, and never rewrite a page you did not author —
  append a section instead.
- Repo creation is public and hard to undo. Confirm the domain genuinely has no
  home before Step 4, and say which repo you are creating and why.
- If `gh` is unauthenticated or lacks access to `mybotagent`, stop and say so.
  Do not fall back to writing into the local vault as if it had synced.
