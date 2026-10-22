import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "E_learning.settings")
django.setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

recorder = MigrationRecorder(connection)
applied = set(recorder.applied_migrations())

from django.db.migrations.loader import MigrationLoader

loader = MigrationLoader(connection, ignore_no_migrations=True)
on_disk = {(app, name) for app, name in loader.disk_migrations}

print("APPLIED BUT NOT ON DISK (stale rows):")
for item in sorted(applied - on_disk):
    print("   ", item)
if not (applied - on_disk):
    print("    (none)")

print("ON DISK BUT NOT APPLIED (pending):")
for item in sorted(on_disk - applied):
    print("   ", item)
if not (on_disk - applied):
    print("    (none)")

print("DATABASES:", connection.settings_dict["NAME"])
with connection.cursor() as c:
    c.execute(
        "select datname from pg_database where datname like 'test_%' or datname like '%elearning%'"
    )
    print("PG DATABASES:", [r[0] for r in c.fetchall()])

    c.execute(
        "select app, name from django_migrations where app in "
        "('accounts','courses','payments','core') order by app, name"
    )
    print("MIGRATION ROWS:")
    for row in c.fetchall():
        print("   ", row)
