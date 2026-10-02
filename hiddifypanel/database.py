# from sqlalchemy_utils import UUIDType
import os

# class SQLAlchemy:
#     def __init__(self):
#         self.engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))
#         self.session_maker = sessionmaker(bind=self.engine)
#         self.session=self.session_maker()
#         @as_declarative()
#         class Base:
#             @declared_attr
#             def __tablename__(cls):
#                 return cls.__name__.lower()
#             @classmethod
#             @property
#             def query(cls):
#                 return self.session.query(cls)
#         self.Query=sa_orm.Query
#         self.Model=Base
#         self.Table=sa.Table
#         self.Column=sa.Column
#         self.Integer=sa.Integer
#         self.ForeignKey=sa.ForeignKey
# def _set_rel_query(self, kwargs) -> None:
#         """Apply the extension's :attr:`Query` class as the default for relationships
#         and backrefs.
#         :meta private:
#         """
#         kwargs.setdefault("query_class", self.Query)
#         if "backref" in kwargs:
#             backref = kwargs["backref"]
#             if isinstance(backref, str):
#                 backref = (backref, {})
#             backref[1].setdefault("query_class", self.Query)
# def relationship(
#         self, *args, **kwargs
#     ) :
#         self._set_rel_query(kwargs)
#         return sa_orm.relationship(*args, **kwargs)
from flask_sqlalchemy import SQLAlchemy
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

db = SQLAlchemy()


# db.UUID = UUIDType  # type: ignore


def _engine_options(uri: str | None) -> dict:
    """READ COMMITTED on MySQL/MariaDB.

    Under the default REPEATABLE READ, MariaDB >= 11.6 (innodb_snapshot_isolation=ON) fails a
    write to a row another transaction changed after this one started with error 1020
    "Record has changed since last read" (e.g. two requests of one admin updating
    admin_user.last_online, or a node sync rewriting users). The panel's requests are short and
    do not rely on repeatable reads, so each statement seeing the latest committed data is right.
    """
    if (uri or "").startswith(("mysql", "mariadb")):
        return {"isolation_level": "READ COMMITTED"}
    return {}


def init_no_flask():
    uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    engine = create_engine(uri, **_engine_options(uri))
    db.session = sessionmaker(bind=engine)()


def init_app(app):

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {**_engine_options(app.config.get("SQLALCHEMY_DATABASE_URI")), **(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})}
    db.init_app(app)
    with app.app_context():
        from hiddifypanel.panel.init_db import init_db

        init_db()


def db_execute(query: str, return_val: bool = False, commit: bool = False, **params):
    # print(params)
    q = db.session.execute(text(query), params)
    if commit:
        db.session.commit()
    if return_val:
        return q.fetchall()

    # with db.engine.connect() as connection:
    #     res = connection.execute(text(query), params)
    #     connection.commit()s
    # return res


def db_execute_ddl(
    query: str,
    *,
    max_attempts: int = 12,
    wait_seconds: float = 5.0,
    lock_wait_timeout: int = 5,
) -> None:
    """Run DDL on a dedicated connection (avoids blocking on the Flask session pool)."""
    import time

    last_err: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        conn = db.engine.connect()
        try:
            conn.execute(text(f"SET SESSION lock_wait_timeout = {int(lock_wait_timeout)}"))
            conn.execute(text(query))
            conn.commit()
            return
        except BaseException as exc:
            last_err = exc
            conn.rollback()
            logger.warning("DDL attempt {}/{} failed: {}", attempt, max_attempts, exc)
            if attempt < max_attempts:
                time.sleep(wait_seconds)
        finally:
            conn.close()
    if last_err is not None:
        raise last_err
