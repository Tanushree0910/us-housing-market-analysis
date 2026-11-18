# GitHub setup (owner task)

The repo contains a ready-made GitHub rule set, `.github/rulesets/protect-main.json`. Once it is switched on, GitHub itself enforces these rules on `main` (CONSTITUTION.md Article 5):

- Changes reach `main` only through a pull request.
- The pull request must pass the **governance** check.
- No one can force-push to `main` or delete it.

AI agents can't change repository settings, so this one step is yours. No commands are needed: everything happens in the browser.

## Steps

1. **Download the rule file.**
   1. On GitHub, open the repo and go to `.github/rulesets/protect-main.json`.
   2. Click the **Download raw file** button (the arrow icon at the top right of the file).
   3. Save it anywhere on your computer.
2. **Open the repo's settings.** Go to the repo's main page and click **Settings** (top bar).
3. In the left menu, click **Rules**, then **Rulesets**.
4. Click **New ruleset**, then **Import a ruleset**.
5. Choose the `protect-main.json` file you downloaded in step 1.
6. Check that the page shows:
   - name **Protect main**, enforcement **Active**, target **Default branch**;
   - the rules **Restrict deletions**, **Block force pushes**, **Require a pull request before merging** (0 approvals), and **Require status checks to pass** with the check **governance**.
7. Scroll down and click **Create**.

## Good to know

- **Private repos on the free plan:** GitHub may say rulesets aren't enforced. If so, either make the repo public (Settings → General → Danger Zone → Change visibility) or upgrade the plan. The AI-side hooks still protect `main` either way.
- **0 approvals is on purpose.** GitHub doesn't let you approve your own pull request, and you are the only person on this repo.
- **Changing the rules later:** edit the ruleset in Settings → Rules → Rulesets. Also update `.github/rulesets/protect-main.json` so the repo keeps an accurate copy.
