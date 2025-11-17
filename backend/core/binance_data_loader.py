"""
Модуль для загрузки исторических данных с Binance Data
"""
import requests
import zipfile
import io
import csv
import psycopg2
import logging
import os
from datetime import datetime, timedelta
from typing import Tuple, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DATABASE', 'backtrader'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

class BinanceDataLoader:
    """Класс для загрузки исторических данных с Binance"""
    
    def __init__(self):
        self.base_url = "https://data.binance.vision/data/futures/um"
    
    def get_connection(self):
        """Создает подключение к PostgreSQL"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def download_and_parse_zip(self, url: str) -> Tuple[bool, List[List]]:
        """
        Скачивает ZIP архив и парсит CSV данные
        
        Args:
            url: URL для скачивания
            
        Returns:
            Tuple[bool, List[List]]: (успех, список строк данных)
        """
        try:
            logger.info(f"📥 Скачивание: {url}")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 404:
                logger.warning(f"⚠️ Данные не найдены: {url}")
                return False, []
            
            if response.status_code != 200:
                logger.error(f"❌ Ошибка скачивания: HTTP {response.status_code}")
                return False, []
            
            # Распаковываем ZIP
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            csv_filename = zip_file.namelist()[0]
            
            # Читаем CSV
            with zip_file.open(csv_filename) as csv_file:
                csv_content = csv_file.read().decode('utf-8')
                csv_reader = csv.reader(io.StringIO(csv_content))
                data_rows = list(csv_reader)
            
            logger.info(f"✅ Получено {len(data_rows)} строк")
            return True, data_rows
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки ZIP: {e}")
            return False, []
    
    def save_to_database(self, symbol: str, timeframe: str, data_rows: List[List]) -> Tuple[bool, int, int]:
        """
        Сохраняет данные в таблицу candles
        
        Args:
            symbol: Символ (например BTCUSDT)
            timeframe: Таймфрейм (например 1d)
            data_rows: Список строк данных из CSV
            
        Returns:
            Tuple[bool, int, int]: (успех, количество новых записей, количество пропущенных дубликатов)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                inserted = 0
                duplicates = 0
                
                for idx, row in enumerate(data_rows):
                    # Пропускаем заголовок если он есть
                    if idx == 0 and row[0] == 'open_time':
                        continue
                    
                    try:
                        # Формат Binance CSV:
                        # [0] open_time, [1] open, [2] high, [3] low, [4] close, [5] volume, ...
                        timestamp = int(row[0])
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        
                        cursor.execute("""
                            INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, timeframe, time) DO NOTHING
                            RETURNING time
                        """, (
                            dt,
                            symbol,
                            timeframe,
                            float(row[1]),  # open
                            float(row[2]),  # high
                            float(row[3]),  # low
                            float(row[4]),  # close
                            float(row[5])   # volume
                        ))
                        
                        if cursor.fetchone():
                            inserted += 1
                        else:
                            duplicates += 1
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка сохранения строки {idx}: {e}")
                        continue
                
                conn.commit()
                logger.info(f"💾 Сохранено: {inserted} новых, {duplicates} дубликатов")
                return True, inserted, duplicates
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в БД: {e}")
            return False, 0, 0
    
    def generate_date_range(self, start_date: str, end_date: str, period: str) -> List[str]:
        """
        Генерирует список дат для загрузки
        
        Args:
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата конца (YYYY-MM-DD)
            period: 'daily' или 'monthly'
            
        Returns:
            List[str]: Список дат в нужном формате
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current = start
        
        if period == 'daily':
            while current <= end:
                dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        else:  # monthly
            while current <= end:
                dates.append(current.strftime('%Y-%m'))
                # Переходим к следующему месяцу
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        
        return dates
    
    def download_historical_data(self, symbol: str, timeframe: str, period: str, 
                                 start_date: str, end_date: str) -> Tuple[bool, str, dict]:
        """
        Основная функция загрузки исторических данных
        
        Args:
            symbol: Символ
            timeframe: Таймфрейм
            period: 'daily' или 'monthly'
            start_date: Дата начала
            end_date: Дата конца
            
        Returns:
            Tuple[bool, str, dict]: (успех, сообщение, статистика)
        """
        try:
            logger.info(f"🔄 Начало загрузки {symbol} {timeframe} ({period}): {start_date} - {end_date}")
            
            # Генерируем список дат
            dates = self.generate_date_range(start_date, end_date, period)
            logger.info(f"📅 Найдено {len(dates)} периодов для загрузки")
            
            total_inserted = 0
            total_duplicates = 0
            successful_downloads = 0
            failed_downloads = 0
            
            # Загружаем данные для каждой даты
            for date in dates:
                # Формируем URL
                period_type = 'daily' if period == 'daily' else 'monthly'
                url = f"{self.base_url}/{period_type}/klines/{symbol}/{timeframe}/{symbol}-{timeframe}-{date}.zip"
                
                # Скачиваем и парсим
                success, data_rows = self.download_and_parse_zip(url)
                
                if success and data_rows:
                    # Сохраняем в БД
                    success, inserted, duplicates = self.save_to_database(symbol, timeframe, data_rows)
                    if success:
                        total_inserted += inserted
                        total_duplicates += duplicates
                        successful_downloads += 1
                    else:
                        failed_downloads += 1
                else:
                    failed_downloads += 1
            
            # Формируем итоговое сообщение
            stats = {
                'total_periods': len(dates),
                'successful': successful_downloads,
                'failed': failed_downloads,
                'inserted': total_inserted,
                'duplicates': total_duplicates
            }
            
            message = f"Загрузка завершена: {successful_downloads}/{len(dates)} периодов, добавлено {total_inserted} свечей"
            logger.info(f"✅ {message}")
            
            return True, message, stats
            
        except Exception as e:
            error_msg = f"Критическая ошибка загрузки: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return False, error_msg, {}

# Создаем глобальный экземпляр
binance_data_loader = BinanceDataLoader()