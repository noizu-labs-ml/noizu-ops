import argparse
import json
import sqlite3
import os
from typing import Optional


class Database:
    DEFAULT_DATABASE = os.path.expanduser("~/.smah/smah.db")

    @staticmethod
    def default_database() -> str:
        return Database.DEFAULT_DATABASE

    @staticmethod
    def args_to_dict(args: argparse.Namespace) -> dict:
        return vars(args)

    def __init__(self, args):
        file = args.database or self.default_database()
        if not os.path.exists(file):
            os.makedirs(os.path.dirname(file), exist_ok=True)
        self.connection: sqlite3.Connection = sqlite3.connect(file)

    def last_session(self):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting = ?
            """,
            ("last_session",)
        )
        result = cursor.fetchone()
        cursor.close()
        if result:
            (session_id,) = result[0]
            session_id = int(session_id)
            return self.session(session_id)
        return None

    def session(self, session_id: int):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT chat_history.id, chat_history.title, chat_history.created_on, chat_history.modified_on, chat_history_details.args, chat_history_details.plan, chat_history_details.pipe_input
            FROM chat_history
            JOIN chat_history_details
            ON chat_history.id = chat_history_details.chat_history_id
            WHERE chat_history.id = ?
            """,
            (session_id,)
        )
        result = cursor.fetchone()

        # get chat_history_messages
        mr = cursor.execute(
            """
            SELECT message
            FROM chat_history_message
            WHERE chat_history_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        ).fetchall()
        messages = []
        for row in mr:
            (row,) = row
            messages.append(json.loads(row))
        cursor.close()
        if result:
            id, title, created_on, modified_on, args, plan, pipe = result
            return {
                "id": id,
                "title": title,
                "created_on": created_on,
                "modified_on": modified_on,
                "args": json.loads(args),
                "plan": json.loads(plan),
                "pipe": pipe,
                "messages": messages
            }
        return None

    def history(self, limit: int = 10):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT chat_history.id, chat_history.title, chat_history.created_on, chat_history.modified_on
            FROM chat_history
            ORDER BY created_on DESC
            LIMIT ?
            """,
            (limit,)
        )
        result = cursor.fetchall()
        cursor.close()
        response = []
        for row in result:
            id, title, created_on, modified_on = row
            response.append({
                "id": id,
                "title": title,
                "created_on": created_on,
                "modified_on": modified_on
            })
        response.reverse()
        return response

    def append_to_chat(self, session_id: int, messages: list) -> None:
        cursor = self.connection.cursor()
        cursor.execute("BEGIN TRANSACTION")
        for message in messages:
            cursor.execute(
                """
                INSERT INTO chat_history_message (chat_history_id, message)
                VALUES (?, ?)
                """,
                (session_id, json.dumps(message))
            )
        cursor.execute("COMMIT")
        cursor.close()

    def save_chat(self, title: str, args: argparse.Namespace, plan: dict, messages: list, pipe: Optional[str] = None) -> None:
        cursor = self.connection.cursor()

        cursor.execute("BEGIN TRANSACTION")
        # Insert into chat_history
        cursor.execute(
            """
            INSERT INTO chat_history (title)
            VALUES (?)
            """, (title,)
        )
        chat_history_id = cursor.lastrowid

        # Insert into chat_history_details
        cursor.execute(
            """
            INSERT INTO chat_history_details (chat_history_id, args, plan, pipe_input)
            VALUES (?, ?, ?, ?)
            """, (chat_history_id, json.dumps(self.args_to_dict(args)), json.dumps(plan), pipe)
        )

        # Insert into chat_history_message
        for message in messages:
            cursor.execute(
                """
                INSERT INTO chat_history_message (chat_history_id, message)
                VALUES (?, ?)
                """, (chat_history_id, json.dumps(message))
            )

        cursor.execute(
            """
            INSERT INTO settings (setting, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting) DO UPDATE SET
                setting_value = excluded.setting_value
            """,
            ("last_session", f"{chat_history_id}")
        )

        # Commit the transaction
        cursor.execute("COMMIT")
        cursor.close()

