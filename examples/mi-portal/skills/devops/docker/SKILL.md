# Skill: Docker & Containerization

Use this skill for:

- Dockerfile changes (production, dev, debug, build, sonar variants)
- Docker Compose configuration (`docker-compose.yml`, `docker-compose.dev.yml`, etc.)
- Multi-platform build concerns (linux/amd64, Apple Silicon)
- Container image security (Anchore scanning, base image updates)
- Local development environment setup via Docker

---

## Goals

- Keep Dockerfiles minimal and layered correctly for cache efficiency
- Keep production and development Dockerfiles clearly separated
- Never bake secrets or credentials into images
- Ensure production images pass Anchore security scanning

---

## Dockerfile Variants

| File | Purpose |
|---|---|
| `Dockerfile` | Production image (ASP.NET Core runtime) |
| `Dockerfile.dev` | Development with hot reload |
| `Dockerfile.debug` | Debugging support |
| `DockerfileBuild` | CI/CD build image |
| `DockerfileBuildWithSonar` | Build image with SonarCloud analysis |

Base images:
- API production: `mcr.microsoft.com/dotnet/aspnet:8.0-jammy`
- Acceptance tests: `mcr.microsoft.com/playwright:v1.36.2-jammy`

---

## Dockerfile Rules

1. Production images must not include build tools or dev dependencies
2. Use multi-stage builds to keep production image size minimal
3. Never `COPY` `.env` files or credential files into images
4. Set `USER` to a non-root user in production images
5. Pin base image digests or versions — do not use `latest`
6. Keep layer order to maximize cache efficiency (install deps before copying source)

---

## Docker Compose Rules

1. Secrets and connection strings come from `.env` files or environment — not hardcoded in compose
2. Volume mounts for development must not conflict with production config
3. Health checks should be defined for dependent services
4. `docker-compose.dev.yml` is for local development only — do not use in CI

---

## Security Rules

- Anchore image scanning runs in CI after Docker build (`api-build.yml`)
- Production images must not expose unnecessary ports
- Do not install debugging tools in production images
- Base image updates should be tested against full integration suite before merging

---

## Local Development

- Use `docker-compose.dev.yml` for local development with hot reload
- SpiceAI middleware runs separately on port 50051
- WireMock runs as a standalone container for API mocking
- `.env` file provides local overrides — see `example.env` for structure

---

## Checklist

For Dockerfile or Compose changes, verify:

- no secrets baked into images
- production image is minimal (no dev/debug tools)
- multi-stage build structure is preserved
- Anchore scan passes (run in `api-build.yml`)
- local dev setup still works with updated Compose config
- platform target is explicit (`linux/amd64`) for CI builds

---

## Avoid

- `COPY . .` without a `.dockerignore` that excludes secrets and node_modules
- Committing `.env` files used by Docker Compose
- Using `latest` tag for base images
- Installing unnecessary tools in production images to "just make it work"
