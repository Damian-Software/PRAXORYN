"""Optional MCP read-only server. Install a compatible mcp Python SDK first."""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from .plugins import invoice_sum

app = FastMCP('Praxoryn Read Only Tools')

@app.tool()
def sum_invoice_lines(values: list[str]) -> str:
    """Calculate a total from decimal amounts. Does not write to an accounting system."""
    return invoice_sum(values)

if __name__ == '__main__':
    app.run()
