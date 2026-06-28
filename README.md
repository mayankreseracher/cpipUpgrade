# cpipUpgrade Go Service

Cloud-Powered Package Virtualization for Android Termux - Go Backend Service

## Overview

This is the Go service component of cpipUpgrade, providing:
- HTTP API on port 5081
- Health checks and metrics
- OpenAPI specification
- Flexible logging (zap/zerolog)
- Prometheus metrics integration
- Optional vulnerability scanning via govulncheck

## Requirements

- Go 1.22 or later

## Building

```bash
go build -o server ./cmd/server
```

## Running

```bash
# With default zap logger
./server

# With zerolog
LOGGER=zerolog ./server

# With autocheck enabled
AUTOCHECK=true ./server
```

## Endpoints

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /openapi.yaml` - OpenAPI specification
- `GET /items` - Items list

## Development

### Run tests
```bash
go test -v ./...
```

### Run linter
```bash
golangci-lint run
```

### Check for vulnerabilities
```bash
govulncheck ./...
```

## Docker

```bash
docker build -t cpip-upgrade:latest .
docker run -p 5081:5081 cpip-upgrade:latest
```

## Environment Variables

- `LOGGER` - Logger backend: `zap` (default) or `zerolog`
- `AUTOCHECK` - Enable automatic vulnerability checking: `true` or `false` (default: false)
