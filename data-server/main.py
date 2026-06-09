import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
import db

# Initialize the server
app = Server("finflow-data")

class GetRecentExpensesInput(BaseModel):
    limit: int = Field(default=20, description="Number of rows to return")
    month: str | None = Field(default=None, description="Month in 'YYYY-MM' format (e.g., '2025-06')")

class GetCategorySummaryInput(BaseModel):
    month: str = Field(..., description="Month in 'YYYY-MM' format (e.g., '2025-06')")

class ExecuteQueryInput(BaseModel):
    sql: str = Field(..., description="A valid SQLite SELECT query against the expenses table")

class GetSpendingAnomaliesInput(BaseModel):
    month: str = Field(..., description="Month in 'YYYY-MM' format (e.g., '2025-06')")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_recent_expenses",
            description=(
                "Returns a list of recent expense transactions from the local SQLite database. "
                "Use this when the user asks about their spending history, recent transactions, "
                "or wants to see raw expense data for a given month."
            ),
            inputSchema=GetRecentExpensesInput.model_json_schema()
        ),
        Tool(
            name="get_category_summary",
            description=(
                "Returns a summary of expenses aggregated by category for a given month. "
                "Use this to show a high-level breakdown of spending."
            ),
            inputSchema=GetCategorySummaryInput.model_json_schema()
        ),
        Tool(
            name="execute_query",
            description=(
                "Executes a raw SQLite SELECT query against the local expenses database. "
                "Use this for any specific or complex financial question that the other tools "
                "cannot answer — e.g. multi-month trends, filtered lookups, averages, or "
                "custom aggregations. The expenses table schema is: "
                "id (int), date (text YYYY-MM-DD), amount (real), merchant (text), "
                "category (text), type (text). Only SELECT queries are permitted."
            ),
            inputSchema=ExecuteQueryInput.model_json_schema()
        ),
        Tool(
            name="get_spending_anomalies",
            description=(
                "Finds merchants where the given month's total spend is more than 50%% higher "
                "than the average of the prior 3 months. Use this to flag unusual or spiking "
                "spending at specific merchants."
            ),
            inputSchema=GetSpendingAnomaliesInput.model_json_schema()
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "get_recent_expenses":
            args = GetRecentExpensesInput(**arguments)
            expenses = db.get_recent_expenses(limit=args.limit, month=args.month)
            return [TextContent(type="text", text=json.dumps(expenses))]
            
        elif name == "get_category_summary":
            args = GetCategorySummaryInput(**arguments)
            summary = db.get_category_summary(month=args.month)
            return [TextContent(type="text", text=json.dumps(summary))]
        
        elif name == "execute_query":
            args = ExecuteQueryInput(**arguments)
            results = db.execute_read_query(args.sql)
            return [TextContent(type="text", text=json.dumps(results))]

        elif name == "get_spending_anomalies":
            args = GetSpendingAnomaliesInput(**arguments)
            anomalies = db.get_spending_anomalies(month=args.month)
            return [TextContent(type="text", text=json.dumps(anomalies))]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

async def main():
    # Ensure DB and sessions table are initialized before starting the server
    db.init_db()
    db.init_sessions_table()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
