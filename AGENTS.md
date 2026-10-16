# Agent instructions

## Project

ShopKart API is a FastAPI application using SQLAlchemy and Pydantic. API routes are in `app/api/v1/endpoints/`, schemas in `app/schemas/`, models in `app/models/`, and shared business logic in `app/services/`.

## Working guidelines

- Follow the existing structure and conventions; keep changes focused on the requested behavior.
- Keep request and response validation in Pydantic schemas and persistence definitions in SQLAlchemy models.
- Preserve compatibility with the supported SQLite, PostgreSQL, and MySQL database URLs when changing persistence code.
- Do not commit secrets, local database files, or generated artifacts.
- Update the relevant documentation when an API contract or setup behavior changes.
- Follow the TDD(Test-driven development) approach for making any changes.
- Keep the README.md file updated.

## Running the application

Install dependencies from `requirements.txt`, then run the API with:

```bash
uvicorn app.main:app --reload
```

The default database URL is `sqlite:///./auth.db`; `DATABASE_URL` can select another supported database.
