def up(cursor):
    """
    Apply schema.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history_details(
            chat_history_id INTEGER PRIMARY KEY,
            args JSON,
            plan JSON,
            pipe_input TEXT DEFAULT NULL,
            FOREIGN KEY(chat_history_id) REFERENCES chat_history(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history_message(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_history_id INTEGER,
            message JSON,
            created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_history_id) REFERENCES chat_history(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings(
            setting VARCHAR(32) PRIMARY KEY,
            setting_value VARCHAR(255)
        )
        """
    )


def down(cursor):
    """
    Rollback schema.
    """
    cursor.execute("DROP TABLE settings")
    cursor.execute("DROP TABLE chat_history_details")
    cursor.execute("DROP TABLE chat_history_message")
    cursor.execute("DROP TABLE chat_history")