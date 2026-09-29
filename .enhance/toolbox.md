# Toolbox inventory (session 2026-09-29)

Stack: Python 3.11+ package (`ganymede/`), stdlib-only generator scripts, and a
static site (`site/`, no framework, no bundler) that Vercel serves. CI is GitHub
Actions with five gates.

| Need | Covered by | Use in phase |
|---|---|---|
| Parallel read-only audit | `Agent` subagents (general-purpose), 5 dimension groups | 1 |
| Lint, format | `ruff` 0.16.5 (installed locally, not in CI) | 0, 4, 6 |
| Tests, coverage | `pytest`, `pytest-cov` (declared in `[dev]`) | 0, 4, 6 |
| Build gates | `ganymede.invariants`, `gen_palette.py`, `fetch_fonts.py`, `build_site_data.py` | 0, 4, 6 |
| Screenshots, interaction checks | Built-in browser pane (`mcp__Claude_Browser__*`) + `.claude/launch.json` static server | 2, 4, 6 |
| Design inspiration | Mobbin MCP (`search_screens`, `search_sections`) | 2 |
| Design critique and system | `impeccable`, `design:design-critique`, `design:accessibility-review` skills | 2, 4 |
| Motion review | `find-animation-opportunities`, `emil-design-eng` skills | 2 |
| Performance | `web-performance-optimization` skill; byte counts with `wc` | 1, 6 |
| Prose (reports, commits) | `ste100` skill rules applied by hand | all |
| GitHub | `gh` CLI, authenticated as `kandulanikhilvarma` | 5, 6 |
| Mermaid validation | `validate_and_render_mermaid_diagram` MCP | 5 |

## Used only where a real need exists

- Figma, Magic Patterns, Canva, Adobe: no Figma file or brand asset source exists
  for this project. The brand is already in `tokens.css`. Not used.
- Sentry, Vercel, Supabase, Neon MCPs: the project has no error tracker or database.
  Vercel deploy is out of scope (DEPLOY: no). Not used.

## Gaps (recommendations, not installed)

| Gap | Why it matters | Best option |
|---|---|---|
| Lighthouse / axe CLI | No automated accessibility or performance score for the site | `npx @axe-core/cli` and `npx lighthouse` in a CI job (needs Node in CI) |
| `pip-audit` | No dependency CVE check in CI | `pip install pip-audit` in the CI job |
| Headless Playwright in CI | Site JS has no automated test | `pytest-playwright` smoke test job |
