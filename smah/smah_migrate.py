from smah.database import Database, Migration
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Migration tool for managing database migrations.")

    # Create subparsers for each command (migrate, rollback, status)
    subparsers = parser.add_subparsers(dest="command", help="Migration commands")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Apply migrations")
    migrate_parser.add_argument("--to", type=str, help="Migrate up to a specific migration name")
    migrate_parser.add_argument("--count", type=int, help="Apply a specified number of migrations")
    migrate_parser.add_argument("--reset-checksums",
                                action=argparse.BooleanOptionalAction,
                                help="Reset migration checksums on mismatch",
                                default=False)

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_parser.add_argument("--to", type=str, help="Rollback to a specific migration name")
    rollback_parser.add_argument("--count", type=int, help="Rollback a specified number of migrations")
    rollback_parser.add_argument("--reset-checksums",
                                action=argparse.BooleanOptionalAction,
                                help="Reset migration checksums on mismatch",
                                default=False)


    # Status command
    subparsers.add_parser("status", help="Show the current migration status")

    # Status command
    create_migration_parser = subparsers.add_parser("create", help="Show the current migration status")
    create_migration_parser.add_argument(dest="name", type=str, help="Name of the migration")

    # database argument
    parser.add_argument("--database", type=str, help="Path to the database file")

    return parser.parse_args()

def main():
    args = parse_arguments()
    database = Database(args)

    if args.command == "migrate":
        Migration.migrate(database, args)
    elif args.command == "rollback":
        Migration.rollback(database, args)
    elif args.command == "status":
        Migration.status(database)
    elif args.command == "create":
        Migration.create(args.name)



if __name__ == "__main__":
    main()