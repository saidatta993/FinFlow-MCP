"""
UI Bridge MCP Server + FastAPI SSE Server.

Threading Architecture:
MCP stdio transport must use the main thread because it intercepts standard input
and standard output. Blocking or redirecting stdio across threads causes issues.
Therefore, the MCP server runs asynchronously in the main thread.

The FastAPI (uvicorn) server is started in a background thread. It listens on 
a TCP port for SSE connections from the browser. The two domains communicate 
via the thread-safe `SSEManager` which bridges the main MCP event loop and the 
FastAPI background thread's event loop.

V2 additions:
- summary + query fields in dashboard update payload
- Session persistence via shared db.py
- REST endpoints for session CRUD
- Line chart type support
"""
import asyncio
import threading
import json
import os
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sse_starlette.sse import EventSourceResponse
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from sse_manager import SSEManager

# Add data-server to sys.path so we can import shared db.py
DATA_SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-server")
sys.path.insert(0, DATA_SERVER_DIR)
import db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sse_manager, fastapi_loop
    fastapi_loop = asyncio.get_running_loop()
    sse_manager = SSEManager(fastapi_loop)
    # Ensure sessions table exists
    db.init_sessions_table()
    yield

# --- FastAPI Setup ---
app_fastapi = FastAPI(lifespan=lifespan)

# Allow CORS for the frontend
app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to share state between threads
sse_manager: SSEManager | None = None
fastapi_loop: asyncio.AbstractEventLoop | None = None


@app_fastapi.get("/health")
def health_check():
    return {"status": "ok"}

@app_fastapi.get("/sse/dashboard")
async def sse_dashboard(request: Request):
    """SSE endpoint to stream dashboard updates."""
    if sse_manager is None:
        return {"error": "SSE Manager not initialized"}
        
    queue = sse_manager.connect()
    
    async def event_generator():
        try:
            while True:
                # Disconnect if client leaves
                if await request.is_disconnected():
                    break
                # Wait for data in the queue
                data = await queue.get()
                yield {"data": data}
        finally:
            sse_manager.disconnect(queue)

    return EventSourceResponse(event_generator())


# --- Session REST Endpoints (V2) ---

@app_fastapi.get("/sessions")
def get_sessions():
    """Returns all saved sessions ordered by timestamp descending."""
    sessions = db.get_all_sessions()
    return sessions

@app_fastapi.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: int):
    """Deletes a session by id."""
    deleted = db.delete_session(session_id)
    return {"deleted": deleted, "id": session_id}


def run_fastapi():
    """Runs the FastAPI application. This will run in a separate thread."""
    host = os.getenv("SSE_HOST", "0.0.0.0")
    port = int(os.getenv("SSE_PORT", "8000"))
    # Disable access logs and all uvicorn logging so it absolutely doesn't print to stdout
    uvicorn.run(app_fastapi, host=host, port=port, log_config=None)


# --- MCP Server Setup ---
app_mcp = Server("finflow-ui")

class DashboardUpdateInput(BaseModel):
    """Input schema for the update_dashboard_chart MCP tool."""
    chart_type: str = Field(..., description="Chart type: 'bar' | 'pie' | 'line'")
    title: str = Field(..., description="Chart title string")
    data: list[dict] = Field(..., description="Chart data: [{name: str, value: float}]")
    summary: str = Field(default="", description="2-3 sentence natural language insight from Claude about the data")
    query: str = Field(default="", description="The original natural language question the user asked")

@app_mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="update_dashboard_chart",
            description=(
                "Renders a visualization on the live dashboard and displays a natural language summary. "
                "Always populate the summary field with 2-3 sentences of insight about the data "
                "being shown — e.g. largest spending category, notable trends, or anomalies. "
                "Also populate the query field with the user's original question. "
                "\n\nChart type selection rules (follow strictly):\n"
                "- Use 'pie' when showing proportions or category breakdowns (e.g. spending by category)\n"
                "- Use 'bar' when comparing discrete values side by side (e.g. top merchants, month vs month)\n"
                "- Use 'line' when showing a value changing over time (e.g. monthly spend trend, daily totals)\n"
                "\nAlways include a 2-3 sentence summary with key insight about the data."
            ),
            inputSchema=DashboardUpdateInput.model_json_schema()
        )
    ]

@app_mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "update_dashboard_chart":
        try:
            args = DashboardUpdateInput(**arguments)
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Build the SSE payload
            payload = {
                "chart_type": args.chart_type,
                "title": args.title,
                "data": args.data,
                "summary": args.summary,
                "timestamp": timestamp
            }
            
            if sse_manager:
                # Broadcasting is thread-safe via SSEManager
                sse_manager.broadcast(payload)
                
                # Persist session to SQLite for history
                try:
                    db.insert_session(
                        timestamp=timestamp,
                        query=args.query,
                        chart_type=args.chart_type,
                        title=args.title,
                        data_json=json.dumps(args.data),
                        summary=args.summary
                    )
                except Exception as db_err:
                    # Don't fail the MCP tool if session persistence fails
                    pass
                
                return [TextContent(type="text", text="Dashboard updated successfully")]
            else:
                return [TextContent(type="text", text="Error: SSE Manager not ready")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def run_mcp_server():
    """Runs the MCP server on stdio transport in the main thread."""
    async with stdio_server() as (read_stream, write_stream):
        await app_mcp.run(read_stream, write_stream, app_mcp.create_initialization_options())

def main():
    # 1. Start FastAPI in a background thread
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    
    # Wait briefly for FastAPI to initialize its event loop and sse_manager
    import time
    time.sleep(1)
    
    # 2. Run MCP Server in the main thread
    asyncio.run(run_mcp_server())

if __name__ == "__main__":
    main()
