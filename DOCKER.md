# Docker Deployment Guide for Joplin MCP Server

This guide explains how to deploy the Joplin MCP Server as a Docker container with streamable HTTP transport, designed to work with the MCP Gateway (Caddy reverse proxy).

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [MCP Gateway Integration](#mcp-gateway-integration)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Overview

The Joplin MCP Server Docker setup provides:

- **Streamable HTTP Transport**: Full HTTP-based MCP communication (not SSE)
- **Production-Ready Container**: Multi-stage build, non-root user, health checks
- **MCP Gateway Integration**: Seamless connection to Caddy reverse proxy
- **Auto-Discovery**: Works with the mcp_gateway Docker network
- **Health Monitoring**: Built-in health check endpoint at `/health`

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Joplin Desktop** running with Web Clipper enabled
3. **Joplin API Token** (get from: Tools > Options > Web Clipper > Advanced options)
4. **MCP Gateway** network (optional, for reverse proxy integration)

## Quick Start

### 1. Clone and Configure

```bash
cd /path/to/joplin-mcp
cp .env.example .env
# Edit .env and set your JOPLIN_API_TOKEN
```

### 2. Build and Run

```bash
# Build the image
docker compose build

# Start the server
docker compose up -d

# Check logs
docker compose logs -f joplin-mcp-server

# Check health
curl http://localhost:8000/health
```

### 3. Test the Server

```bash
# The server should respond with health status
curl http://localhost:8000/health

# Example response:
# {"status": "healthy", "service": "joplin-mcp", "version": "0.4.1"}
```

## Configuration

### Environment Variables

Configure the server using environment variables in `.env` or `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `streamable-http` | Transport protocol (streamable-http, http, sse, stdio) |
| `MCP_HOST` | `0.0.0.0` | Host to bind to (0.0.0.0 for all interfaces) |
| `MCP_PORT` | `8000` | Port to listen on |
| `MCP_PATH` | `/mcp` | Base path for MCP endpoints |
| `MCP_LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |
| `JOPLIN_API_TOKEN` | (required) | Your Joplin API token |
| `JOPLIN_BASE_URL` | `http://localhost:41184` | Joplin API base URL |
| `JOPLIN_MCP_CONFIG` | - | Optional: Path to config JSON file |

### Using Configuration File

You can mount a configuration file instead of using environment variables:

```yaml
# docker-compose.yml
services:
  joplin-mcp-server:
    volumes:
      - ./joplin-mcp.json:/config/joplin-mcp.json:ro
```

## MCP Gateway Integration

### Adding to Caddy Gateway

To integrate with the MCP Gateway (Caddy reverse proxy), add this to your Caddyfile:

```caddyfile
# Joplin MCP - Note management
handle_path /joplin* {
    reverse_proxy joplin-mcp-server:8000 {
        header_up Host {upstream_hostport}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

### Update Gateway's docker-compose.yml

The Joplin MCP server already uses the `mcp_gateway` network. Just ensure your Caddy gateway includes:

```yaml
# In your Caddy gateway's docker-compose.yml
services:
  mcp-gateway:
    # ... existing config ...
    networks:
      - mcp_gateway

networks:
  mcp_gateway:
    name: mcp_gateway
    driver: bridge
```

### Access Through Gateway

Once configured, access the Joplin MCP server through the gateway:

```bash
# Health check through gateway
curl https://mcp.orb.local/joplin/health

# MCP endpoint
# Configure your Claude Desktop or MCP client to use:
# https://mcp.orb.local/joplin/mcp
```

## Production Deployment

### Security Best Practices

1. **Use Non-Root User**: The container runs as user `mcp` (UID 1001)
2. **Read-Only Config**: Mount config files as read-only (`:ro`)
3. **Network Isolation**: Use Docker networks to isolate services
4. **TLS Termination**: Use Caddy gateway for HTTPS/TLS

### Docker Network Setup

The server connects to the `mcp_gateway` network automatically. To create it:

```bash
docker network create mcp_gateway
```

### Connecting Joplin

If Joplin is running on the host machine:

```yaml
# docker-compose.yml
environment:
  # Use host.docker.internal to access host services
  - JOPLIN_BASE_URL=http://host.docker.internal:41184
```

If Joplin is in another container:

```yaml
# docker-compose.yml
environment:
  # Use container name
  - JOPLIN_BASE_URL=http://joplin-container:41184

networks:
  - mcp_gateway
  - joplin_network  # Shared network with Joplin
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

Here's a complete production-ready setup:

### 1. Directory Structure

```
/opt/joplin-mcp/
├── docker-compose.yml
├── .env
└── joplin-mcp.json (optional)
```

### 2. `.env` File

```bash
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
MCP_LOG_LEVEL=info
JOPLIN_API_TOKEN=your_token_here
JOPLIN_BASE_URL=http://host.docker.internal:41184
```

### 3. Deploy

```bash
cd /opt/joplin-mcp
docker compose up -d
docker compose logs -f
```

### 4. Add to Caddyfile

```caddyfile
handle_path /joplin* {
    reverse_proxy joplin-mcp-server:8000 {
        header_up Host {upstream_hostport}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

### 5. Access

```bash
# Direct access
curl http://localhost:8000/health

# Through gateway
curl https://mcp.orb.local/joplin/health
```

## Reference

- [Joplin MCP Documentation](https://github.com/alondmnt/joplin-mcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Caddy Documentation](https://caddyserver.com/docs/)
