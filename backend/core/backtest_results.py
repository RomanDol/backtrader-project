"""
Модуль для сохранения результатов бэктеста в PostgreSQL
"""
import os
import logging
import psycopg2
from typing import List, Dict, Any
from dotenv import load_dotenv
import json

load_dotenv()

logger = logging.getLogger(__name__)

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DATABASE', 'messages'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

class BacktestResultsManager:
    """Класс для управления результатами бэктестов"""
    
    def get_connection(self):
        """Создает подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def clear_results(self):
        """Очищает таблицу current_trades перед новым бэктестом"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("TRUNCATE TABLE current_trades RESTART IDENTITY")
                conn.commit()
            logger.info("🗑️ Таблица current_trades очищена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки таблицы: {e}")
            return False
    
    def save_trades(self, trades: List[Dict[str, Any]]):
        """
        Сохраняет результаты сделок в таблицу current_trades
        
        Args:
            trades: Список сделок с данными
        """
        if not trades:
            logger.warning("⚠️ Нет сделок для сохранения")
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for trade in trades:
                    cursor.execute("""
                        INSERT INTO current_trades (
                            entry_date, entry_price, entry_size, side,
                            exit_date, exit_price, pnl, pnl_percent,
                            commission, bars_held, trade_history
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        trade.get('entry_date'),
                        trade.get('entry_price'),
                        trade.get('entry_size'),
                        trade.get('side'),
                        trade.get('exit_date'),
                        trade.get('exit_price'),
                        trade.get('pnl'),
                        trade.get('pnl_percent'),
                        trade.get('commission'),
                        trade.get('bars_held'),
                        json.dumps(trade.get('trade_history'))
                    ))
                
                conn.commit()
                logger.info(f"✅ Сохранено {len(trades)} сделок в базу")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сделок: {e}")
            return False

# Создаем глобальный экземпляр
backtest_results_manager = BacktestResultsManager()
