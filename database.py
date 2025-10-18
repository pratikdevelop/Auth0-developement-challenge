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
        
        conn.commit()
        conn.close()
    
    def create_chat(self, title="New Chat"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO chats (title) VALUES (?)', (title,))
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chat_id
    
    def get_all_chats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM chats ORDER BY created_at DESC')
        chats = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return chats
    
    def get_chat_messages(self, chat_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC',
            (chat_id,)
        )
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return messages
    
    def add_message(self, chat_id, role, content):
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
    
    def delete_chat(self, chat_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE chat_id = ?', (chat_id,))
        cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
        conn.commit()
        conn.close()
