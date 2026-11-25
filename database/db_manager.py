"""SQLite database manager for HealthTrack.

Handles connection creation, foreign-key enforcement, schema setup,
and safe, user-scoped helper methods so each user can only access
their own health records.
"""

from pathlib import Path
import sqlite3
from typing import Any, Iterable, Optional

# Default database location inside HealthTrack/data/healthtrack.db
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "healthtrack.db"

# Allowlist of health record tables to prevent invalid table names in dynamic queries
HEALTH_TABLES = frozenset(
    {
        "weight_logs",
        "blood_pressure_logs",
        "heart_rate_logs",
        "activity_logs",
    }
)


class DatabaseError(Exception):
    """Custom exception raised when a database operation fails."""


class DatabaseManager:
    """Manages SQLite connections, schema initialization, and safe queries."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        """Store the database path, ensure parent folder exists, and set up tables."""
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Open a new SQLite connection with foreign keys and dict-like rows enabled."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # SQLite requires enabling foreign keys per connection
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not connect to database: {exc}") from exc

    def initialize_database(self) -> None:
        """Create all required tables and indexes if they do not already exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            height_cm REAL,
            target_weight_kg REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            bmi REAL,
            recorded_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS blood_pressure_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            systolic INTEGER NOT NULL,
            diastolic INTEGER NOT NULL,
            recorded_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS heart_rate_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bpm INTEGER NOT NULL,
            recorded_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            steps INTEGER NOT NULL DEFAULT 0,
            active_minutes INTEGER NOT NULL DEFAULT 0,
            sleep_hours REAL NOT NULL DEFAULT 0.0,
            calories_burned INTEGER NOT NULL DEFAULT 0,
            recorded_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_weight_user_date
            ON weight_logs (user_id, recorded_date);
        CREATE INDEX IF NOT EXISTS idx_bp_user_date
            ON blood_pressure_logs (user_id, recorded_date);
        CREATE INDEX IF NOT EXISTS idx_hr_user_date
            ON heart_rate_logs (user_id, recorded_date);
        CREATE INDEX IF NOT EXISTS idx_activity_user_date
            ON activity_logs (user_id, recorded_date);
        """
        conn = self.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Failed to initialize database schema: {exc}") from exc
        finally:
            conn.close()

    def execute_write(self, query: str, params: Iterable[Any] = ()) -> int:
        """Execute an INSERT, UPDATE, or DELETE statement and return lastrowid."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, tuple(params))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            conn.rollback()
            raise
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database write failed: {exc}") from exc
        finally:
            conn.close()

    def execute_update(self, query: str, params: Iterable[Any] = ()) -> int:
        """Execute an UPDATE or DELETE statement and return affected row count."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseError(f"Database update failed: {exc}") from exc
        finally:
            conn.close()

    def fetch_one(self, query: str, params: Iterable[Any] = ()) -> Optional[dict]:
        """Fetch a single row as a dictionary, or None if not found."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row is not None else None
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database query failed: {exc}") from exc
        finally:
            conn.close()

    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[dict]:
        """Fetch all matching rows as a list of dictionaries."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database query failed: {exc}") from exc
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # User-Isolated Health Record Helpers
    # -----------------------------------------------------------------------

    def _validate_health_table(self, table_name: str) -> None:
        """Ensure only recognized health tables can be queried dynamically."""
        if table_name not in HEALTH_TABLES:
            raise ValueError(f"Invalid health table name: {table_name}")

    def fetch_user_records(
        self,
        table_name: str,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Return records belonging strictly to the given user_id."""
        self._validate_health_table(table_name)

        conditions = ["user_id = ?"]
        params: list[Any] = [user_id]

        if start_date:
            conditions.append("recorded_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("recorded_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        query = (
            f"SELECT * FROM {table_name} "
            f"WHERE {where_clause} "
            f"ORDER BY recorded_date DESC, id DESC"
        )

        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(int(limit))

        return self.fetch_all(query, params)

    def delete_user_record(self, table_name: str, record_id: int, user_id: int) -> bool:
        """Delete a single record only if it belongs to the given user_id."""
        self._validate_health_table(table_name)
        query = f"DELETE FROM {table_name} WHERE id = ? AND user_id = ?"
        deleted_rows = self.execute_update(query, (record_id, user_id))
        return deleted_rows > 0
