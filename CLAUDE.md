# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## TOP RULES
ALWAYS REPLY IN CHINESE
have to use superpower
use TDD to develop(REG)
always give me several resolutions and recommand a plan that has lower tech-debt
dont edit code without acception, just discuss

---

## Project Overview

A campus card (一卡通) simulation system with three independent components:

- **server** — Backend HTTP API + SQLite + admin UI (embedded)
- **issuer** — Card issuance & recharge frontend
- **terminal** — POS-style payment terminal

All components are written in Go, compile to single binaries, and are deployed via Docker Compose.

---

## Architecture

```
issuer (port 3001) ──HTTP──► server (port 8080) ◀──HTTP── terminal (port 3002)
                           │
                        SQLite
```

**Key Design Decisions:**

1. **No `common` package** — Each component implements its own `Card` struct and `HMAC` functions. Code duplication is acceptable; keeping components independent is prioritized.
2. **Card files** — JSON with HMAC-SHA256 signature. Issuer creates them; terminal validates them before charging.
3. **Terminal flow** — Input amount → "Start Charge" → Upload card file → Call server API → Auto-download updated card file
4. **Docker networking** — Bridge network, services communicate via service names (`http://onecard-server:8080`)
5. **Server serves admin UI** — Not a separate binary; Vue/React build is embedded with `go:embed`
6. **Database abstraction** — GORM with `DB_DRIVER`/`DB_DSN` env vars; swap SQLite → PostgreSQL by changing config only
7. **Stateless services** — terminal and issuer can scale horizontally: `docker-compose up -d --scale terminal=10`

---

## Build & Run

### Local Development

```bash
# Set HMAC key (required)
export CARD_HMAC_KEY=your-secret-key

# Run server (port 8080)
cd server && go run main.go

# Run issuer (port 3001)
cd issuer && go run main.go

# Run terminal (port 3002)
cd terminal && go run main.go
```

### Docker Compose

```bash
# First time setup
cp .env.example .env
# Edit .env to set CARD_HMAC_KEY

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Build Binaries

```bash
# Build for current platform
go build -o bin/onecard-server ./server

# Cross-compile for Windows
GOOS=windows GOARCH=amd64 go build -o bin/onecard-server.exe ./server

# Cross-compile for macOS
GOOS=darwin GOARCH=amd64 go build -o bin/onecard-server-mac ./server
```

---

## Environment Variables

| Variable | Used By | Description |
|----------|---------|-------------|
| `CARD_HMAC_KEY` | all | HMAC signing key (must be identical) |
| `SERVER_URL` | issuer, terminal | Backend URL (`http://onecard-server:8080` in Docker) |
| `DB_DRIVER` | server | Database driver (`sqlite` / `postgres`) |
| `DB_DSN` | server | Database connection string |
| `PORT` | all | Service port (8080/3001/3002) |

---

## API Endpoints (Server)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cards` | Create card |
| GET | `/api/cards` | List all cards (admin) |
| GET | `/api/cards/:id` | Get card by ID |
| POST | `/api/cards/:id/consume` | Charge card |
| POST | `/api/cards/:id/recharge` | Recharge card |
| POST | `/api/cards/:id/suspend` | Suspend card |
| POST | `/api/cards/:id/activate` | Activate card |
| GET | `/api/transactions` | List transactions (optional `?card_id=xxx`) |
| GET | `/api/transactions/all` | All transactions (admin) |
| GET | `/api/stats` | Statistics (admin) |
| GET | `/health` | Health check |

---

## Card File Format

```json
{
  "card_id": "2024001",
  "name": "张三",
  "balance": 500.00,
  "status": "active",
  "expires_at": "2027-06-30T23:59:59Z",
  "created_at": "2026-03-31T00:00:00Z",
  "updated_at": "2026-03-31T12:30:00Z",
  "transactions": [],
  "hmac": "sha256_signature_here"
}
```

HMAC is computed over all fields except `hmac` itself, using `HMAC-SHA256(card_hmac_key, json_bytes)`.

---

## Component-Specific Notes

### Server (`server/`)
- Uses GORM AutoMigrate for schema
- Each service has: `api/` (HTTP), `service/` (business logic), `db/` (data), `crypto/` (HMAC)
- Static files in `static/` are embedded via `go:embed`

### Issuer (`issuer/`)
- Creates card files and saves to user-selected directory
- Only two functions: **Create Card** and **Recharge**
- Browser auto-opens on startup

### Terminal (`terminal/`)
- POS-style UI with numeric keypad
- Does NOT calculate amounts — only inputs a single charge value
- Auto-downloads updated card file after successful charge
- Supports both file picker and drag-drop for card upload

---

## Error Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1001 | Card not found |
| 1002 | Insufficient balance |
| 1003 | Card expired |
| 1004 | Card suspended |
| 1005 | HMAC verification failed |
| 5000 | Internal server error |

---

## Documentation

Detailed specs in `docs/specs/`:
- `2026-03-31-design.md` — Overall design
- `2026-03-31-server-implementation.md` — Backend details
- `2026-03-31-issuer-implementation.md` — Issuer details
- `2026-03-31-terminal-implementation.md` — Terminal details
- `2026-03-31-docker-deployment.md` — Docker setup
