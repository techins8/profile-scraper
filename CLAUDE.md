# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a **Malt.fr Profile Scraper** application built with FastAPI and Selenium. It scrapes freelancer profiles from Malt.fr and stores them in a PostgreSQL database.

### Core Components

- **FastAPI API** (`app/api.py`): REST API with `/api/profile` endpoint for triggering scrapes
- **Selenium Scraper** (`app/services/malt_scrapper.py`): Uses undetected-chromedriver to bypass bot detection
- **Profile Service** (`app/services/profile_service.py`): Business logic layer that orchestrates scraping and database operations
- **SQLAlchemy Models** (`app/models/malt_profile.py`): Database schema with profile status tracking (TODO, IN_PROGRESS, SCRAPPED, ERROR, etc.)
- **Database** (`app/core/database.py`): PostgreSQL connection management

### Key Architecture Patterns

- **Docker-first workflow**: All commands run inside Docker containers or fallback to local execution if containers aren't running
- **Profile status lifecycle**: Profiles transition through statuses (TODO → IN_PROGRESS → SCRAPPED/ERROR)
- **Workspace pattern**: Each profile gets its own workspace directory at `var/{profile_id}` for screenshots and debugging artifacts
- **Headless Chrome**: Uses Chromium with Xvfb for headless browser execution in Docker

## Development Commands

### Setup
```bash
make sync                    # Full project sync: destroys containers, rebuilds, installs packages, and migrates DB
```

### Docker Operations
```bash
make docker-build            # Build and start containers
make docker-up               # Start existing containers
make docker-down             # Stop containers
make docker-destroy          # Stop containers and remove volumes
make docker-sh               # Shell into app container
make docker-logs c=<service> # View logs (c=app or c=database)
```

### Python/Formatting
```bash
make format                  # Format code with Black
make python-packages         # Install/update Python packages
```

### Database & Migrations
```bash
make migration msg="description"  # Generate new Alembic migration
make migrate                      # Apply pending migrations
make migration-status             # Check current migration status
make migration-history            # View migration history
make migration-downgrade rev=-1   # Rollback migration (specify rev)
make backup                       # Backup database to var/backup/
make restore                      # Restore from latest backup or file=path
make drop-db                      # Drop and recreate database
```

### Scraping
```bash
make malt script=profile_id  # Run scraper for specific profile (uses app/malt.py)
```

### Testing
```bash
make test-all                # Run all pytest tests
make bruno                   # Run Bruno API tests in tests/bruno/
```

### Git Workflow
```bash
make push                    # Format, run Bruno tests, auto-commit, and force-push current branch
```

## Important Technical Details

### Environment Variables
Configuration is loaded from `.env` via `app/core/config.py`:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`, `HTTP_TOKEN`, `SENTRY_DSN`: API credentials
- `WORKSPACE_BASE_PATH`: Base directory for scraper workspaces (default: "var")

### Docker Execution Pattern
The Makefile uses a smart pattern that checks if Docker containers are running, falls back to local execution if not:
```makefile
DOCKER_EXEC_APP = @if [ "$$($(DOCKER_COMPOSE) ps -q app ...)" = "true" ]; then \
    $(DOCKER_COMPOSE) exec -it app $(1); \
else \
    $(1); \
fi
```

### Chrome Driver Setup
- Uses `undetected-chromedriver` to avoid bot detection
- Runs in headless mode via Xvfb in Docker (`:99` display)
- Chrome profile/cache stored in `/home/chrome/.config/chromium` and `/home/chrome/.cache/chromium`
- Screenshots saved to `var/{profile_id}/full_page.png` for debugging

### Profile Scraping Flow
1. API receives URL at `/api/profile?url=...&force_scrapping=false`
2. `ProfileService.process_profile()` checks if profile exists in DB
3. If exists and `force_scrapping=false`, returns cached data
4. Otherwise, updates status to IN_PROGRESS and launches `MaltScrapper`
5. Scraper takes full page screenshot, extracts data via `ExtractMaltInfo`
6. Data is saved to DB and status updated to SCRAPPED (or ERROR on failure)

### Database Schema Notes
- Primary key is UUID (`gen_random_uuid()`)
- `profile_id` is the unique Malt username (from URL)
- JSON columns store complex data: categories, skills, experience, education, certifications
- `last_scraped_at` tracks when profile was last updated

## Code Style

- Uses **Black** formatter (enforced)
- French comments in Makefile, English in Python code
- No unnecessary comments in Python code
