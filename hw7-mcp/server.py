"""HW-7: read-only employee-zone authorization tools."""
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, create_engine, select
from starlette.responses import JSONResponse

from models import EmployeeZoneAuthorization, WarehouseEmployee


class Authorization(SQLModel):
    employee_id: str
    zone_code: str
    authorization_status: str = Field(
        description="Recorded status: Active or Suspended."
    )


class EmployeeAuthorizations(SQLModel):
    employee_id: str
    employee_name: str
    authorization_count: int = Field(ge=0)
    authorizations: list[Authorization]


database_path = Path(
    os.environ.get("WAREHOUSE_DATABASE", "/data/warehouse.db")
).resolve()
if not database_path.is_file():
    raise FileNotFoundError(f"Warehouse database not found: {database_path}")

engine = create_engine(
    f"sqlite:///{database_path.as_uri()}?mode=ro&uri=true",
    connect_args={"check_same_thread": False},
)
mcp = FastMCP("HW-7 Warehouse Authorizations")


@mcp.tool
def get_employee_authorizations(employee_id: str) -> EmployeeAuthorizations:
    """Read all recorded zone authorizations for an existing employee.

    Returns a count and records sorted by zone code. An existing employee with
    no authorizations returns zero and an empty list. A nonexistent employee
    produces a tool error. This tool cannot create, update, or delete records.
    """
    try:
        with Session(engine) as session:
            employee = session.get(WarehouseEmployee, employee_id)
            if employee is None:
                raise ToolError("Employee not found. Check the employee ID.")
            statement = select(EmployeeZoneAuthorization).where(
                EmployeeZoneAuthorization.employee_id == employee_id
            ).order_by(EmployeeZoneAuthorization.zone_code)
            records = session.exec(statement).all()
            return EmployeeAuthorizations(
                employee_id=employee.employee_id,
                employee_name=employee.employee_name,
                authorization_count=len(records),
                authorizations=[Authorization.model_validate(record) for record in records],
            )
    except SQLAlchemyError as exc:
        raise ToolError("Cannot read the warehouse database.") from exc


@mcp.tool
def get_authorization(employee_id: str, zone_code: str) -> Authorization:
    """Read the recorded status for one employee-zone authorization.

    Supply both employee_id and zone_code. Active and Suspended are recorded
    statuses, not a comprehensive safety or certification assessment. A missing
    employee or authorization produces a tool error. This tool cannot write.
    """
    try:
        with Session(engine) as session:
            if session.get(WarehouseEmployee, employee_id) is None:
                raise ToolError("Employee not found. Check the employee ID.")
            record = session.get(
                EmployeeZoneAuthorization, (employee_id, zone_code)
            )
            if record is None:
                raise ToolError("Authorization not found for this employee-zone pair.")
            return Authorization.model_validate(record)
    except SQLAlchemyError as exc:
        raise ToolError("Cannot read the warehouse database.") from exc


@mcp.custom_route("/healthz", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001, stateless_http=True)
