"""Repository-scoped read-only MCP facade over pinned CodeGraphContext.

Upstream tool schemas/results are preserved. Mutation tools and upstream agent
instructions are intentionally not forwarded. Index/update via run_cgc.py first.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.server import Server
from mcp.server.stdio import stdio_server

ALLOWED = frozenset({
    "find_code", "analyze_code_relationships", "calculate_cyclomatic_complexity",
    "find_dead_code", "find_most_complex_functions", "get_repository_stats",
    "list_indexed_repositories",
})


def error(message):
    return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=message)])


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve(strict=True)
    db = Path(args.db).resolve(strict=True)
    if not repo.is_dir() or not db.is_file():
        parser.error("--repo must be an existing directory and --db an indexed database file")
    root = Path(__file__).resolve().parent
    params = StdioServerParameters(
        command=str(root / "venv/Scripts/python.exe"),
        args=["-X", "utf8", str(root / "run_cgc.py"), "--path", str(db), "mcp", "start"],
        cwd=str(repo), env={**os.environ, "PYTHONUTF8": "1", "CGC_ALLOWED_ROOTS": str(repo)},
    )
    async with stdio_client(params) as (backend_read, backend_write):
        async with ClientSession(backend_read, backend_write) as backend:
            await backend.initialize()
            catalog = {tool.name: tool for tool in (await backend.list_tools()).tools if tool.name in ALLOWED}
            if catalog.keys() != ALLOWED:
                raise RuntimeError("Pinned upstream tool catalog changed")
            server = Server("codegraph-context-readonly", version="0.6.13-local.1",
                            instructions="Read-only static code graph for the configured repository. Verify inferred relationships against source; results may be incomplete or stale. Indexing is an explicit CLI operation.")

            @server.list_tools()
            async def list_tools():
                return list(catalog.values())

            @server.call_tool()
            async def call_tool(name, arguments):
                if name not in ALLOWED:
                    return error("Tool is not exposed by this read-only facade")
                arguments = dict(arguments)
                if arguments.get("graph_name"):
                    return error("graph_name override is disabled; this facade uses one configured database")
                if "repo_path" in arguments and Path(arguments["repo_path"]).resolve() != repo:
                    return error("repo_path must match the configured repository")
                if "repo_path" in catalog[name].inputSchema.get("properties", {}):
                    arguments["repo_path"] = repo.as_posix()
                for field in ("path", "context"):
                    value = arguments.get(field)
                    if value and ("/" in value or "\\" in value):
                        candidate = Path(value)
                        candidate = candidate if candidate.is_absolute() else repo / candidate
                        if not candidate.resolve().is_relative_to(repo):
                            return error(f"{field} must remain inside the configured repository")
                        arguments[field] = candidate.resolve().as_posix()
                return await backend.call_tool(name, arguments)

            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

