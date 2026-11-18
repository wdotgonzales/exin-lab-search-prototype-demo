## What
<!-- What changed and why, in a few bullets -->
-

## How tested
<!-- Commands you ran and what you checked by hand -->
- [ ] `uv run pytest` passes
- [ ] `npm test`, `npm run lint`, `npm run build` pass
- [ ] Checked it manually in the browser (local)

## Screens
<!-- Screenshots for any UI change; delete if none -->

## Definition of Done
- [ ] Migration runs `upgrade` → `downgrade -1` → `upgrade` (if any)
- [ ] Tests cover the new behaviour (incl. database state where relevant)
- [ ] No secrets or URLs hard-coded; new settings added to `.env.example` (and SSM for prod)
- [ ] After merge: smoke-tested on https://exin-therapeutics.bubble-pop-rush.fyi
- [ ] README / Technical Design updated if behaviour changed
