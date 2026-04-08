# StockPilot Deployment Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Vercel Deployment](#vercel-deployment)
- [Environment Variable Configuration](#environment-variable-configuration)
- [vercel.json Explanation](#verceljson-explanation)
- [api.py Entry Point Details](#apipy-entry-point-details)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Production Recommendations](#production-recommendations)

---

## Prerequisites

Before deploying StockPilot, ensure you have the following:

- **Python 3.12+** installed locally
- **Node.js 18+** (required for the Vercel CLI)
- **Vercel account** — sign up at [vercel.com](https://vercel.com)
- **Vercel CLI** installed globally:
  ```bash
  npm install -g vercel
  ```
- **Git** — the project should be in a Git repository (GitHub, GitLab, or Bitbucket)

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-local-secret-key-change-in-production
DATABASE_URL=sqlite+aiosqlite:///./stockpilot.db
ENVIRONMENT=development
DEBUG=true
```

### 5. Run the Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`.

> **Tip:** The `--reload` flag enables hot-reloading — the server restarts automatically when you modify source files.

### 6. Run Tests

```bash
pytest -v
```

For async test support:

```bash
pytest -v --asyncio-mode=auto
```

---

## Vercel Deployment

### Option A: Deploy via Vercel Dashboard (Recommended)

1. **Push your code** to a GitHub, GitLab, or Bitbucket repository.

2. **Log in** to [vercel.com](https://vercel.com) and click **"Add New Project"**.

3. **Import** your repository from the Git provider.

4. **Configure the project:**
   - **Framework Preset:** Select `Other`
   - **Root Directory:** Leave as `.` (project root)
   - **Build Command:** Leave empty (no build step needed)
   - **Output Directory:** Leave empty

5. **Set environment variables** (see [Environment Variable Configuration](#environment-variable-configuration) below).

6. Click **"Deploy"** and wait for the deployment to complete.

### Option B: Deploy via Vercel CLI

1. **Log in** to Vercel from the terminal:
   ```bash
   vercel login
   ```

2. **Deploy** from the project root:
   ```bash
   vercel
   ```
   Follow the prompts to link the project to your Vercel account.

3. **Deploy to production:**
   ```bash
   vercel --prod
   ```

### Subsequent Deployments

Once connected, every push to your main branch triggers an automatic production deployment. Pull requests generate preview deployments with unique URLs.

---

## Environment Variable Configuration

Configure the following environment variables in the **Vercel Dashboard** under **Settings → Environment Variables**:

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | Secret key for JWT signing and session security. Must be a strong, random string in production. | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5` |
| `DATABASE_URL` | **Yes** | Database connection string. Use an external database for production (see [Production Recommendations](#production-recommendations)). | `postgresql+asyncpg://user:pass@host:5432/stockpilot` |
| `ENVIRONMENT` | No | Deployment environment identifier. | `production` |
| `DEBUG` | No | Enable debug mode. **Must be `false` in production.** | `false` |

### Setting Variables via Vercel CLI

```bash
vercel env add SECRET_KEY production
vercel env add DATABASE_URL production
vercel env add ENVIRONMENT production
vercel env add DEBUG production
```

You will be prompted to enter the value for each variable.

### Setting Variables via Vercel Dashboard

1. Navigate to your project in the Vercel Dashboard.
2. Go to **Settings** → **Environment Variables**.
3. Add each variable with the appropriate value.
4. Select the environments where the variable should be available: **Production**, **Preview**, and/or **Development**.
5. Click **Save**.

> **Security Note:** Never commit your `.env` file or secrets to version control. The `.gitignore` file should include `.env`.

---

## vercel.json Explanation

The `vercel.json` file at the project root configures how Vercel builds and routes your application:

```json
{
  "builds": [
    {
      "src": "api.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/api.py"
    }
  ]
}
```

### Breakdown

- **`builds`**: Defines the build configuration.
  - `"src": "api.py"` — The entry point file for the Python serverless function.
  - `"use": "@vercel/python"` — Tells Vercel to use the Python runtime. Vercel automatically installs dependencies from `requirements.txt`.

- **`routes`**: Defines URL routing rules (evaluated in order).
  - **Static files route** (`/static/(.*)`) — Requests to `/static/*` are served directly from the `static/` directory as static assets. This avoids routing static file requests through the Python function.
  - **Catch-all route** (`/(.*)`) — All other requests are forwarded to `api.py`, which exposes the FastAPI application.

> **Important:** Route order matters. The static files route must come before the catch-all route, otherwise static assets would be handled by the Python function unnecessarily.

---

## api.py Entry Point Details

Vercel's Python runtime expects a specific entry point. The `api.py` file in the project root serves as the adapter between Vercel's serverless infrastructure and the FastAPI application:

```python
from main import app
```

### How It Works

1. **Vercel discovers `api.py`** based on the `builds` configuration in `vercel.json`.
2. **The `@vercel/python` runtime** looks for an ASGI/WSGI application object named `app` in the specified file.
3. **`api.py` imports `app`** from `main.py`, which is the fully configured FastAPI application instance with all routes, middleware, and event handlers registered.
4. **Vercel wraps the ASGI app** in a serverless function handler that converts HTTP events to ASGI scope and back.

### Key Points

- The file **must** expose a variable named `app` that is an ASGI-compatible application.
- All application setup (route registration, middleware, startup events) happens in `main.py` — `api.py` is purely a re-export.
- Do **not** add additional logic to `api.py` — keep it as a thin entry point.
- If you rename `main.py` or the `app` variable, update `api.py` accordingly.

---

## Troubleshooting Common Issues

### 404 Errors on All Routes

**Symptom:** Every route returns a 404 Not Found response.

**Causes & Fixes:**
- **Missing or misconfigured `vercel.json`:** Ensure the catch-all route `"src": "/(.*)"` points to `"dest": "/api.py"`.
- **`api.py` not importing `app` correctly:** Verify that `api.py` contains `from main import app` and that `main.py` exists at the project root.
- **Route prefix mismatch:** If your FastAPI routes use a prefix (e.g., `/api/v1`), ensure you're requesting the correct URL path.

### Static Files Not Loading (CSS, JS, Images)

**Symptom:** The application loads but styles are missing, scripts fail, or images don't appear.

**Causes & Fixes:**
- **Missing static route in `vercel.json`:** Ensure the `/static/(.*)` route is defined **before** the catch-all route.
- **Incorrect static file paths in templates:** Verify that templates reference static files with the correct path (e.g., `/static/css/style.css`).
- **Static directory not included in deployment:** Ensure the `static/` directory is not listed in `.vercelignore`.

### Cold Starts / Slow Initial Response

**Symptom:** The first request after a period of inactivity takes several seconds.

**Explanation:** Vercel serverless functions experience cold starts when no warm instance is available. The Python runtime must initialize, import dependencies, and set up the application on each cold start.

**Mitigations:**
- **Minimize dependencies:** Remove unused packages from `requirements.txt` to reduce import time.
- **Lazy imports:** For heavy libraries, consider importing them inside the functions that use them rather than at module level.
- **Vercel Pro/Enterprise:** Upgrade to access features like increased function duration limits and more concurrent executions.
- **Keep-alive pings:** Use an external monitoring service (e.g., UptimeRobot) to ping your application periodically, keeping instances warm.

### Database Persistence Caveats

**Symptom:** Data is lost between requests or after redeployment.

**Explanation:** Vercel serverless functions run in ephemeral, read-only file systems. **SQLite databases stored on the local filesystem will not persist** between function invocations. Each invocation may run on a different instance with a fresh filesystem.

**Fixes:**
- **Use an external database** for production deployments (see [Production Recommendations](#production-recommendations)).
- SQLite is suitable **only** for local development.
- If you see `sqlite3.OperationalError: attempt to write a readonly database`, this confirms the filesystem is read-only in the Vercel environment.

### Import Errors / Module Not Found

**Symptom:** Deployment fails with `ModuleNotFoundError`.

**Causes & Fixes:**
- **Missing dependency in `requirements.txt`:** Ensure all third-party packages are listed. Run `pip freeze > requirements.txt` or manually verify.
- **Incorrect Python version:** Vercel uses Python 3.12 by default. Ensure your code is compatible. You can specify the version in `vercel.json`:
  ```json
  {
    "functions": {
      "api.py": {
        "runtime": "python3.12"
      }
    }
  }
  ```

### Template Rendering Errors

**Symptom:** `500 Internal Server Error` when accessing pages that render Jinja2 templates.

**Causes & Fixes:**
- **Templates directory not found:** Ensure the `templates/` directory is at the project root and is included in the deployment.
- **Incorrect `TemplateResponse` usage:** With Starlette 1.0+ / FastAPI 0.135+, use the new API:
  ```python
  templates.TemplateResponse(request, "template.html", context={"key": value})
  ```
  The old style `templates.TemplateResponse("name.html", {"request": request})` causes `TypeError: unhashable type: 'dict'`.

---

## Production Recommendations

### Use an External Database

For production deployments on Vercel, you **must** use an external database service. Recommended options:

| Provider | Database | Connection String Format |
|---|---|---|
| **Neon** | PostgreSQL (serverless) | `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require` |
| **Supabase** | PostgreSQL | `postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres` |
| **PlanetScale** | MySQL | `mysql+aiomysql://user:pass@host/dbname?ssl=true` |
| **Railway** | PostgreSQL | `postgresql+asyncpg://postgres:pass@host:port/railway` |
| **AWS RDS** | PostgreSQL/MySQL | Standard connection string with asyncpg/aiomysql driver |

> **Driver Note:** Ensure you install the appropriate async database driver (`asyncpg` for PostgreSQL, `aiomysql` for MySQL) and include it in `requirements.txt`.

### Generate a Strong SECRET_KEY

Never use a weak or default secret key in production. Generate a cryptographically secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This produces a 64-character hexadecimal string. Set this as your `SECRET_KEY` environment variable in Vercel.

### Security Checklist

- [ ] `SECRET_KEY` is a strong, randomly generated value (not the default)
- [ ] `DEBUG` is set to `false` in production
- [ ] `DATABASE_URL` points to an external, persistent database
- [ ] CORS origins are explicitly configured (not `["*"]`)
- [ ] HTTPS is enforced (Vercel handles this automatically)
- [ ] `.env` file is in `.gitignore`
- [ ] Sensitive data is stored only in Vercel environment variables
- [ ] Database credentials use least-privilege access

### Performance Tips

- **Connection pooling:** Use connection pooling for your database (e.g., PgBouncer, Neon's built-in pooler) to handle concurrent serverless connections efficiently.
- **Response caching:** Add `Cache-Control` headers for static or infrequently changing responses.
- **Function size:** Keep the deployment bundle small. Use `.vercelignore` to exclude test files, documentation, and development artifacts:
  ```
  __pycache__
  *.pyc
  .pytest_cache
  tests/
  .env
  .git
  venv/
  *.md
  ```

### Monitoring

- Use **Vercel Analytics** (available on Pro plans) for performance monitoring.
- Integrate **Sentry** or a similar error tracking service for production error visibility.
- Set up **health check endpoints** (e.g., `GET /health`) and monitor them with an uptime service.

---

## Quick Reference

| Task | Command |
|---|---|
| Local dev server | `uvicorn main:app --reload --port 8000` |
| Run tests | `pytest -v` |
| Deploy preview | `vercel` |
| Deploy production | `vercel --prod` |
| View logs | `vercel logs <deployment-url>` |
| List env vars | `vercel env ls` |
| Pull env vars locally | `vercel env pull .env.local` |