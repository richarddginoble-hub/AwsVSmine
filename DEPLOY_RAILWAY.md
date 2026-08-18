GitHub Actions-only deployment notes
------------------------------------

This repository is configured to run scheduled tasks entirely within GitHub Actions. The previous workflow that POSTed to an external /run endpoint has been disabled and replaced by a GitHub-only scheduled task.

What’s in this repo now
- app.py — contains perform_task() used by run_task.py
- run_task.py — script executed by GitHub Actions to run perform_task and write run-output/last_run.txt
- requirements.txt — Python dependencies (Flask, gunicorn)
- .github/workflows/scheduled-task.yml — scheduled workflow that runs run_task.py hourly and uploads run-output as an artifact
- .github/workflows/scheduled-run.yml — DISABLED: previously posted to /run on an external host (kept only for history; it no longer runs on a cron schedule)

Why this is the best fit
- No external hosting required: scheduled work runs entirely inside GitHub Actions.
- Simpler maintenance: you don’t need to deploy or manage Railway/Render/VMs.
- Artifacts: results are stored as workflow artifacts; for long-term durability, integrate external storage (S3, DB, etc.).

Secrets and cleanup
- RUN_URL is no longer used by the active workflows. If you previously added RUN_URL to repository secrets, you can safely remove it.
- RUN_KEY is optional for GitHub-only runs; remove it if you don’t use it elsewhere. If you keep it, nothing will break.

How to remove unused secrets
1) Go to your repository → Settings → Secrets and variables → Actions.
2) Remove RUN_URL and RUN_KEY if you no longer need them.

Re-enabling a hosted endpoint later
- If you later decide to host the app (Railway, Vercel, Render), restore or re-create the scheduled-run.yml workflow to POST to RUN_URL and set RUN_URL and RUN_KEY in repository secrets and the host environment.

Optional cleanup tasks you might want
- Delete the disabled .github/workflows/scheduled-run.yml file entirely if you don’t want it in history (git rm + commit). Keeping it disabled preserves a record of the previous approach.
- Remove Dockerfile/Procfile if you are certain you will never host the app; otherwise keep them for an easy future migration.
- Add a small README/README_UPGRADE.md explaining how to move from GitHub-only to hosted deployment.

If you want me to:
- Delete the disabled scheduled-run.yml file now, reply “delete disabled workflow”.
- Remove Dockerfile/Procfile from the repo, reply “remove hosting files”.
- Create README update, reply “update README”.

