# Deploying djazair.dev

The `CI` workflow (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`:

1. **Test**: a syntax check and the unit tests, on Python 3.12 and 3.13.
2. **Build**: `python site/build.py`, uploaded as the `site` artifact.
3. **Deploy** to Cloudflare Pages, only after both pass, so a failing change never replaces the live site:
   - a push to `main` deploys to the project's production branch (`main`);
   - a pull request from this repository deploys a preview at `pr-<number>.<project>.pages.dev`, linked from the pull request. Pull requests from forks never deploy, because they can't see the secrets.

Until the settings below exist, the deploy step is skipped with a notice and everything else still runs.

## One-time setup (founder)

These need account access, so they aren't automated.

1. **Create the Pages project.** In Cloudflare, go to *Workers & Pages → Create → Pages → Upload assets* and create a project for the full site (for example `djazair-dev-site`), with `main` as the production branch. Keep the project that serves the holding page as it is: djazair.dev stays on the holding page until launch.
2. **Create an API token.** *My Profile → API Tokens → Create Token → Custom token*, with the single permission *Account → Cloudflare Pages → Edit* for the djazair.dev account. Give it an expiry date and note it in your password manager.
3. **Add them to GitHub.** In the repository, *Settings → Secrets and variables → Actions*:
   - secret `CLOUDFLARE_API_TOKEN`: the token;
   - secret `CLOUDFLARE_ACCOUNT_ID`: the account ID (shown in the Cloudflare dashboard sidebar);
   - variable `CLOUDFLARE_PAGES_PROJECT`: the project name from step 1.
4. **Protect `main`.** *Settings → Rules → Rulesets → New branch ruleset* targeting `main`: require a pull request before merging; require the status checks `Test (Python 3.12)`, `Test (Python 3.13)` and `Build the site`; block force pushes; restrict deletions.
5. **Add the second admin** (PRD R2) to the GitHub organisation and the Cloudflare account, with two-factor authentication.

Secrets are only read by the deploy step, are passed to Wrangler through its inputs and are never printed. The built site contains no secrets.

## Scheduled jobs

Scheduled workflows (the Innovation Graph check and the Hub sync) only run when the repository variable `SCHEDULES_ENABLED` is `true`, so nothing runs on a timer until you turn it on. Each can also be started by hand from the *Actions* tab.

## Launch

At launch, move the `djazair.dev` custom domain from the holding-page project to the site project (*Custom domains* tab), then check that `https://djazair.dev/` redirects to a language and that `https://djazair.dev/en/` loads.
