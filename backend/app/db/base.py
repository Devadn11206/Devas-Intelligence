from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convention for foreign keys and indices
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

shared_metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = shared_metadata


class IntelBase(DeclarativeBase):
    metadata = MetaData(schema="intel", naming_convention=convention)


class TenantBase(DeclarativeBase):
    metadata = MetaData(schema="tenant", naming_convention=convention)
