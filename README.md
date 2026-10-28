# E-Learning

A Django-based e-learning platform where students can browse and enrol in courses,
instructors can create and manage their own courses and lessons, and payments are
handled through Stripe Checkout.

Built with **Django 5.2**, **Django REST Framework**, **django-allauth** (Google login),
**Stripe**, and **Tailwind CSS v4** with a glassmorphism design. Deployed on
**Render** with **PostgreSQL** and served by **Gunicorn + WhiteNoise**.

> This repo uses a single branch: **`main`** only. No feature branches.

---

## Features

### For students

- Browse published courses and view course details with lessons.
- Enrol in free courses instantly; paid courses go through Stripe Checkout.
- Student dashboard with enrolled courses and progress-style overview.
- Profile view and edit.

### For instructors

- Instructor dashboard with their own courses, lesson counts and student counts.
- Create, edit and publish courses; add and edit lessons.
- Ownership is enforced: an instructor can only manage their own courses
  (admins/superusers can manage all courses).

### Accounts & roles

- Custom user model (`accounts.User`) with three roles: `student`, `instructor`, `admin`.
- One shared login page. The register page has a Student / Instructor toggle that
  sets the role directly at signup — no document upload on the register page.
- Server-side role allowlist: only `student` and `instructor` can be selected.
  A forged `role=admin` falls back to `student`.
- Email verification with a 6-digit OTP (5-minute expiry, 60-second resend cooldown).
- Google login via django-allauth, with the account chooser forced
  (`prompt: select_account`), so a browser already signed in to Google still shows
  the "Choose an account" page.

### Payments

- Stripe Checkout Sessions. The price is always re-read from the database
  server-side — it is never trusted from the browser.
- The success page verifies the session with the Stripe API and then fulfils
  enrolment. The same fulfilment function is shared with the Stripe webhook,
  so fulfilment is idempotent.
