"""SQLModel table mappings for tam.db, copied from IEE305_L14_TAM.db.

These models describe the existing tables. The SQLite database retains its
CHECK, NOT NULL, primary-key, and foreign-key constraints. Do not recreate the
database with SQLModel.metadata.create_all(); it already contains the schema
and sample data used in lectures 14 and 16.
"""

from pydantic import NaiveDatetime
from sqlalchemy import ForeignKeyConstraint
from sqlmodel import Field, SQLModel


class Operator(SQLModel, table=True):
    """An operator who performs time-and-motion observations."""

    __tablename__ = "Operator"

    op_id: str = Field(primary_key=True)
    name: str


class WorkOrder(SQLModel, table=True):
    """A work order identified by its job number."""

    __tablename__ = "WorkOrder"

    job_num: str = Field(primary_key=True)


class DuctSpec(SQLModel, table=True):
    """The material, gauge, and shape of a duct specification."""

    __tablename__ = "DuctSpec"

    spec_id: str = Field(primary_key=True)
    material: str
    gauge: int
    shape: str


class WOLine(SQLModel, table=True):
    """A work-order line with a composite primary key."""

    __tablename__ = "WOLine"

    job_num: str = Field(primary_key=True, foreign_key="WorkOrder.job_num")
    line_num: int = Field(primary_key=True)
    quantity: int
    spec_id: str = Field(foreign_key="DuctSpec.spec_id")


class TAMObservation(SQLModel, table=True):
    """An observation with timestamps that do not include a time zone."""

    __tablename__ = "TAMObservation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["job_num", "line_num"],
            ["WOLine.job_num", "WOLine.line_num"],
        ),
    )

    obs_id: str = Field(primary_key=True)
    start: NaiveDatetime
    end: NaiveDatetime
    op_id: str = Field(foreign_key="Operator.op_id")
    job_num: str
    line_num: int
