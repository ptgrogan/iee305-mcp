"""Exercise the real MCP HTTP connection and read-only database access."""
import asyncio

from fastmcp import Client
from sqlalchemy.exc import OperationalError

from server import engine


async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:
        tools = await client.list_tools()
        assert [tool.name for tool in tools] == ["get_operator_summary"]
        schema = tools[0].output_schema
        assert set(schema["required"]) == {
            "op_id", "name", "observation_count", "total_minutes"
        }
        fields = schema["properties"]
        assert fields["op_id"]["type"] == "string"
        assert fields["name"]["type"] == "string"
        assert fields["observation_count"]["type"] == "integer"
        assert fields["observation_count"]["minimum"] == 0
        assert fields["total_minutes"]["type"] == "number"
        assert fields["total_minutes"]["minimum"] == 0
        assert "overlaps" in fields["total_minutes"]["description"]
        print("MCP discovery exposes the typed OperatorSummary output schema.")
        for op_id, count, minutes in [
            ("OP-14", 14, 202.95), ("OP-03", 29, 923.0), ("OP-53", 0, 0)
        ]:
            result = await client.call_tool("get_operator_summary", {"op_id": op_id})
            data = result.structured_content
            assert set(data) == set(schema["required"]), data
            assert data["op_id"] == op_id, data
            assert isinstance(data["name"], str), data
            assert data["observation_count"] == count, data
            assert abs(data["total_minutes"] - minutes) < 0.001, data
            print(f"{op_id}: {count} observations, {minutes} minutes")
        for op_id in ["OP-99", "OP-14' OR 1=1 --"]:
            result = await client.call_tool(
                "get_operator_summary", {"op_id": op_id}, raise_on_error=False
            )
            assert result.is_error, result
        print("Missing and invalid operator IDs return MCP tool errors.")

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("UPDATE Operator SET name=name WHERE op_id='OP-14'")
    except OperationalError as exc:
        assert "readonly" in str(exc).lower(), str(exc)
    else:
        raise AssertionError("Database connection unexpectedly allowed a write.")
    print("MCP output schema, HTTP calls, and SQLite read-only mode passed.")


asyncio.run(main())