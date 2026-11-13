# Trademark conflict deployment and analysis notes

## Local development

Copy `.env.example` to `.env` to customize local settings. The backend and MCP
server load this file automatically; values already set in the process
environment take precedence. The local `.env` is ignored by Git and
contains only local development defaults. Do not reuse it in production.

Start the backend from this directory on port `8081` so the Vite proxy can
reach it:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8081
```

In development, analysis runs as an API background task if Redis is not
available. Production still requires Redis and a running analysis worker.

Start the frontend from `trademark-conflict-frontend` with `npm run dev`; Vite
serves it on `http://localhost:5189` and proxies API, evidence, and health
requests to `http://127.0.0.1:8081`. Set `VITE_API_PROXY_TARGET` when the
backend uses a different local address or port.

The comparison form accepts PDF and XLSX documents (including `.xlxs` as a
filename alias) or standalone SVG, JPG, JPEG, PNG, WEBP, BMP, TIFF, and GIF
images on either side. Image uploads are compared visually; PDF/XLSX document
comparisons continue to use the document text and logo extraction pipeline.

## Production configuration

Copy/configure `POSTGRES_PASSWORD`, `OIDC_ISSUER`, `OIDC_AUDIENCE`,
`OIDC_JWKS_URL`, `OIDC_CLIENT_ID`, and a randomly generated
`EVIDENCE_URL_SIGNING_KEY` in the Compose environment. Do not commit these
values. The backend rejects production startup when the OIDC or evidence
signing settings are missing.

The Vite proxy is for local development only. When building the frontend
container, set `VITE_API_BASE_URL` to the public backend origin, or configure
the frontend host to proxy `/api`, `/evidence`, and `/health` to the backend.
For a separate frontend and backend origin, set `CORS_ALLOWED_ORIGINS` to the
frontend origin.

The identity provider's SPA client must allow this redirect URI:

```text
https://<application-host>/auth/callback
```

The API access token must have the configured audience and include a stable
tenant claim (`tenant_id` by default) plus a roles claim (`roles` by default).
Set `OIDC_TENANT_CLAIM` and `OIDC_ROLES_CLAIM` if the provider uses different
claim names. Supported application roles are `admin`, `analyst`, and
`reviewer`; admins are tenant-scoped, not global. The frontend uses an
authorization-code flow and keeps OIDC state in session storage.

`DATABASE_URL` is supported for local development. Compose supplies
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; SQLAlchemy builds
the PostgreSQL URL safely, including passwords with URL-reserved characters.
Alembic migrations run at backend startup. Redis-backed work is processed by
the `analysis-worker` service. Do not scale the API worker independently from
the shared upload/evidence volumes unless those files are moved to shared
object storage.
Jobs found in a pre-tenant database are assigned to the isolated
`legacy-unassigned` tenant rather than exposed to newly authenticated tenants.
They can be reviewed only after an operator deliberately migrates their
ownership; jobs without an explicit retention date are still cleaned up based
on their creation date and the configured retention period.

Daily PostgreSQL dumps are stored in the Docker `backup_data` volume and
rotated after 30 days. This volume is on the same host as the database and is
not an off-site disaster-recovery copy; copy backups to a separately managed
encrypted destination and test restores regularly.

Uploaded files and generated artifacts are scheduled for deletion after
`JOB_RETENTION_DAYS` (90 by default). Review/audit records remain in PostgreSQL
after file cleanup. Configure operational log shipping for the JSON API logs,
worker logs, and backup service output.

## Ownkube variables

Create separate Ownkube services from `trademark-conflict-backend/Dockerfile`
and `trademark-conflict-frontend/Dockerfile`. The backend listens on port
`8081`; the frontend listens on port `80`.

