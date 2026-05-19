# Environment Setup

## Goals
- Provide a simple, consistent environment file structure.
- Separate local developer setup from production configuration.
- Avoid committing secrets to the repository.

## Target Environment Structure
Frontend/
- .env.example
- .env.local
- .env.production.example

Backend/
- .env.example
- .env.local
- .env.production.example

## Frontend
- Copy Frontend/.env.example to Frontend/.env.local and fill in values.
- For production, use Frontend/.env.production.example as a template for Frontend/.env.production (not committed).

## Backend
- Copy Backend/.env.example to Backend/.env.local and fill in values.
- For production, use Backend/.env.production.example as a template for Backend/.env.production (not committed).

## Docker Compose Notes
- docker-compose.dev.yml uses Backend/.env.local and Frontend/.env.local.
- docker-compose.prod.yml expects:
  - ./.env.production (shared infrastructure values for postgres)
  - ./Backend/.env.production
  - ./Frontend/.env.production

## Secrets Safety
- Do not commit .env.local or .env.production files.
- Use placeholders in *.example files only.
- Rotate secrets regularly per security/SECURITY_OVERVIEW.md.
