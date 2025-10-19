import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name='chat_history.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("PRAGMA table_info(chats)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'user_id' not in columns:
            cursor.execute('ALTER TABLE chats ADD COLUMN user_id TEXT DEFAULT "default_user"')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats (id)
            )
        ''')
        
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id)')
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
    
    def create_chat(self, user_id, title="New Chat"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO chats (user_id, title) VALUES (?, ?)', (user_id, title))
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chat_id
    
    def get_all_chats(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM chats WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        chats = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return chats
    
    def get_chat_owner(self, chat_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM chats WHERE id = ?', (chat_id,))
        result = cursor.fetchone()
        conn.close()
        return result['user_id'] if result else None
    
    def get_chat_messages(self, chat_id, user_id):
        if self.get_chat_owner(chat_id) != user_id:
            return []
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC',
            (chat_id,)
        )
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages
    
    def add_message(self, chat_id, role, content, user_id):
        if self.get_chat_owner(chat_id) != user_id:
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)',
            (chat_id, role, content)
        )
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return message_id
    
    def delete_chat(self, chat_id, user_id):
        if self.get_chat_owner(chat_id) != user_id:
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
        cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
        conn.commit()
        conn.close()
        return True