Set these backend runtime variables (use your own service URLs and secrets):

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://<user>:<password>@<postgres-host>:5432/<database>
REDIS_URL=redis://<redis-host>:6379/0
OIDC_ISSUER=https://<identity-provider>/
OIDC_AUDIENCE=<api-audience>
OIDC_JWKS_URL=https://<identity-provider>/.well-known/jwks.json
EVIDENCE_URL_SIGNING_KEY=<unique-random-secret>
CORS_ALLOWED_ORIGINS=https://<frontend-domain>
OCR_ENABLED=true
OCR_LANGUAGES=eng+mya
```

`DATABASE_URL` can instead be supplied as `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD`. `CORS_ALLOWED_ORIGINS` must contain the public
frontend origin, with no trailing slash. The OIDC provider must issue API
tokens with the configured audience and stable `tenant_id` and `roles` claims.
The frontend's OIDC client must allow
`https://<frontend-domain>/auth/callback`.

Production analysis also needs a worker service using the backend image and
the same database, Redis, environment variables, and persistent upload/evidence
storage. Set its Ownkube start command to:

```sh
rq worker --url "$REDIS_URL" trademark-analysis
```

Set these frontend **build-time** variables on the frontend service:

```text
VITE_API_BASE_URL=https://<backend-domain>
VITE_OIDC_AUTHORITY=https://<identity-provider>/
VITE_OIDC_CLIENT_ID=<spa-client-id>
VITE_OIDC_SCOPE=openid profile email
```

If the frontend domain proxies `/api`, `/evidence`, and `/health` to the backend,
`VITE_API_BASE_URL` can be empty instead. `VITE_API_PROXY_TARGET` is for local
Vite development only and is not used by the production NGINX container.

If deploying the MCP server separately, also set its runtime `MCP_API_KEY`
(at least 32 characters), `BACKEND_BASE_URL=https://<backend-domain>`,
`EVIDENCE_PUBLIC_BASE_URL=https://<backend-domain>/evidence`, and
`MCP_ALLOW_LOCAL_PATHS=false`. Configure that service's start command to run
`python -m apexive_mcp.server`; it listens on `MCP_PORT` (default `8100`).

## Jurisdiction and source metadata

The analysis form records the jurisdiction code, Nice classes, and goods/
services descriptions for each uploaded document. The goods/services overlap
score is an advisory comparison. Different jurisdictions, missing class data,
and absent scope descriptions produce `needs_review`; they are not silently
treated as a legal conflict or a no-conflict. The score does not decide
likelihood of confusion and is not legal advice.

Registry source name, URL, retrieval time, and optional source record ID can be
attached to a job and are included in the generated report. The application
does not currently download or synchronize records from live national,
EUIPO, or WIPO trademark registries. Only cite a registry source when the
uploaded records were actually obtained from that source.

## Myanmar/English OCR and evaluation

Compose installs Tesseract with its English and Myanmar trained data. OCR is
enabled for the API and analysis worker by default in Compose through
`OCR_ENABLED=true`; `OCR_LANGUAGES` defaults to `eng+mya`. Override either
setting deliberately if deploying other languages. In local development,
install the Tesseract executable and the selected language data separately;
installing the Python `pytesseract` wrapper alone is not enough. When OCR is
enabled, blank mark text is read from extracted trademark images and supplied
to the existing exact-text check. Tesseract errors fail visibly rather than
being treated as “no text”.

Curated transliteration is currently an **evaluation-only** comparison path.
No automatic Myanmar romanizer is enabled: transliteration conventions vary,
and treating a guessed spelling as exact could turn into a false conflict.
The JSON dataset stores OCR text, optional human-supplied transliterations,
and an adjudicated `expected_conflict` boolean per case. Replace/add examples
only with reviewer-verified labels before using its metrics to assess real
performance.

Run the regression evaluator from `backend`:

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.ocr_evaluation
```

It reports true/false positives and negatives, accuracy, precision, recall,
and F1 for OCR text alone and OCR text plus curated transliteration. The
checked-in examples are synthetic fixtures for regression coverage, not a
representative accuracy estimate and not evidence of real-world false-positive
or false-negative rates. No live OCR was exercised in this development
environment because the Tesseract executable/language data are not installed.

## Validation

Run the backend unit suite from `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run frontend checks from `frontend`:

```powershell
npm.cmd run build
npm.cmd run lint
```
