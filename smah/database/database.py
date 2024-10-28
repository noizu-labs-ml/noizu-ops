import sqlite3
import os

class Database:
    DEFAULT_DATABASE = os.path.expanduser("~/.smah/smah.db")

    @staticmethod
    def default_database() -> str:
        return Database.DEFAULT_DATABASE

    def __init__(self, args):
        file = args.database or self.default_database()
        if not os.path.exists(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)
        self.connection: sqlite3.Connection = sqlite3.connect(file)



