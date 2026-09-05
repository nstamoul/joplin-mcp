"""Regression tests for the FastMCP 3 runtime contract.

Startup logging used to read ``mcp._tool_manager._tools``. FastMCP 3 removed
that private attribute, which aborted the server before it ever bound a port.
Tool-name discovery must therefore go through the public API and must never be
fatal, because it only feeds a log line.
"""

import asyncio

import pytest
from fastmcp import FastMCP

from joplin_mcp.fastmcp_server import list_registered_tool_names


def _server_with_tools() -> FastMCP:
    server = FastMCP("contract-probe")

    @server.tool
    def alpha(value: int) -> int:
        """First probe tool."""
        return value

    @server.tool
    def beta(value: int) -> int:
        """Second probe tool."""
        return value

    return server


def test_private_tool_manager_is_gone_in_fastmcp3():
    """Documents the upstream removal this module has to tolerate."""
    assert getattr(FastMCP("contract-probe"), "_tool_manager", None) is None


def test_lists_registered_tool_names():
    assert sorted(list_registered_tool_names(_server_with_tools())) == ["alpha", "beta"]


def test_never_raises_when_discovery_fails():
    class Broken:
        def list_tools(self):
            raise RuntimeError("upstream API changed again")

    assert list_registered_tool_names(Broken()) == []


def test_works_inside_a_running_event_loop():
    async def main():
        return list_registered_tool_names(_server_with_tools())

    assert sorted(asyncio.run(main())) == ["alpha", "beta"]
