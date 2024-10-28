import argparse
import hashlib
import os
import time
import importlib
import textwrap
import sqlite3
from smah.database.database import Database

class Migration:
    # Migrations are stored in the `migrations` directory
    MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

    def __init__(self):
        pass


    @staticmethod
    def get_schema_migrations(database: Database):
        cursor = database.connection.cursor()
        create_table = textwrap.dedent(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations(
                migration VARCHAR(255) PRIMARY KEY, 
                checksum CHAR(32), 
                applied BOOLEAN DEFAULT FALSE, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ).strip()
        cursor.execute(create_table)

        cursor.execute("SELECT migration, checksum, applied, created_at, modified_at FROM schema_migrations ORDER BY migration ASC")
        result = cursor.fetchall()
        cursor.close()
        migrations = []
        for row in result:
            migration, checksum, applied, created_at, modified_at = row
            migrations.append(
                {
                    'migration': migration,
                    'checksum': checksum,
                    'applied': applied == 1,
                    'created_at': created_at,
                    'modified_at': modified_at
                }
            )
        return migrations

    @staticmethod
    def get_migrations():
        migrations = []
        os.makedirs(Migration.MIGRATIONS_DIR, exist_ok=True)
        for migration in os.listdir(Migration.MIGRATIONS_DIR):
            if migration.endswith(".py"):
                digest = hashlib.md5(open(os.path.join(Migration.MIGRATIONS_DIR, migration), "rb").read()).hexdigest()
                migrations.append({'file': migration, 'checksum': digest})
        return migrations

    @staticmethod
    def apply_migration(database: Database, migration: dict):
        cursor = database.connection.cursor()
        module = importlib.import_module(f"smah.database.migrations.{migration['file'][:-3]}")
        cursor.execute("BEGIN TRANSACTION")
        try:
            module.up(cursor)
            cursor.execute(
            """
                INSERT INTO schema_migrations (migration, checksum, applied) 
                VALUES (?, ?, ?)
                ON CONFLICT(migration) DO UPDATE SET
                    checksum = excluded.checksum,
                    applied = excluded.applied
                """,
                (migration['file'], migration['checksum'], True)
            )
            cursor.execute("COMMIT")
            cursor.close()
            print(f"Applied Migration {migration['file']}")
        except Exception as e:
            cursor.execute("ROLLBACK")
            cursor.close()
            print(f"Error Applying Migration {migration['file']}: {e}")
            exit(2)

    @staticmethod
    def rollback_migration(database: Database, migration: dict):
        cursor = database.connection.cursor()
        module = importlib.import_module(f"smah.database.migrations.{migration['file'][:-3]}")
        cursor.execute("BEGIN TRANSACTION")
        try:
            module.down(cursor)
            cursor.execute(
                """
                INSERT INTO schema_migrations (migration, checksum, applied) 
                VALUES (?, ?, ?)
                ON CONFLICT(migration) DO UPDATE SET
                    checksum = excluded.checksum,
                    applied = excluded.applied
                """,
                (migration['file'], migration['checksum'], False)
            )
            cursor.execute("COMMIT")
            cursor.close()
            print(f"Reverted Migration '{migration['file']}'")
        except Exception as e:
            cursor.execute("ROLLBACK")
            cursor.close()
            print(f"Error Reverting Migration '{migration['file']}': {e}")
            exit(2)

    @staticmethod
    def migrate(database: Database, args: argparse.Namespace):
        count = 0
        available_migrations = Migration.get_migrations()
        tracked_migrations = {m['migration']: m for m in Migration.get_schema_migrations(database)}

        for migration in available_migrations:
            # Skip migrations that have already been applied
            tracked = tracked_migrations.get(migration['file'])
            if tracked and tracked['applied']:
                if tracked['checksum'] != migration['checksum']:
                    print(f"Checksum Mismatch in {migration['file']}: expected {tracked['checksum']} but got {migration['checksum']}")
                    if args.reset_checksums:
                        cursor = database.connection.cursor()
                        cursor.execute("UPDATE schema_migrations SET checksum = ? WHERE migration = ?", (migration['checksum'], migration['file']))
                        cursor.close()
                    else:
                        exit(1)
                if args.to and args.to == migration['file']:
                    print(f"Migration Complete: changes applied {count}")
                    exit(0)
            else:
                Migration.apply_migration(database, migration)
                count += 1
                if args.count and count >= args.count:
                    print(f"Migration Complete: changes applied {count}")
                    exit(0)
                if args.to and args.to == migration['file']:
                    print(f"Migration Complete: changes applied {count}")
                    exit(0)
        if count == 0:
            print("No Migrations Pending")
        else:
            print(f"Migration Complete: changes applied {count}")

    @staticmethod
    def rollback(database: Database, args: argparse.Namespace):
        count = 0
        available_migrations = {m['file']: m for m in Migration.get_migrations()}
        tracked_migrations = [m for m in Migration.get_schema_migrations(database) if m['applied'] and m['migration'] in available_migrations]
        tracked_migrations.reverse()
        if args.to:
            # Verify to target is applied
            available = False
            for migration in tracked_migrations:
                if migration['migration'] == args.to:
                    available = True
                    break
            if not available:
                print(f"Migration --to '{args.to}' not applied or available")
                exit(1)
        for migration in tracked_migrations:
            Migration.rollback_migration(database, available_migrations[migration['migration']])
            count += 1
            if args.count and count >= args.count:
                print(f"Rollback Complete: changes applied {count}")
                exit(0)
            if args.to and args.to == migration['migration']:
                print(f"Rollback Complete: changes applied {count}")
                exit(0)
        if count == 0:
            print("No Migrations Available for Rollback")
        else:
            print(f"Rollback Complete #{count} migrations reverted.")

    @staticmethod
    def status(database: Database):
        available_migrations = Migration.get_migrations()
        tracked_migrations = {m['migration']: m for m in Migration.get_schema_migrations(database)}
        if not available_migrations:
            print("No Migrations Available")
            exit(0)
        out = ""
        for migration in available_migrations:
            migration['applied'] = False
            migration['checksum_mismatch'] = False
            tracked = tracked_migrations.get(migration['file'])
            if tracked:
                migration['applied'] = tracked['applied']
                if tracked['checksum'] != migration['checksum']:
                    migration['checksum_mismatch'] = True
            out += f"{migration['file']} {'(applied)' if migration['applied'] else ''} {'(checksum mismatch)' if migration['checksum_mismatch'] else ''}\n"
        print(f"Migrations:\n{out}")

    @staticmethod
    def create(name: str) -> None:
        epoch = int(time.time())
        template = textwrap.dedent(
            """
            def up(cursor):
                \"\"\"
                Apply schema.
                \"\"\"
                pass
                
            def down(cursor):
                \"\"\"
                Rollback schema.
                \"\"\"
                pass    
         
            """).strip()
        mf = os.path.join(Migration.MIGRATIONS_DIR, f"{epoch}_{name}.py")
        os.makedirs(Migration.MIGRATIONS_DIR, exist_ok=True)
        with open(mf, "w") as file:
            file.write(template)
        print(f"Created migration: {mf}")

