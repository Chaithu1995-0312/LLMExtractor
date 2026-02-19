import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from .adapter import DBAdapter

_pool = None


def init_pool():
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not set")

        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url
        )


def get_adapter():
    if _pool is None:
        init_pool()
    return PostgresAdapter(_pool)


class PostgresAdapter(DBAdapter):

    def __init__(self, pool: SimpleConnectionPool):
        self.pool = pool

    def _get_conn(self):
        return self.pool.getconn()

    def _put_conn(self, conn):
        self.pool.putconn(conn)

    def execute(self, query: str, params: tuple = None):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
            conn.commit()
        finally:
            self._put_conn(conn)

    def fetch_one(self, query: str, params: tuple = None):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                result = cur.fetchone()
            return result
        finally:
            self._put_conn(conn)

    def fetch_all(self, query: str, params: tuple = None):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                result = cur.fetchall()
            return result
        finally:
            self._put_conn(conn)

    @contextmanager
    def transaction(self):
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    yield cur
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn(conn)
