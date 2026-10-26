"""L-18: query the lecture database directly inside an MCP tool."""
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, create_engine, select
from starlette.responses import JSONResponse

from models import Operator, TAMObservation


class OperatorSummary(SQLModel):
    """An operator's observation count and summed recorded duration."""

    op_id: str
    name: str
    observation_count: int = Field(ge=0)
    total_minutes: float = Field(
        ge=0,
        description="Sum of recorded observation durations in minutes; overlaps count separately.",
    )


database_path = Path(
    os.environ.get("TAM_DATABASE", Path(__file__).with_name("tam.db"))
).resolve()
if not database_path.is_file():
    raise FileNotFoundError(f"Lecture database not found: {database_path}")

# Open the existing lecture database in read-only mode.
engine = create_engine(
    f"sqlite:///{database_path.as_uri()}?mode=ro&uri=true",
    connect_args={"check_same_thread": False},
)

mcp = FastMCP("Time-and-Motion")


@mcp.tool
def get_operator_summary(op_id: str) -> OperatorSummary:
    """Get an operator's name, observation count, and total recorded minutes.

    Use an operator ID such as OP-14. Total minutes sum all observations,
    including overlaps; they do not measure productivity or elapsed shift time.
    """
    try:
        with Session(engine) as session:
            operator = session.get(Operator, op_id)
            if operator is None:
                raise ToolError("Operator not found. Check the operator ID.")

            statement = select(TAMObservation).where(TAMObservation.op_id == op_id)
            observations = session.exec(statement).all()

            total_minutes = 0.0
            for observation in observations:
                duration = observation.end - observation.start
                total_minutes += duration.total_seconds() / 60

            return OperatorSummary(
                op_id=operator.op_id,
                name=operator.name,
                observation_count=len(observations),
                total_minutes=total_minutes,
            )
    except SQLAlchemyError as exc:
        raise ToolError("Cannot read the time-and-motion database.") from exc



# Hosting details for the browser-based classroom deployment.
@mcp.custom_route("/healthz", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001, stateless_http=True)