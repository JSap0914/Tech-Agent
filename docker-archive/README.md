# Docker Configuration Archive

These Docker files are archived for future use after ANYON platform integration is complete.

## Archived Files

- `docker-compose.yml.backup` - Full service orchestration (PostgreSQL, Redis, FastAPI, Prometheus, Grafana)
- `Dockerfile.backup` - Tech Spec Agent container definition
- `.dockerignore.backup` - Docker build exclusions

## Why Docker Was Removed

Docker was temporarily removed to simplify local development while completing ANYON platform integration. The application now runs directly on the host machine with locally installed PostgreSQL and Redis services.

## When to Re-enable Docker

Docker should be re-enabled when:
1. All ANYON agents are fully integrated (Plan → Design → Tech Spec → Backlog → Development)
2. Ready to deploy to production environment
3. Need consistent development environments across team members
4. Ready to set up inter-agent networking and service discovery

## Re-enabling Docker

### Step 1: Restore Docker Files
```bash
# Copy files back to project root
cp docker-archive/docker-compose.yml.backup docker-compose.yml
cp docker-archive/Dockerfile.backup Dockerfile
cp docker-archive/.dockerignore.backup .dockerignore
```

### Step 2: Update Environment Configuration
Edit `.env` file and change localhost connections back to container names:

```bash
# Change FROM:
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/anyon_db
REDIS_URL=redis://localhost:6379/0

# Change TO:
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/anyon_db
REDIS_URL=redis://redis:6379/0
```

### Step 3: Add ANYON Platform Services (if needed)
Update `docker-compose.yml` to include:
- Other ANYON agents (if running as containers)
- Shared networking for inter-agent communication
- Service discovery configuration
- Load balancers/API gateways

### Step 4: Start Docker Services
```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f tech-spec-agent
```

### Step 5: Verify Functionality
```bash
# Health check
curl http://localhost:8000/health

# Run tests
docker-compose exec tech-spec-agent pytest tests/integration/test_architecture_generation.py -v
```

## Docker Service Configuration (Reference)

The original `docker-compose.yml` included:

- **PostgreSQL 15** (postgres:15-alpine) - Port 5432
- **Redis 7** (redis:7-alpine) - Port 6379
- **Tech Spec Agent API** (FastAPI/Python) - Port 8000
- **Prometheus** (monitoring) - Port 9090
- **Grafana** (dashboards) - Port 3001
- **PgAdmin** (dev only) - Port 5050

All services had health checks and proper dependency ordering.

## Notes

- Data persistence was handled via Docker volumes (postgres_data, redis_data, etc.)
- Services communicated via a custom bridge network
- The Tech Spec Agent waited for PostgreSQL and Redis to be healthy before starting
- Grafana was preconfigured with Prometheus as data source

## Questions?

See main `README.md` for current local development setup instructions.

---

**Archived**: 2025-01-16
**Reason**: Temporary removal for simplified local development during ANYON integration
**Status**: Ready to restore when needed