- Cancelled checkouts stay `PENDING` (no payment row is created for a checkout
  that never completed). The webhook only works once `STRIPE_WEBHOOK_SECRET`
  is set in the Render dashboard (see [Environment variables](#environment-variables)).

### API

- JWT authentication (SimpleJWT, access 30 min / refresh 7 days, rotation +
  blacklist) plus the browsable web UI.
- Serializers, generic class-based views and ownership permissions for courses,
  lessons, enrolments and payments (see [API endpoints](#api-endpoints)).

### Design

- Tailwind CSS v4 (standalone CLI, no Node) + glassmorphism cards.
- Design system: forest `#203d32`, moss `#557461`, beige `#f7f3ea`,
  linen `#e8e1d3`, bronze `#b88a54`, Inter font.
- Tailwind source lives in `assets/input.css`; only the compiled
  `static/css/output.css` is collected and served (see
  [Tailwind workflow](#tailwind-workflow)).

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Django 5.2, Python 3 |
| API | Django REST Framework 3.18, SimpleJWT 5.5 |
| Auth | django-allauth 65.19 (Google OAuth) |
| Payments | Stripe 15.6 (Checkout + webhooks) |
| Email | Brevo HTTPS API, with SMTP and console fallbacks |
| Database | PostgreSQL (via `dj-database-url`) |
| Static files | WhiteNoise |
| Server | Gunicorn |
| CSS | Tailwind CSS v4.1.7 (standalone CLI) |
| Deploy | Render (`render.yaml` + `Procfile`) |

---

## Project structure

```text
E_learning/            # Django project settings, root URLs, WSGI/ASGI
accounts/              # Custom User, Profile, OTP verification, roles,
                       # permissions, dashboards, profile, Google adapter
courses/               # Course, Lesson, Enrollment; web + API views,
                       # serializers, permissions, seed_courses command
payments/              # Stripe Checkout, success/cancel, webhook, Payment model
core/                  # Home/about pages, email backends, custom middleware
                       # (maintenance mode + request timing)
assets/
  input.css            # Tailwind v4 source (edit this, never output.css directly)
static/
  css/output.css       # Compiled Tailwind (generated, git-ignored)
  css/style.css        # Legacy styles kept as fallback
  js/auth.js           # Login/register/OTP page behaviour
templates are inside each app, e.g. accounts/templates/accounts/
```

---

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/RomaanAli/Django_learning.git
cd Django_learning

# 2. Virtual environment
python -m venv .venv
# Windows (PowerShell):
#   .venv\Scripts\Activate.ps1
# macOS / Linux:
#   source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment variables (see table below)
#    Create a .env file in the project root and fill in your own values —
#    never commit real secrets. (.env is git-ignored.)

# 5. Database + demo data
python manage.py migrate
python manage.py seed_courses   # safe to re-run: never duplicates existing records

# 6. Compile Tailwind (see workflow below)
./tailwindcss -i assets/input.css -o static/css/output.css --minify

# 7. Run
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and create a superuser with:

```bash
python manage.py createsuperuser
```

Admin is at `/admin/`.

> **Note:** The test suite needs a live PostgreSQL database — the project
> settings are PostgreSQL-only. See [Testing](#testing).

---

## Tailwind workflow

Tailwind v4 is compiled with the standalone CLI (no Node, no Play CDN in
production). **Do not edit `static/css/output.css` by hand** — it is generated
and git-ignored.

```bash
# Download the binary once for your platform from:
# https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.1.7
#   macOS: tailwindcss-macos-arm64 / tailwindcss-macos-x64
#   Linux: tailwindcss-linux-x64
#   Windows: tailwindcss-windows-x64.exe

# Compile (re-run after every change to assets/input.css or template classes):
./tailwindcss -i assets/input.css -o static/css/output.css --minify
```

Why the source is in `assets/` and not `static/css/`: WhiteNoise tried to resolve
the `@import "tailwindcss"` in `static/css/input.css` during `collectstatic` and
broke the build. Moving the source to `assets/input.css` (compiled to
`static/css/output.css` before `collectstatic`) fixed that. On Render, the
`render.yaml` build command does this automatically, in this order:
install deps → download Tailwind binary → compile CSS → `collectstatic`.

If pages look unstyled after a change, recompile and hard-refresh the browser.

---

## Environment variables

Settings load a `.env` file from the project root (via `python-dotenv`) and
also read real environment variables. On Render, the `sync: false` values are
set in the Render dashboard, not in `render.yaml`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes (fail-closed: missing key stops boot) | Django secret key. On Render: `generateValue: true`. |
| `DJANGO_DEBUG` | No (default `False`) | Set `True` only for local development. |
| `DATABASE_URL` | Yes | PostgreSQL connection string. On Render: from the `elearning` database. |
| `DJANGO_ALLOWED_HOSTS` | No | Comma-separated hosts. Default includes `localhost`, `127.0.0.1`, `.onrender.com`. |
| `BREVO_API_KEY` | For real email | Brevo API key (`xkeysib-…`). Without it, OTP mail falls back to SMTP, then console — and `manage.py check` warns `elearning.W001`. |
| `DEFAULT_FROM_EMAIL` | For real email | Must be a Brevo-verified sender, otherwise OTP mail will not deliver. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | Optional | SMTP fallback if Brevo is not configured. |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | For Google login | Google Cloud OAuth credentials. The "Continue with Google" button is only shown when Google is configured. |
| `STRIPE_PUBLISHABLE_KEY` / `STRIPE_SECRET_KEY` | For paid courses | Stripe keys (test keys for development). |
| `STRIPE_WEBHOOK_SECRET` | For webhooks | Stripe webhook signing secret. **Set this in the Render dashboard** — without it the webhook returns "not configured" and enrolment depends only on the success-page redirect. |
| `STRIPE_CURRENCY` | No (default `usd`) | Currency code for Checkout. |
| `MAINTENANCE_MODE` | No | Set to `true` to show maintenance mode (admin, login/logout, static/media, Stripe webhook, Google and auth pages are still reachable). |

**Never commit a `.env` file or a real key.** `.env` is git-ignored.

---

## API endpoints

Base URL: `/api/`. Authenticated requests use `Authorization: Bearer <access-token>`.

| Method & path | Who | Notes |
| --- | --- | --- |
| `POST /api/token/` | Anyone | Obtain JWT access + refresh tokens. |
| `POST /api/token/refresh/` | Anyone | Refresh an access token. |
| `POST /api/token/verify/` | Anyone | Verify a token. |
| `GET /api/me/` | Authenticated | Current user (web-style profile dict). |
| `GET /api/courses/` | Anyone | Published courses, paginated (10 per page), with search/ordering. |
| `POST /api/courses/` | Instructor | Creates a course owned by the caller. |
| `GET /api/courses/<id>/` | Anyone / owner | Drafts only for their owner/admin. |
| `PUT/PATCH /api/courses/<id>/` | Owner | Title, description and price are writable; `id`, `is_published` and `instructor` are read-only. |
| `GET /api/courses/instructor/` | Instructor / admin | Caller's own courses (admins see all). |
| `GET /api/courses/<id>/lessons/` | Enrolled student / owner | 403 for anyone else. |
| `POST /api/courses/<id>/lessons/` | Owner | 403 for other instructors and students. |
| `GET /api/courses/<id>/lessons/<lesson_id>/` | Enrolled student / owner | Same guard as the list. |
| `GET /api/courses/enrollments/` | Authenticated | Caller's own enrolments, newest first. |
| `POST /api/courses/enrollments/` | Student only | Free courses only — paid courses return 400 (use Stripe Checkout). |
| `GET /api/courses/enrollments/<id>/` | Owner of the enrolment | Other users get 404, never details. |
| `GET /api/courses/payments/` , `GET /api/courses/payments/<id>/` | Owner | Read-only; no Stripe IDs are exposed. |

---

## Payments flow (how it works)

1. Student clicks "Buy" on a paid course → `payments/confirm/<course_id>/`.
2. Checkout creates a Stripe Checkout Session. The amount is re-read from the
   `Course` row in the database, never from the request.
3. Stripe redirects back to `payments/success/<course_id>/?session_id=…`.
   The success view verifies the session with the Stripe API, then calls
   `fulfill_checkout_session()` to create the enrolment and mark the
   `Payment` as paid.
4. The webhook at `/webhooks/stripe/` (signature-verified with
   `STRIPE_WEBHOOK_SECRET`) calls the **same** fulfilment function, so a
   payment is fulfilled even if the user closes the tab before the redirect —
   and fulfilling twice is safe.
5. Cancelling at Stripe returns to `payments/cancel/<course_id>/` and no
   enrolment is created.

---

## Testing

```bash
# Requires a PostgreSQL database (set DATABASE_URL + DJANGO_SECRET_KEY first)
python manage.py test
```

The suite covers accounts/roles, OTP, course/lesson ownership, enrolments,
Stripe fulfilment and API permissions. There is currently no CI workflow —
running the suite locally against Postgres before a release is the check.

---

## Deployment (Render)

Deployment is defined in `render.yaml` and happens automatically on every
push to `main`:

- **Build:** `pip install -r requirements.txt` → download Tailwind binary →
  compile `assets/input.css` → `static/css/output.css` → `collectstatic`.
- **Start:** `python manage.py migrate && python manage.py seed_courses &&
  gunicorn E_learning.wsgi --bind 0.0.0.0:$PORT`
- **Database:** Render Postgres service `elearning` (free plan).

After a deploy, check:

1. The build log shows Tailwind compiled **before** `collectstatic`.
2. `manage.py check` warning `W001` appears only if Brevo is misconfigured.
3. Home, course list/detail, login, register (both toggle states), OTP,
   dashboards and payment confirm render without horizontal scroll on mobile.
4. Stripe webhook secret is set in the dashboard (see above).
5. Instructor uploads live on Render's ephemeral filesystem and are not
   served by Django in production (`DEBUG=False`) — persistent object
   storage is still an open decision for instructor documents.

Render's free plan has no shell access without a premium subscription, so
production debugging is done through logs and the admin, not a remote shell.

---

## Security notes

- Role selection is allowlisted server-side (student/instructor only).
- Course/lesson ownership is checked on web and API (`is_managed_by`), for
  both reads of draft/paid content and writes.
- API enrolment rejects paid courses and non-students; web enrolment is POST-only.
- `DEBUG` and `SECRET_KEY` are fail-closed in production settings.
- The diagnostics view (`accounts/google-check/`) is staff-only.
- Known open items (not hidden): OTPs are currently stored in plaintext and
  have no attempt limit; `Payment` rows use CASCADE deletes and `FAILED` /
  `REFUNDED` are not yet written by webhook handlers; profile email changes
  do not yet trigger re-verification. These are tracked for a follow-up change
  with a migration, not silently ignored.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| Pages unstyled | Tailwind not recompiled — run the compile command above and hard-refresh. |
| `elearning.W001` on `manage.py check` | No real mail transport: set `BREVO_API_KEY` + verified `DEFAULT_FROM_EMAIL`. |
| Webhook returns "not configured" | `STRIPE_WEBHOOK_SECRET` is not set in the Render dashboard. |
| `ImproperlyConfigured: DJANGO_SECRET_KEY` | Secret key env var is missing — set it (Render generates it). |
| `DisallowedHost` (400) | Host not in `DJANGO_ALLOWED_HOSTS` — add it, do not use `*` in production. |
| Tests fail to start | No Postgres `DATABASE_URL` — the suite is PostgreSQL-only. |
| Instructor document 404 in production | Expected with `DEBUG=False` — see the media/storage note above. |

---

## Contributing

This is a learning project with a single-branch (`main`) workflow. Keep changes
small, keep the role-toggle and design-system rules above intact, and run
`manage.py check` + the test suite before pushing. If you change a template
class or `assets/input.css`, recompile Tailwind before committing — the
compiled `output.css` itself is never committed.
