import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    
    def clear_trades(self):
        """Очищает таблицу перед новым тестом"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM current_trades")
        self.conn.commit()
        cursor.close()
    
    def save_trade(self, trade_data):
        """Сохраняет одну сделку"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO current_trades 
            (entry_date, entry_price, entry_size, side,
             exit_date, exit_price, pnl, pnl_percent, 
             commission, bars_held, mae, mfe)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, trade_data)
        self.conn.commit()
        cursor.close()
    
    def close(self):
        """Закрывает соединение"""
        self.conn.close()