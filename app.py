from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import pandas as pd
# from strategy import run_backtest
from backend.core.binance_symbols import binance_symbols_manager
from backend.core.binance_data_loader import binance_data_loader
from auth import auth_manager



app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

CORS(app)

# Папка для загрузки файлов
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

@app.before_request
def auth_middleware():
    """Проверка авторизации для всех запросов"""
    return auth_manager.require_auth()
    
@app.context_processor
def inject_grafana():
    dashboards_str = os.getenv('DASHBOARDS', '{}')
    return {'dashboards': json.loads(dashboards_str)}

@app.route('/')
def index():
    """Главная страница"""
    return render_template('backtest.html')


@app.route('/tools')
def tools():
    """Страница инструментов"""
    return render_template('tools.html')

@app.route('/backtest')
def backtest_page():
    """Страница тестирования стратегий"""
    return render_template('backtest.html')


@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """API для получения списка доступных стратегий"""
    try:
        from strategies import get_strategies_list
        strategies = get_strategies_list()
        
        return jsonify({
            'success': True,
            'strategies': strategies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/api/get_trades', methods=['GET'])
def get_trades():
    """Получение сделок из последнего бэктеста"""
    try:
        import psycopg2
        
        DB_CONFIG = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DATABASE', 'backtrader'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                EXTRACT(EPOCH FROM entry_date) as entry_time,
                EXTRACT(EPOCH FROM exit_date) as exit_time,
                entry_price,
                exit_price,
                side,
                pnl
            FROM current_trades
            ORDER BY entry_date ASC
        """)
        
        rows = cursor.fetchall()
        
        trades = []
        for row in rows:
            trades.append({
                'entry_time': int(row[0]),
                'exit_time': int(row[1]),
                'entry_price': float(row[2]),
                'exit_price': float(row[3]),
                'side': row[4],
                'pnl': float(row[5])
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'trades': trades
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/backtest', methods=['POST'])
def backtest():
    """API для запуска бэктеста"""
    try:
        from backend.core.backtest_runner import backtest_runner
        
        data = request.json
        
        # Получение параметров
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        strategy_module = data.get('strategy_module')
        strategy_class = data.get('strategy_class')
        initial_cash = float(data.get('initial_cash', 10000))
        commission = float(data.get('commission', 0.001)) / 100  # Переводим из % в доли
        
        # Параметры стратегии
        strategy_params = data.get('strategy_params', {})
        print(f"=== DEBUG APP.PY ===")
        print(f"strategy_params: {strategy_params}")
        print(f"sar_timeframe в params: {strategy_params.get('sar_timeframe')}")
        print(f"=== END DEBUG ===")
        
        # Валидация обязательных полей
        if not all([symbol, timeframe, start_date, end_date, strategy_module, strategy_class]):
            return jsonify({
                'success': False,
                'error': 'Не все обязательные поля заполнены'
            }), 400
        
        # Запуск бэктеста
        result = backtest_runner.run_backtest(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            strategy_module=strategy_module,
            strategy_class=strategy_class,
            strategy_params=strategy_params,
            initial_cash=initial_cash,
            commission=commission
        )
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API для загрузки CSV файла с данными"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
        
        if file and file.filename.endswith('.csv'):
            filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Проверка формата файла
            df = pd.read_csv(filepath, nrows=5)
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            
            if not all(col in df.columns for col in required_columns):
                os.remove(filepath)
                return jsonify({
                    'success': False, 
                    'error': f'CSV должен содержать колонки: {", ".join(required_columns)}'
                }), 400
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Файл успешно загружен'
            })
        
        return jsonify({'success': False, 'error': 'Неверный формат файла. Требуется CSV'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/update_symbols', methods=['POST'])
def update_symbols():
    """Обновление списка символов Binance"""
    try:
        success, message = binance_symbols_manager.update_symbols()
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка обновления символов: {str(e)}'
        }), 500


@app.route('/api/get_symbols', methods=['GET'])
def get_symbols():
    """Получение списка символов из базы данных"""
    try:
        symbols = binance_symbols_manager.get_symbols_list()
        return jsonify({
            'status': 'success',
            'symbols': symbols
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка получения символов: {str(e)}'
        }), 500


@app.route('/api/download_historical_data', methods=['POST'])
def download_historical_data():
    """Загрузка исторических данных с Binance"""
    try:
        data = request.json
        
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        period = data.get('period')  # 'daily' или 'monthly'
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Валидация
        if not all([symbol, timeframe, period, start_date, end_date]):
            return jsonify({
                'status': 'error',
                'message': 'Все поля обязательны для заполнения'
            }), 400
        
        # Загружаем данные
        success, message, stats = binance_data_loader.download_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'stats': stats
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка загрузки данных: {str(e)}'
        }), 500
    """Загрузка исторических данных с Binance"""
    try:
        data = request.json
        
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        period = data.get('period')  # 'daily' или 'monthly'
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Валидация
        if not all([symbol, timeframe, period, start_date, end_date]):
            return jsonify({
                'status': 'error',
                'message': 'Все поля обязательны для заполнения'
            }), 400
        
        # Здесь будет логика загрузки данных
        # Пока возвращаем заглушку
        return jsonify({
            'status': 'success',
            'message': f'Загрузка данных для {symbol} ({timeframe}) с {start_date} по {end_date} (период: {period})'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка загрузки данных: {str(e)}'
        }), 500

@app.route('/api/get_available_data', methods=['GET'])
def get_available_data():
    """Получение доступных символов, таймфреймов и диапазонов дат"""
    try:
        import psycopg2
        
        DB_CONFIG = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DATABASE', 'backtrader'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Получаем уникальные комбинации символов и таймфреймов с датами
        cursor.execute("""
            SELECT 
                symbol, 
                timeframe,
                MIN(time) as start_date,
                MAX(time) as end_date,
                COUNT(*) as candles_count
            FROM candles
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe
        """)
        
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                'symbol': row[0],
                'timeframe': row[1],
                'start_date': row[2].strftime('%Y-%m-%d'),
                'end_date': row[3].strftime('%Y-%m-%d'),
                'candles_count': row[4]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка получения данных: {str(e)}'
        }), 500


@app.route('/api/get_candles', methods=['POST'])
def get_candles():
    """Получение свечей для графика"""
    try:
        import psycopg2
        
        data = request.json
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not all([symbol, timeframe, start_date, end_date]):
            return jsonify({
                'status': 'error',
                'message': 'Все параметры обязательны'
            }), 400
        
        DB_CONFIG = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DATABASE', 'backtrader'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                EXTRACT(EPOCH FROM time) as timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM candles
            WHERE symbol = %s 
                AND timeframe = %s 
                AND time >= %s 
                AND time <= %s
            ORDER BY time ASC
        """, (symbol, timeframe, start_date, end_date))
        
        rows = cursor.fetchall()
        
        candles = []
        for row in rows:
            candles.append({
                'time': int(row[0]),
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
                'volume': float(row[5])
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'candles': candles
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Ошибка получения свечей: {str(e)}'
        }), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)