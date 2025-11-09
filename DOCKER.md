# Docker Deployment Guide for Joplin MCP Server

This guide explains how to deploy the Joplin MCP Server as a Docker container with streamable HTTP transport, designed to work with the MCP Gateway (Caddy reverse proxy) or Traefik.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Environments](#deployment-environments)
- [MCP Gateway Integration](#mcp-gateway-integration)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Overview

The Joplin MCP Server Docker setup provides:

- **Streamable HTTP Transport**: Full HTTP-based MCP communication (not SSE)
- **Production-Ready Container**: Multi-stage build, non-root user, health checks
- **Multi-Environment Support**: Separate configs for local (MacBook) and production (Wyze)
- **Central Configuration**: Uses shared `.env` file at `/opt/docker/mcp-proxy/.env`
- **Reverse Proxy Ready**: Works with Caddy (mcp_gateway) or Traefik (t2_proxy)
- **Health Monitoring**: Built-in health check endpoint at `/health`

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Joplin Desktop** running with Web Clipper enabled
3. **Joplin API Token** (get from: Tools > Options > Web Clipper > Advanced options)
4. **Central `.env` file** at `/opt/docker/mcp-proxy/.env`
5. **MCP Gateway network** (for local) or **Traefik** (for production)

## Quick Start

### Local Development (MacBook)

```bash
# Navigate to the MCPs directory
cd /opt/docker/mcp-proxy/MCPs/joplin-mcp

# Build and run using local configuration
docker compose -f docker-compose.yml -f docker-compose.local.yaml up -d

# Check logs
docker compose logs -f joplin-mcp-server

# Check health
curl http://localhost:8006/health
```

### Production Deployment (Wyze)

```bash
# Navigate to the MCPs directory
cd /opt/docker/mcp-proxy/MCPs/joplin-mcp

# Build and run using production configuration
docker compose -f docker-compose.yml -f docker-compose.wyze.yaml up -d

# Check logs
docker compose logs -f joplin-mcp-server

# Check health (via Traefik)
curl https://mcp.nstam.eu/joplin/health
```

## Configuration

### Central Environment File

The server uses a central `.env` file located at `/opt/docker/mcp-proxy/.env`. Add these variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `JOPLIN_API_TOKEN` | (required) | Your Joplin API token |
| `JOPLIN_BASE_URL` | `http://localhost:41184` | Joplin API base URL |
| `MCP_DEBUG` | `false` | Enable debug mode |

### Server Configuration (docker-compose.yml)

The base configuration sets these defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `streamable-http` | Transport protocol (streamable-http, http, sse, stdio) |
| `MCP_HOST` | `0.0.0.0` | Host to bind to (0.0.0.0 for all interfaces) |
| `MCP_PORT` | `8006` | Port to listen on |
| `MCP_PATH` | `/mcp` | Base path for MCP endpoints |
| `MCP_LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |

### Optional Configuration File

You can mount a configuration file for advanced settings:

```yaml
# Uncomment in docker-compose.yml
volumes:
  - ./joplin-mcp.json:/config/joplin-mcp.json:ro
```

## Deployment Environments

### Three-File Configuration Approach

The deployment uses Docker Compose override files:

1. **docker-compose.yml** - Base configuration (don't use directly)
2. **docker-compose.local.yaml** - Local MacBook development
3. **docker-compose.wyze.yaml** - Production Wyze deployment

### Local (MacBook) - mcp_gateway Network

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yaml up -d
```

Features:
- Exposes port 8006 on host
- Connects to `mcp_gateway` network
- Debug mode enabled
- Accessed via: `https://mcp.orb.local/joplin`

### Production (Wyze) - Traefik Integration

```bash
docker compose -f docker-compose.yml -f docker-compose.wyze.yaml up -d
```

Features:
- No host port binding (internal only)
- Connects to `t2_proxy` network
- Traefik reverse proxy labels
- Authelia authentication
- Accessed via: `https://mcp.nstam.eu/joplin`

## MCP Gateway Integration

### Caddy Gateway (Local/MacBook)

The Caddyfile entry for Joplin MCP:

```caddyfile
# Joplin MCP - Note management and knowledge base
handle_path /joplin* {
    reverse_proxy joplin-mcp-server:8006 {
        header_up Host {upstream_hostport}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Access URL: `https://mcp.orb.local/joplin/mcp`

### Traefik Integration (Production/Wyze)

Traefik labels are automatically configured in `docker-compose.wyze.yaml`:

- **Host**: `mcp.nstam.eu`
- **Path**: `/joplin`
- **Port**: `8006`
- **Middleware**: Authelia authentication + path stripping

Access URL: `https://mcp.nstam.eu/joplin/mcp`

### Testing Connection

```bash
# Local (MacBook)
curl https://mcp.orb.local/joplin/health

# Production (Wyze)
curl -u username:password https://mcp.nstam.eu/joplin/health
```

## Production Deployment

### Security Best Practices

1. **Use Non-Root User**: The container runs as user `mcp` (UID 1001)
2. **Read-Only Config**: Mount config files as read-only (`:ro`)
3. **Network Isolation**: Use Docker networks to isolate services
4. **TLS Termination**: Use Caddy gateway for HTTPS/TLS

### Docker Networks

**Local (MacBook):**
```bash
docker network create mcp_gateway
```

**Production (Wyze):**
```bash
# t2_proxy should already exist from Traefik setup
docker network ls | grep t2_proxy
```

### Connecting to Joplin

**Local (MacBook)** - Add to `/opt/docker/mcp-proxy/.env`:
```bash
JOPLIN_BASE_URL=http://host.docker.internal:41184
JOPLIN_API_TOKEN=your_token_here
```

**Production (Wyze)** - Add to `/opt/docker/mcp-proxy/.env`:
```bash
JOPLIN_BASE_URL=http://your-joplin-host:41184
JOPLIN_API_TOKEN=your_token_here
```

If Joplin is in another Docker container:
```bash
JOPLIN_BASE_URL=http://joplin-container-name:41184
```

### Resource Limits

Add resource limits for production:

```yaml
# docker-compose.yml
services:
  joplin-mcp-server:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          memory: 256M
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs joplin-mcp-server

# Check if port is already in use
sudo lsof -i :8000

# Verify config
docker compose config
```

### Cannot Connect to Joplin

```bash
# Test from inside container
docker exec -it joplin-mcp-server curl http://host.docker.internal:41184/ping

# Check Joplin Web Clipper settings
# Tools > Options > Web Clipper > Enable Web Clipper service
```

### Health Check Failing

```bash
# Check health endpoint directly
docker exec -it joplin-mcp-server curl http://localhost:8000/health

# View health status
docker inspect joplin-mcp-server | grep -A 10 Health
```

### Gateway Integration Issues

```bash
# Verify network connection
docker network inspect mcp_gateway

# Test direct connection
curl http://joplin-mcp-server:8000/health

# Check Caddy logs
docker compose -f /path/to/mcp-gateway/docker-compose.yml logs -f
```

### Debug Mode

Enable debug logging:

```yaml
# docker-compose.yml
environment:
  - MCP_LOG_LEVEL=debug
```

Then restart:

```bash
docker compose restart joplin-mcp-server
docker compose logs -f joplin-mcp-server
```

## Complete Example

### Directory Structure

```
/opt/docker/mcp-proxy/
├── .env                           # Central configuration
└── MCPs/
    └── joplin-mcp/
        ├── docker-compose.yml       # Base config
        ├── docker-compose.local.yaml   # MacBook
        ├── docker-compose.wyze.yaml    # Production
        └── ... (source files)
```

### Central `.env` File

Edit `/opt/docker/mcp-proxy/.env`:

```bash
# Joplin MCP Configuration
JOPLIN_API_TOKEN=your_joplin_api_token_here
JOPLIN_BASE_URL=http://host.docker.internal:41184

# Optional
MCP_DEBUG=false
```

### Local Deployment (MacBook)

```bash
cd /opt/docker/mcp-proxy/MCPs/joplin-mcp
docker compose -f docker-compose.yml -f docker-compose.local.yaml up -d
curl http://localhost:8006/health
curl https://mcp.orb.local/joplin/health
```

### Production Deployment (Wyze)

```bash
cd /opt/docker/mcp-proxy/MCPs/joplin-mcp
docker compose -f docker-compose.yml -f docker-compose.wyze.yaml up -d
curl https://mcp.nstam.eu/joplin/health
```

### Update Caddyfile (Local)

Add to `/opt/docker/mcp-gateway/Caddyfile`:

```caddyfile
handle_path /joplin* {
    reverse_proxy joplin-mcp-server:8006 {
        header_up Host {upstream_hostport}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

## Reference

- [Joplin MCP Documentation](https://github.com/alondmnt/joplin-mcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Caddy Documentation](https://caddyserver.com/docs/)
