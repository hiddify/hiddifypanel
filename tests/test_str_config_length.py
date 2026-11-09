import unittest
from unittest import mock

from sqlalchemy.dialects import mysql, sqlite

from hiddifypanel.models import StrConfig
from hiddifypanel.panel import init_db


class StrConfigLengthTests(unittest.TestCase):
    """Settings longer than 3072 characters (e.g. the spare REALITY SNIs after a scan) are stored on MySQL/MariaDB."""

    def test_value_column_is_text(self):
        # MariaDB in strict mode rejects a value longer than a VARCHAR column ("Data too long", error 1406).
        self.assertEqual(StrConfig.value.type.compile(dialect=mysql.dialect()), "TEXT")
        self.assertEqual(StrConfig.value.type.compile(dialect=sqlite.dialect()), "TEXT")

    def test_existing_databases_are_altered_once(self):
        self.assertGreaterEqual(init_db.latest_db_version(), 200)
        with mock.patch.object(init_db, "db", mock.Mock(engine=mock.Mock(dialect=mysql.dialect()))), mock.patch.object(init_db, "db_execute") as db_execute:
            init_db._v200(1)  # a virtual child shares the table: nothing to do
            db_execute.assert_not_called()
            init_db._v200(0)
        db_execute.assert_called_once_with("ALTER TABLE str_config MODIFY COLUMN value TEXT", commit=True)


if __name__ == "__main__":
    unittest.main()
