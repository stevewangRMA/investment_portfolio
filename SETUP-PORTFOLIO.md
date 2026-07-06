# Portfolio Auto-Update — Setup Guide

Your site now has a Portfolio section that reads `portfolio.json`. Right now it shows **sample data** (yellow badge). Follow these steps once and it will refresh with your real IBKR account every day, automatically.

## How it works

```
IBKR Flex Web Service  →  GitHub Action (daily 6:30am ET)  →  portfolio.json  →  GitHub Pages site
```

## Step 1 — Create a Flex Query in IBKR (~5 min)

1. Log in to [IBKR Client Portal](https://www.interactivebrokers.com/portal) → **Performance & Reports → Flex Queries**.
2. Create a new **Activity Flex Query**, name it `portfolio-site`.
3. Select exactly these two sections (click **Select All** for fields in each):
   - **Net Asset Value (NAV) in Base** (older accounts may show this as "Equity Summary in Base by Report Date")
   - **Open Positions**
4. Delivery configuration: Format **XML**, Period **Last 365 Calendar Days**, Date format **yyyy-MM-dd**.
5. Save, and note the **Query ID** shown in the list.

## Step 2 — Enable Flex Web Service (~2 min)

1. Client Portal → **Performance & Reports → Flex Queries → Flex Web Service Configuration** (on the same page as your queries; on some accounts it's instead under Settings → Account Settings).
2. Check **Flex Web Service Status** to activate → Save.
3. Generate a **token**: set "Should Expire After" to 1 year, leave the IP field blank, click Generate New Token (regenerating later invalidates the old token — set a calendar reminder for renewal).
4. Copy the token somewhere safe. Treat it like a password.

## Step 3 — Put the site on GitHub (~10 min)

1. Create a GitHub account if needed, then a new repository (e.g. `stephen-wang-site`).
2. Upload the **entire contents** of this folder: `index.html`, `portfolio.json`, `decks/`, `scripts/`, and `.github/` (the `.github` folder is hidden — make sure it's included; easiest via `git push` from terminal rather than web upload, since the web uploader can skip hidden folders).
3. Enable the site: repo **Settings → Pages → Source: Deploy from a branch → main / (root)**. Your site will be live at `https://<username>.github.io/<repo>/`.

## Step 4 — Add secrets (~2 min)

Repo **Settings → Secrets and variables → Actions → New repository secret**:

- `IBKR_FLEX_TOKEN` = your token from Step 2
- `IBKR_FLEX_QUERY_ID` = your Query ID from Step 1

## Step 5 — Test

Repo **Actions** tab → **Update portfolio** → **Run workflow**. In ~1 minute it should commit a fresh `portfolio.json`; reload your site and the "Sample data" badge disappears. From then on it runs automatically every day at 6:30am ET.

## Notes

- **Everything is public**: the repo (free GitHub Pages requires a public repo) and `portfolio.json` — including its full git history — are visible to anyone. You chose to show dollar values; to switch to percentages-only later, edit one line in `index.html`: `const SHOW_DOLLARS = false;`
- IBKR Flex data is end-of-day, so the site always shows the previous close.
- If the Action fails, the most common causes: token expired, wrong Query ID, or missing sections in the Flex Query.
