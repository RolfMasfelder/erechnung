"""
pgTAP Database Tests — direkt in der PostgreSQL-Datenbank ausgeführt.

Zwei Testklassen:
  PgTAPSchemaTests        — Struktur-/Schema-Tests (keine Testdaten nötig)
  PgTAPBusinessLogicTests — Daten-Integritäts-Tests (benötigen generate_test_data)

Die SQL-Dateien liegen in postgres/tests/ und können auch direkt via psql
ausgeführt werden:
  psql -U postgres -d erechnung_db -f postgres/tests/01_schema.sql

pgTAP-Ausgabe: TAP-Format (Test Anything Protocol)
  ok 1 - Beschreibung    → Test bestanden
  not ok 2 - Beschreibung → Test fehlgeschlagen
"""

import os
import re

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase, tag


# Pfad zum postgres/tests/-Verzeichnis (relativ zum Projektroot)
PGTAP_TESTS_DIR = os.path.join(
    os.path.dirname(__file__),  # /app/project_root/invoice_app/tests/
    "..",
    "..",
    "..",  # → /app/
    "postgres",
    "tests",
)
PGTAP_TESTS_DIR = os.path.normpath(PGTAP_TESTS_DIR)


def _load_sql(filename: str) -> str:
    """Lädt eine SQL-Datei aus dem postgres/tests/-Verzeichnis."""
    path = os.path.join(PGTAP_TESTS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _run_pgtap_sql(sql: str) -> list[str]:
    """
    Führt pgTAP-SQL-Statements aus und gibt alle TAP-Ausgabezeilen zurück.

    Wichtig: BEGIN und ROLLBACK werden entfernt, da Django die Tests
    selbst in eine Transaktion einbettet und am Ende per Rollback aufräumt.
    """
    # Kommentare entfernen, dann in Einzelstatements splitten
    sql_no_comments = re.sub(r"--[^\n]*", "", sql)
    statements = [s.strip() for s in sql_no_comments.split(";")]

    # BEGIN / ROLLBACK / COMMIT überspringen — Django kontrolliert die Transaktion
    skip_patterns = {"BEGIN", "ROLLBACK", "COMMIT"}

    tap_lines = []
    with connection.cursor() as cursor:
        for stmt in statements:
            if not stmt or stmt.upper() in skip_patterns:
                continue
            cursor.execute(stmt)
            if cursor.description:
                rows = cursor.fetchall()
                for row in rows:
                    if row[0] is not None:
                        tap_lines.append(str(row[0]))

    return tap_lines


def _ensure_extensions() -> None:
    """Installiert pgTAP und weitere Extensions in der Test-DB.

    Nötig weil Django eine frische Test-DB erstellt ohne das init-extensions.sql
    auszuführen, das nur beim ersten Start der Produktions-DB läuft.

    Raises SkipTest if pgtap is not available on the system.
    """
    from unittest import SkipTest

    from django.db import utils as db_utils

    with connection.cursor() as cursor:
        # Check pgtap availability first.
        # TestCase wraps in a transaction (savepoint needed), but
        # TransactionTestCase uses autocommit (no active transaction block).
        in_transaction = not connection.get_autocommit()

        if in_transaction:
            cursor.execute("SAVEPOINT _pgtap_check")

        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgtap")
        except (db_utils.ProgrammingError, db_utils.NotSupportedError, db_utils.OperationalError):
            if in_transaction:
                cursor.execute("ROLLBACK TO SAVEPOINT _pgtap_check")
            raise SkipTest("pgtap extension not available on this PostgreSQL server") from None
        else:
            if in_transaction:
                cursor.execute("RELEASE SAVEPOINT _pgtap_check")

        # Other extensions — these ship with standard PostgreSQL
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")


def _assert_all_passed(test_case: TestCase, tap_lines: list[str], sql_file: str) -> None:
    """Prüft TAP-Output auf Fehler und schlägt den Test mit Details fehl."""
    failures = [line for line in tap_lines if line.startswith("not ok")]
    if failures:
        failure_detail = "\n".join(failures)
        test_case.fail(
            f"pgTAP-Tests in '{sql_file}' fehlgeschlagen:\n\n{failure_detail}\n\n"
            f"Vollständiger TAP-Output:\n" + "\n".join(tap_lines)
        )


# ============================================================
# Testklasse 1: Schema-Tests (keine Testdaten erforderlich)
# ============================================================


@tag("pgtap")
class PgTAPSchemaTests(TestCase):
    """
    Prüft die Datenbankstruktur: Tabellen, Spalten, PKs, FKs,
    UNIQUE-Constraints, Datentypen und installierte Extensions.

    Diese Tests schlagen fehl wenn:
    - Migrationen nicht vollständig ausgeführt wurden
    - pgTAP oder eine andere Extension fehlt
    - Ein Tabellenname durch Umbenennen eines Django-Modells geändert wurde
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_extensions()

    def test_schema_structure(self):
        """Alle Tabellen, Spalten und Constraints sind korrekt definiert."""
        sql = _load_sql("01_schema.sql")
        tap_lines = _run_pgtap_sql(sql)

        self.assertTrue(
            any("ok" in line for line in tap_lines),
            "pgTAP hat keine Ausgabe produziert — Extension installiert?",
        )
        _assert_all_passed(self, tap_lines, "01_schema.sql")


# ============================================================
# Testklasse 2: Business-Logic-Tests (benötigen Testdaten)
# ============================================================


@tag("pgtap")
class PgTAPBusinessLogicTests(TransactionTestCase):
    """
    Prüft Daten-Integrität und Business-Logik direkt in der Datenbank.

    Verwendet TransactionTestCase weil generate_test_data außerhalb einer
    Django-Testanweisung Daten persistent schreiben muss, damit die
    pgTAP-Abfragen sie sehen können.

    Diese Tests schlagen fehl wenn:
    - Status-/Typ-Felder ungültige Werte enthalten
    - Beträge negativ sind
    - Referentielle Integrität verletzt ist
    - invoice_number-Format nicht dem Regex entspricht
    - Duplikate in UNIQUE-Feldern existieren
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_extensions()
        # Testdaten anlegen (minimal preset = 5 invoices, kurze Laufzeit)
        call_command("generate_test_data", "--preset", "minimal", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        # Testdaten direkt via ORM löschen — generate_test_data --clear würde
        # anschließend auch neue Daten anlegen und dabei nach
        # Country 'DE' suchen, die in der Test-DB nicht existiert.
        from invoice_app.models import BusinessPartner, Company, Invoice, InvoiceLine, Product

        InvoiceLine.objects.all().delete()
        Invoice.objects.all().delete()
        Product.objects.all().delete()
        BusinessPartner.objects.all().delete()
        Company.objects.all().delete()
        super().tearDownClass()

    def test_business_logic_and_data_integrity(self):
        """Status-Werte, Beträge, Referenzen und Formate sind konsistent."""
        sql = _load_sql("02_business_logic.sql")
        tap_lines = _run_pgtap_sql(sql)

        self.assertTrue(
            any("ok" in line for line in tap_lines),
            "pgTAP hat keine Ausgabe produziert — Testdaten vorhanden?",
        )
        _assert_all_passed(self, tap_lines, "02_business_logic.sql")
