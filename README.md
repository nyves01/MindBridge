# MindBridge Rwanda

MindBridge Rwanda is a Django mental-health information and support prototype
for young adults in Rwanda. It provides educational resources, reflection
tools, approved professional profiles, appointment requests, private feedback,
and account-management features.

MindBridge is educational and supportive. It does not diagnose conditions,
prescribe treatment, or replace qualified professionals or emergency services.

## Features

- Account registration, login, logout, password change and password reset
- Required privacy-notice acceptance during registration (not stored)
- Authenticated sessions that expire after 15 minutes without activity
- Platform-user and mental-health-professional roles
- Private professional applications and administrator review
- Public directory listings limited to approved, consenting professionals
- Professional search and filtering
- Appointment requests require login and return to the selected professional
- Public education, wellness, support-guide, and feedback pages
- One existing wellness tip selected per day
- Self-awareness reflection with written guidance and no displayed score
- Appointment requests, responses, cancellations and rescheduling using date and time only
- In-app appointment notifications, shown in the appointments list, and access checks
- Fixed-choice feedback without a free-text field, and account deactivation
- Urgent-support guidance and responsive pages

## AI assistance disclosure

GitHub Copilot was used as an AI coding assistant during development and
contributed code and tests. Its assistance included authentication validation
and redirects, appointment workflow validation and form states, error pages,
Render configuration and demo-account seeding, responsive styling,
documentation, and the logout flow. The project owner is responsible for
reviewing and understanding the final submission.

## Prerequisites

- Git
- Python 3.12 or newer
- Windows 10/11 with PowerShell (commands below use PowerShell)
- A web browser

Local development uses SQLite and does not require a separate database server.
The deployment blueprint provisions PostgreSQL on Render.

## Clone and install

```powershell
git clone https://github.com/nyves01/MindBridge.git
Set-Location MindBridge
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The project dependencies, including Django, are pinned in
[`requirements.txt`](requirements.txt).

## Environment configuration

The project reads environment variables from the process environment; it does
not load a `.env` file automatically. [`.env.example`](.env.example) documents
the variable names and local examples. Local defaults work without copying it.
To set a variable in the current PowerShell session, use
`$env:VARIABLE_NAME = "value"` before running Django.

| Variable | Purpose |
| --- | --- |
| `DJANGO_DEBUG` | `True` for local development; set to `False` in production. |
| `DJANGO_SECRET_KEY` | Required when `DJANGO_DEBUG=False`. Use a private, unique value; Render generates one from `render.yaml`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames, without schemes. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins including `https://` in production. |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS; enabled by the Render blueprint. |
| `DATABASE_URL` | Optional database URL. Local default is the project SQLite database; Render uses its provisioned PostgreSQL database. |
| `DJANGO_EMAIL_BACKEND` | Defaults to Django’s console backend. Set to `django.core.mail.backends.smtp.EmailBackend` to enable SMTP. |
| `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT` | SMTP server and port. |
| `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_USE_SSL` | SMTP transport options; configure according to the provider. Do not enable both. |
| `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD` | SMTP account credentials. Keep these out of source control. |
| `DJANGO_DEFAULT_FROM_EMAIL` | Sender address used for outgoing email. |

For production, set environment variables in the hosting platform. The Render
blueprint sets the expected host and CSRF origin for the configured
`mindbridge-rwanda` service. If Render assigns a different hostname, update
`DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` in the Render
environment to match it.

## Database setup

The local database is `db.sqlite3`, which is ignored by Git. Apply the
committed migrations after installing dependencies:

```powershell
python manage.py migrate
```

Do not run `makemigrations` for normal setup. The Render build command applies
migrations to the provisioned PostgreSQL database.

## Demo accounts

After migrations, create the demo accounts:

```powershell
python manage.py seed_demo
```

The command creates a platform user, an approved professional with a directory
profile, and a Django superuser. It can be run repeatedly without creating
duplicates; existing demo passwords are not changed.

| Role | Username | Password |
| --- | --- | --- |
| Platform user | `demo_user` | `MindBridge-Demo-2026!` |
| Approved professional | `demo_professional` | `MindBridge-Demo-2026!` |
| Administrator | `demo_admin` | `MindBridge-Demo-2026!` |

The administrator signs in at `/admin/`. These are public demo credentials;
never use them for real users or a production administrator account.

## Run locally

```powershell
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). The home page is public;
the dashboard and other account features require login.

## Tests and checks

```powershell
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Deployment on Render

The repository includes a Render Blueprint in [`render.yaml`](render.yaml).
Connect the repository to Render and create a Blueprint from that file. It
defines the web service and PostgreSQL database, runs migrations and collects
static files during the build, seeds the demo accounts, and starts the Django
app with Gunicorn.

The blueprint sets `DJANGO_DEBUG=False`, generates `DJANGO_SECRET_KEY`, and
configures `mindbridge-rwanda-qlzw.onrender.com`, the current public hostname.
If the deployed hostname changes, update the allowed-host and CSRF-origin
variables in the Render dashboard before using the app. No
database migration command needs to be run manually after a successful
Blueprint build. The build runs `python manage.py seed_demo` after migrations;
the command is repeatable and does not overwrite existing demo account
passwords.

### Live URL

The deployed application is available at
<https://mindbridge-rwanda-qlzw.onrender.com>.

## Roles and privacy

- Platform users can use resources, submit reflections and feedback, and
  request appointments.
- Approved professionals can receive and respond to appointment requests.
- Django administrators review professional applications and manage accounts.
- Only approved professionals who consent are shown in the public directory.
- Passwords use Django’s password hashing and validation.
- Appointment records are not available in Django admin; users and their assigned professionals can access appointment details.
- New appointment and feedback submissions do not collect free-text personal or health details.
- Account deactivation disables login; it does not erase historical records.

## Known limitations

- Password reset email uses the console backend by default. Emails will not be
  delivered unless a working SMTP provider and its environment variables are
  configured in the hosting environment.
- Anonymous feedback submissions are allowed and are not linked to an account.
- Earlier appointment and feedback free-text values, if any, remain in their database columns but are no longer collected or shown in the application. A separately reviewed data-retention migration is still needed before the SRS privacy requirement is fully met.
- Privacy-notice acceptance is required at registration but is not retained as
  a separate consent record.
- The daily wellness tip is selected from the six existing suggestions; no
  additional wellness content is implemented.
- Render deployments ensure the demo accounts exist, including a demo
  superuser. The credentials are public and are only suitable for evaluation.
- Rwanda-specific emergency and crisis contact details are withheld until
  verified. The app is not an emergency-response service.
- The self-awareness reflection is educational, not a clinical assessment or
  diagnosis. Its numeric score remains stored with submitted answers but is
  not shown to users.
- Ikinyarwanda translation is not enabled pending translation verification.
- Replace or disable demo credentials before any real production use.
