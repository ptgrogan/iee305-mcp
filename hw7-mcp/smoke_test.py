"""Run inside the hw7-mcp container; uses no model key or student accounts."""
import asyncio
import hashlib
import sqlite3
from fastmcp import Client
from sqlalchemy.exc import OperationalError
from server import database_path, engine


async def main():
    before = hashlib.sha256(database_path.read_bytes()).hexdigest()
    async with Client("http://127.0.0.1:8001/mcp") as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert set(tools) == {"get_employee_authorizations", "get_authorization"}
        assert set(tools["get_authorization"].input_schema["required"]) == {
            "employee_id", "zone_code"
        }
        for tool in tools.values():
            assert tool.output_schema["type"] == "object"
        for employee, zone, status in [
            ("EMP-09", "AMB", "Active"), ("EMP-14", "AMB", "Active"),
            ("EMP-31", "BLK", "Suspended"), ("EMP-36", "REF", "Active"),
        ]:
            result = await client.call_tool("get_authorization", {
                "employee_id": employee, "zone_code": zone,
            })
            assert result.structured_content == {
                "employee_id": employee, "zone_code": zone,
                "authorization_status": status,
            }, result
            print(employee, zone, status)
        for employee, count in [("EMP-14", 1), ("EMP-31", 1), ("EMP-53", 0)]:
            result = await client.call_tool("get_employee_authorizations", {
                "employee_id": employee,
            })
            data = result.structured_content
            assert data["employee_id"] == employee
            assert data["employee_name"]
            assert data["authorization_count"] == count == len(data["authorizations"])
            if count == 0:
                assert data["authorizations"] == []
            print(employee, "authorization count", count)
        for tool, args, expected_error in [
            ("get_employee_authorizations", {"employee_id": "EMP-999"}, "Employee not found"),
            ("get_authorization", {"employee_id": "EMP-999", "zone_code": "AMB"}, "Employee not found"),
            ("get_authorization", {"employee_id": "EMP-14", "zone_code": "REF"}, "Authorization not found"),
            ("get_employee_authorizations", {"employee_id": "EMP-14' OR 1=1 --"}, "Employee not found"),
        ]:
            result = await client.call_tool(tool, args, raise_on_error=False)
            assert result.is_error and expected_error in str(result.content), result
        result = await client.call_tool("get_authorization", {"employee_id": "EMP-14"}, raise_on_error=False)
        assert result.is_error
        # A model cannot select a write tool because none is exposed.
        result = await client.call_tool("update_authorization", {
            "employee_id": "EMP-14", "zone_code": "AMB", "authorization_status": "Suspended"
        }, raise_on_error=False)
        assert result.is_error
        # Recheck the actual stored value, independent of any model response.
        result = await client.call_tool("get_authorization", {
            "employee_id": "EMP-14", "zone_code": "AMB"
        })
        assert result.structured_content["authorization_status"] == "Active"
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("UPDATE EmployeeZoneAuthorization SET authorization_status=authorization_status")
    except OperationalError as exc:
        assert "readonly" in str(exc).lower()
    else:
        raise AssertionError("Read-only engine allowed a write")
    # Bypass the engine's mode=ro to check the Docker mount independently.
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("UPDATE EmployeeZoneAuthorization SET authorization_status=authorization_status")
    except sqlite3.OperationalError as exc:
        assert "readonly" in str(exc).lower()
    else:
        connection.rollback()
        raise AssertionError("Read-only mount allowed a write")
    finally:
        connection.close()
    assert hashlib.sha256(database_path.read_bytes()).hexdigest() == before
    print("PASS: discovery, schemas, results, errors, no write tool, read-only engine/mount, unchanged snapshot")


asyncio.run(main())

