"""Table mappings for the existing IEE 305 HW-6 database.
Use these models with SQLModel, or implement the API with parameterized sqlite3 SQL.
The provided database already contains its tables, keys, constraints, and records.
"""
from sqlmodel import Field, SQLModel


class WarehouseEmployee(SQLModel, table=True):
    __tablename__ = "WarehouseEmployee"
    employee_id: str = Field(primary_key=True)
    employee_name: str


class WarehouseZone(SQLModel, table=True):
    __tablename__ = "WarehouseZone"
    zone_code: str = Field(primary_key=True)
    temperature_requirement: str
    access_restriction: str


class EmployeeZoneAuthorization(SQLModel, table=True):
    __tablename__ = "EmployeeZoneAuthorization"
    employee_id: str = Field(primary_key=True, foreign_key="WarehouseEmployee.employee_id")
    zone_code: str = Field(primary_key=True, foreign_key="WarehouseZone.zone_code")
    authorization_status: str
