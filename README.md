# Experiment Tracker

A full-stack experiment management platform for tracking machine learning experiments, models, runs, and associated assets. Built with Django REST Framework on the backend and React (Vite + TypeScript) on the frontend.

---

## Overview

This project is currently intended for local development and internal/self-hosted usage. Authentication and production hardening are not yet implemented.

Experiment Tracker provides a structured way to manage the lifecycle of ML experiments — from defining models and setups to logging run metrics, outputs, and observability data. It's designed for local or team-hosted deployments where you want full ownership of your experiment metadata.

**Core concepts:**

- **Models** — versioned ML models with optional parent lineage
- **Experiments** — typed, versioned experiments tied to a model
- **Runs** — individual execution instances of an experiment on a specific setup
- **Setups** — reusable execution environment configurations
- **Platforms** — hardware/software platforms linked to setups
- **Materials** — versioned assets (datasets, scripts, configs) used by models and experiments
- **Parameters** — flexible key-value metadata attachable to any entity
- **Tags** — cross-entity labels for filtering and organization
- **Run Observability** — per-run logs, metrics, and output files

---

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python 3, Django 4.2, Django REST Framework |
| Database  | PostgreSQL                          |
| Frontend  | React 18, TypeScript, Vite          |
| Styling   | CSS Modules                         |
| API comms | Fetch API with a thin `apiFetch` wrapper |

---

## Project Structure

```text
experiment-tracker/
├── experiment_tracker/          # Django backend
│   ├── experiment_tracker/      # Project settings, urls, wsgi/asgi
│   └── expt_webapp/             # Main Django app
│       ├── models.py            # All database models
│       ├── views.py             # ViewSets, serializers, API endpoints
│       ├── urls.py              # URL routing
│       ├── admin.py             # Django admin registrations
│       ├── migrations/          # Database migrations
│       └── templates/           # Django HTML templates (legacy UI)
│
├── experiment-tracker-ui/       # React frontend
│   ├── src/
│   │   ├── App.tsx              # Root component & routing
│   │   ├── api/client.js        # Shared API fetch utility
│   │   └── assets/              # Static assets
│   ├── public/                  # Public assets (favicon, icons)
│   └── vite.config.ts           # Vite build configuration
│
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

---

### Backend Setup

```bash
cd experiment_tracker

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install django djangorestframework django-cors-headers psycopg2-binary python-dotenv

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and a new secret key
```

Generate a new Django secret key:

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

```bash
# Apply migrations
python manage.py migrate

# Create an admin user (optional)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

The backend will be available at `http://localhost:8000`.

---

### Frontend Setup

```bash
cd experiment-tracker-ui

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit VITE_API_BASE_URL if your backend runs on a different port

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## API Overview

The REST API is served at `http://localhost:8000/api/` and follows standard ViewSet conventions. Key endpoints:

| Resource          | Endpoint prefix           |
|-------------------|---------------------------|
| Models            | `/api/models/`            |
| Experiments       | `/api/experiments/`       |
| Runs              | `/api/runs/`              |
| Setups            | `/api/setups/`            |
| Platforms         | `/api/platforms/`         |
| Materials         | `/api/materials/`         |
| Material Types    | `/api/material-types/`    |
| Parameters        | `/api/parameters/`        |
| Tags              | `/api/tags/`              |
| Run Logs          | `/api/run-logs/`          |
| Run Metrics       | `/api/run-metrics/`       |
| Run Outputs       | `/api/run-outputs/`       |
| Dashboard         | `/api/dashboard/`         |
| Search            | `/api/search/`            |
| Activity Feed     | `/api/activity/`          |
| Model Comparison  | `/api/compare/models/`    |
| Version Tracking  | `/api/versions/`          |

Notable custom actions include `GET /api/models/{id}/lineage/`, `GET /api/runs/{id}/timeline/`, `POST /api/runs/compare_metrics/`, and `POST /api/parameters/bulk_update/`.

A browsable API is available in development at `http://localhost:8000/api/`.

---

## Environment Variables

### Backend (`experiment_tracker/.env`)

| Variable            | Description                          |
|---------------------|--------------------------------------|
| `DJANGO_SECRET_KEY` | Django secret key (keep private)     |
| `DB_NAME`           | PostgreSQL database name             |
| `DB_USER`           | PostgreSQL username                  |
| `DB_PASSWORD`       | PostgreSQL password                  |
| `DB_HOST`           | Database host (e.g. `localhost`)     |
| `DB_PORT`           | Database port (default: `5432`)      |
| `DB_TEST_NAME`      | Test database name (optional)        |

### Frontend (`experiment-tracker-ui/.env`)

| Variable             | Description                        |
|----------------------|------------------------------------|
| `VITE_API_BASE_URL`  | Base URL of the Django API server  |

---

## Project Status

Active development — APIs, database schema, and frontend functionality may change over time.

---

## Notes

- WARNING: API endpoints are currently unauthenticated and should not be exposed publicly. This project is configured for **local development** and internal/self-hosted usage. Before any public or team deployment, you should add proper authentication (e.g. Django token auth or session auth), set `DEBUG = False`, and configure appropriate `ALLOWED_HOSTS`.
- Media files (run output uploads) are stored under `experiment_tracker/media/` which is excluded from version control.
- Database migrations are included and should be applied fresh on a new PostgreSQL instance.

---

## License

No license has been added to this project yet.

All rights are reserved by the author unless otherwise stated.