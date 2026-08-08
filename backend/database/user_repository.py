import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Optional

import psycopg
from psycopg import sql
from psycopg.errors import UniqueViolation

from products.sentinel_career.backend.auth.models import User

_USERS_TABLE = "sentinel_users"
_SCHEMA_CREATED = False


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não configurado.")
    return url


@contextmanager
def _get_connection():
    connection = psycopg.connect(_get_database_url())
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_schema(connection) -> None:
    global _SCHEMA_CREATED
    if _SCHEMA_CREATED:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_USERS_TABLE} (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                plan TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                last_login TIMESTAMPTZ,
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
    _SCHEMA_CREATED = True


def _row_to_user(row) -> User:
    return User(
        id=str(row[0]),
        name=row[1],
        email=row[2],
        password_hash=row[3],
        plan=row[4],
        created_at=row[5].isoformat() if row[5] else None,
        last_login=row[6].isoformat() if row[6] else None,
        is_active=bool(row[7]),
    )


def create_user(name: str, email: str, password_hash: str, plan: str) -> User:
    now = datetime.now(timezone.utc)
    with _get_connection() as connection:
        _ensure_schema(connection)
        new_id = uuid.uuid4()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "INSERT INTO {} (id, name, email, password_hash, plan, created_at, last_login, is_active)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, name, email, password_hash, plan, created_at, last_login, is_active"
                    ).format(sql.Identifier(_USERS_TABLE)),
                    (str(new_id), name, email, password_hash, plan, now, None, True),
                )
                row = cursor.fetchone()
        except UniqueViolation as exc:
            raise UniqueViolation("duplicate-user") from exc
    if row is None:
        raise RuntimeError("Falha ao criar usuário.")
    return _row_to_user(row)


def get_user_by_email(email: str) -> Optional[User]:
    with _get_connection() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT id, name, email, password_hash, plan, created_at, last_login, is_active"
                    " FROM {} WHERE email = %s"
                ).format(sql.Identifier(_USERS_TABLE)),
                (email,),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


def get_user_by_id(user_id: str) -> Optional[User]:
    with _get_connection() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT id, name, email, password_hash, plan, created_at, last_login, is_active"
                    " FROM {} WHERE id = %s"
                ).format(sql.Identifier(_USERS_TABLE)),
                (user_id,),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_user(row)


def list_users(limit: Optional[int] = None) -> Iterable[User]:
    with _get_connection() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            if limit is None:
                cursor.execute(
                    sql.SQL(
                        "SELECT id, name, email, password_hash, plan, created_at, last_login, is_active"
                        " FROM {} ORDER BY created_at DESC"
                    ).format(sql.Identifier(_USERS_TABLE))
                )
            else:
                cursor.execute(
                    sql.SQL(
                        "SELECT id, name, email, password_hash, plan, created_at, last_login, is_active"
                        " FROM {} ORDER BY created_at DESC LIMIT %s"
                    ).format(sql.Identifier(_USERS_TABLE)),
                    (limit,),
                )
            rows = cursor.fetchall()
    return [_row_to_user(row) for row in rows]


def update_last_login(user_id: str) -> None:
    now = datetime.now(timezone.utc)
    with _get_connection() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("UPDATE {} SET last_login = %s WHERE id = %s").format(sql.Identifier(_USERS_TABLE)),
                (now, user_id),
            )


def ensure_admin_exists(name: str, email: str, password_hash: str, plan: str) -> User:
    existing = get_user_by_email(email)
    if existing:
        return existing
    try:
        return create_user(name, email, password_hash, plan)
    except UniqueViolation:
        return get_user_by_email(email)  # pragma: no cover

