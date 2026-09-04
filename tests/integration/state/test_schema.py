"""Integration tests for the Supabase schema and owner-scoped RLS policies."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import psycopg
import pytest
from psycopg import Connection
from psycopg.errors import CheckViolation, InsufficientPrivilege

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "state" / "schema.sql"
RLS_PATH = REPO_ROOT / "state" / "rls_policies.sql"
TEST_DB_URL_ENV = "SUPABASE_TEST_DB_URL"

OWNER_A = UUID("11111111-1111-4111-8111-111111111111")
OWNER_B = UUID("22222222-2222-4222-8222-222222222222")
ROLE_ID = UUID("33333333-3333-4333-8333-333333333333")
DIGEST_ID = UUID("44444444-4444-4444-8444-444444444444")

TABLES = (
    "roles",
    "application_status_history",
    "contacts",
    "skill_gap_findings",
    "digests",
    "digest_roles",
)
POLICY_COMMANDS = {"SELECT", "INSERT", "UPDATE", "DELETE"}
UNAUTHORIZED_INSERTS = (
    (
        "roles",
        """
        insert into public.roles
            (owner_id, source, source_job_id, listing_url,
             company, title, location, description)
        values
            (%s, 'lever', 'job-2', 'https://example.test/jobs/2',
             'Other Co', 'Engineer', 'Remote', 'Description')
        """,
        (OWNER_A,),
    ),
    (
        "application_status_history",
        """
        insert into public.application_status_history (owner_id, role_id, status)
        values (%s, %s, 'applied')
        """,
        (OWNER_A, ROLE_ID),
    ),
    (
        "contacts",
        """
        insert into public.contacts (owner_id, name, company)
        values (%s, 'Other Contact', 'Example Co')
        """,
        (OWNER_A,),
    ),
    (
        "skill_gap_findings",
        """
        insert into public.skill_gap_findings
            (owner_id, role_id, skill, finding_type, evidence)
        values (%s, %s, 'Python', 'missing', 'Required by role')
        """,
        (OWNER_A, ROLE_ID),
    ),
    (
        "digests",
        """
        insert into public.digests (owner_id, digest_date)
        values (%s, current_date + 1)
        """,
        (OWNER_A,),
    ),
    (
        "digest_roles",
        """
        insert into public.digest_roles (digest_id, role_id, owner_id)
        values (%s, %s, %s)
        """,
        (DIGEST_ID, ROLE_ID, OWNER_A),
    ),
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database() -> Iterator[Connection]:
    """Apply both migrations inside a transaction on a dedicated test project."""
    database_url = os.getenv(TEST_DB_URL_ENV)
    if not database_url:
        pytest.skip(f"{TEST_DB_URL_ENV} is not set")

    connection = psycopg.connect(database_url)
    try:
        with connection.cursor() as cursor:
            existing = cursor.execute(
                """
                select tablename
                from pg_catalog.pg_tables
                where schemaname = 'public'
                """,
            ).fetchall()
            if existing:
                pytest.fail(
                    f"{TEST_DB_URL_ENV} must point to a clean test database; "
                    f"found existing tables: {existing}"
                )

            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            cursor.execute(RLS_PATH.read_text(encoding="utf-8"))
            _seed_test_rows(cursor)

        yield connection
    finally:
        connection.rollback()
        connection.close()


def _seed_test_rows(cursor: psycopg.Cursor) -> None:
    """Create two owners and one owner-A row in every application table."""
    cursor.execute(
        """
        insert into auth.users
            (id, instance_id, aud, role, email, created_at, updated_at)
        values
            (%s, '00000000-0000-0000-0000-000000000000',
             'authenticated', 'authenticated', 'owner-a@example.test', now(), now()),
            (%s, '00000000-0000-0000-0000-000000000000',
             'authenticated', 'authenticated', 'owner-b@example.test', now(), now())
        """,
        (OWNER_A, OWNER_B),
    )
    cursor.execute(
        """
        insert into public.roles
            (id, owner_id, source, source_job_id, listing_url,
             company, title, location, description)
        values
            (%s, %s, 'greenhouse', 'job-1', 'https://example.test/jobs/1',
             'Example Co', 'Backend Engineer', 'Remote', 'Example description')
        """,
        (ROLE_ID, OWNER_A),
    )
    cursor.execute(
        """
        insert into public.application_status_history
            (owner_id, role_id, status, context)
        values (%s, %s, 'pursued', 'Strong match')
        """,
        (OWNER_A, ROLE_ID),
    )
    cursor.execute(
        """
        insert into public.contacts (owner_id, name, company, email)
        values (%s, 'Alex Example', 'Example Co', 'alex@example.test')
        """,
        (OWNER_A,),
    )
    cursor.execute(
        """
        insert into public.skill_gap_findings
            (owner_id, role_id, skill, finding_type, evidence)
        values (%s, %s, 'PostgreSQL', 'weak', 'Limited production evidence')
        """,
        (OWNER_A, ROLE_ID),
    )
    cursor.execute(
        """
        insert into public.digests (id, owner_id, digest_date)
        values (%s, %s, current_date)
        """,
        (DIGEST_ID, OWNER_A),
    )
    cursor.execute(
        """
        insert into public.digest_roles (digest_id, role_id, owner_id)
        values (%s, %s, %s)
        """,
        (DIGEST_ID, ROLE_ID, OWNER_A),
    )


def _execute_as(
    connection: Connection,
    owner_id: UUID,
    statement: str,
    parameters: tuple[object, ...] = (),
    *,
    fetch: bool = False,
) -> tuple[list[tuple], int]:
    """Execute once as an authenticated owner, then roll back that operation."""
    connection.execute("savepoint rls_operation")
    error: Exception | None = None
    rows: list[tuple] = []
    rowcount = -1
    try:
        connection.execute("set local role authenticated")
        connection.execute(
            "select set_config('request.jwt.claim.sub', %s, true)",
            (str(owner_id),),
        )
        result = connection.execute(statement, parameters)
        if fetch:
            rows = result.fetchall()
        rowcount = result.rowcount
    except Exception as exc:  # re-raised after restoring the outer transaction
        error = exc
    finally:
        connection.execute("rollback to savepoint rls_operation")
        connection.execute("release savepoint rls_operation")

    if error is not None:
        raise error
    return rows, rowcount


def test_schema__fresh_database__creates_exact_core_tables(
    database: Connection,
) -> None:
    rows = database.execute(
        """
        select tablename
        from pg_catalog.pg_tables
        where schemaname = 'public'
        order by tablename
        """,
    ).fetchall()

    assert [row[0] for row in rows] == sorted(TABLES)


def test_schema__every_core_table__has_rls_enabled_and_forced(
    database: Connection,
) -> None:
    rows = database.execute(
        """
        select c.relname, c.relrowsecurity, c.relforcerowsecurity
        from pg_catalog.pg_class as c
        join pg_catalog.pg_namespace as n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relname = any(%s)
        order by c.relname
        """,
        (list(TABLES),),
    ).fetchall()

    assert rows == [(table, True, True) for table in sorted(TABLES)]


def test_rls__every_core_table__has_policy_for_each_operation(
    database: Connection,
) -> None:
    rows = database.execute(
        """
        select tablename, cmd
        from pg_catalog.pg_policies
        where schemaname = 'public' and tablename = any(%s)
        """,
        (list(TABLES),),
    ).fetchall()
    commands_by_table = {
        table: {command for row_table, command in rows if row_table == table}
        for table in TABLES
    }

    assert commands_by_table == {table: POLICY_COMMANDS for table in TABLES}


@pytest.mark.parametrize("table", TABLES)
def test_rls__different_owner_selects_table__returns_no_rows(
    database: Connection, table: str
) -> None:
    rows, _ = _execute_as(
        database, OWNER_B, f"select owner_id from public.{table}", fetch=True
    )

    assert rows == []


@pytest.mark.parametrize("table", TABLES)
def test_rls__different_owner_updates_table__affects_no_rows(
    database: Connection, table: str
) -> None:
    _, rowcount = _execute_as(
        database,
        OWNER_B,
        f"update public.{table} set owner_id = %s",
        (OWNER_B,),
    )

    assert rowcount == 0


@pytest.mark.parametrize("table", TABLES)
def test_rls__different_owner_deletes_table__affects_no_rows(
    database: Connection, table: str
) -> None:
    _, rowcount = _execute_as(database, OWNER_B, f"delete from public.{table}")

    assert rowcount == 0


@pytest.mark.parametrize("table", TABLES)
def test_rls__owning_user_selects_table__returns_own_row(
    database: Connection, table: str
) -> None:
    rows, _ = _execute_as(
        database, OWNER_A, f"select owner_id from public.{table}", fetch=True
    )

    assert rows == [(OWNER_A,)]


@pytest.mark.parametrize(
    ("table", "statement", "parameters"),
    UNAUTHORIZED_INSERTS,
    ids=[case[0] for case in UNAUTHORIZED_INSERTS],
)
def test_rls__different_owner_inserts_table__raises_policy_violation(
    database: Connection,
    table: str,
    statement: str,
    parameters: tuple[object, ...],
) -> None:
    with pytest.raises(InsufficientPrivilege):
        _execute_as(database, OWNER_B, statement, parameters)


def test_rls__anonymous_role__has_no_table_privileges(database: Connection) -> None:
    rows = database.execute(
        """
        select table_name,
               has_table_privilege('anon', format('public.%I', table_name),
                                   'select, insert, update, delete')
        from information_schema.tables
        where table_schema = 'public'
        order by table_name
        """
    ).fetchall()

    assert rows == [(table, False) for table in sorted(TABLES)]


def test_digest__unresolved_role__prevents_review(database: Connection) -> None:
    database.execute("savepoint digest_review")
    try:
        with pytest.raises(CheckViolation, match="all its roles are resolved"):
            database.execute(
                "update public.digests set reviewed_at = now() where id = %s",
                (DIGEST_ID,),
            )
    finally:
        database.execute("rollback to savepoint digest_review")
        database.execute("release savepoint digest_review")


def test_digest__all_roles_resolved__allows_review(database: Connection) -> None:
    database.execute("savepoint digest_review")
    try:
        database.execute(
            """
            update public.digest_roles
            set resolution_status = 'applied', resolved_at = now()
            where digest_id = %s and role_id = %s
            """,
            (DIGEST_ID, ROLE_ID),
        )
        result = database.execute(
            """
            update public.digests
            set reviewed_at = now()
            where id = %s
            returning reviewed_at
            """,
            (DIGEST_ID,),
        ).fetchone()

        assert result is not None
        assert result[0] is not None
    finally:
        database.execute("rollback to savepoint digest_review")
        database.execute("release savepoint digest_review")
