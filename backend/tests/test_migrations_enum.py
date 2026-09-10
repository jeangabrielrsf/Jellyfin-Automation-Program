"""Regression test: Postgres enums created by Alembic migrations must match
the SQLAlchemy model enums.

SQLAlchemy's ``Enum`` column stores the *member name* of a Python enum
(UPPERCASE, e.g. ``'CLEARED'``). If a migration adds a value with the wrong
case (e.g. ``'cleared'``, the member value), every query filtering on that
column raises ``InvalidTextRepresentation`` on Postgres. SQLite never
validates enum values, so the normal test suite cannot catch this.

This test replays the enum evolution from the migration files (in the actual
migration order, following the revision chain) and asserts the final value
set matches the model enum member names.
"""
import enum
import importlib.util
import re
from pathlib import Path

import pytest

from app.models.download import ContentType, DownloadStatus

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _load_migration_modules():
    modules = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[module.revision] = module
    return modules


def _ordered_migrations(modules):
    heads = [
        rev
        for rev, module in modules.items()
        if not any(other.down_revision == rev for other in modules.values())
    ]
    assert len(heads) == 1, f"Expected a single migration head, got {heads}"
    ordered = []
    revision = heads[0]
    while revision:
        module = modules[revision]
        ordered.append(module)
        revision = module.down_revision
    return list(reversed(ordered))


def _upgrade_body(source: str) -> str:
    match = re.search(r"def upgrade\(\)\s*(?:->[^:]*)?:\n(.*?)(?=\ndef |\Z)", source, re.DOTALL)
    assert match, "Could not find upgrade() body in migration source"
    return match.group(1)


def _evolve_enum(enum_name: str) -> set:
    values = set()
    seen_create = False
    for module in _ordered_migrations(_load_migration_modules()):
        body = _upgrade_body(module.__loader__.get_source(module.__name__))
        create = re.search(rf"sa\.Enum\(([^)]*name='{enum_name}'[^)]*)\)", body)
        if create:
            values_body = create.group(1).split("name=")[0]
            values = set(re.findall(r"'([^']+)'", values_body))
            seen_create = True
        for value in re.findall(rf"ALTER TYPE {enum_name} ADD VALUE '([^']+)'", body):
            values.add(value)
        for old, new in re.findall(
            rf"ALTER TYPE {enum_name} RENAME VALUE '([^']+)' TO '([^']+)'", body
        ):
            assert old in values, (
                f"RENAME VALUE '{old}' TO '{new}' on enum {enum_name} refers to a "
                f"value not present in the enum ({sorted(values)})"
            )
            values.remove(old)
            values.add(new)
    assert seen_create, f"No migration creates enum {enum_name}"
    return values


@pytest.mark.parametrize(
    "enum_name,enum_class",
    [
        ("downloadstatus", DownloadStatus),
        ("contenttype", ContentType),
    ],
)
def test_migration_enum_matches_model_member_names(enum_name, enum_class):
    model_values = {member.name for member in enum_class}
    assert isinstance(enum_class, type) and issubclass(enum_class, enum.Enum)

    migrated_values = _evolve_enum(enum_name)

    assert migrated_values == model_values, (
        f"Enum '{enum_name}' in migrations ({sorted(migrated_values)}) does not "
        f"match model enum {enum_class.__name__} member names "
        f"({sorted(model_values)}). SQLAlchemy stores member names; a mismatch "
        f"causes InvalidTextRepresentation on Postgres."
    )
