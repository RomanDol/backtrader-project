from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import pandas as pd
from strategy import run_backtest
from backend.core.binance_symbols import binance_symbols_manager

app = Flask(__name__)
CORS(app)

# Папка для загрузки файлов
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/tools')
def tools():
    """Страница инструментов"""
    return render_template('tools.html')


@app.route('/api/backtest', methods=['POST'])
def backtest():
    """API для запуска бэктеста"""
    try:
        data = request.json
        
        # Получение параметров
        initial_cash = float(data.get('initial_cash', 10000))
        commission = float(data.get('commission', 0.001))
        fast_period = int(data.get('fast_period', 10))
        slow_period = int(data.get('slow_period', 30))
        
        # Запуск бэктеста
        results = run_backtest(
            data_file=None,  # Используем тестовые данные
            initial_cash=initial_cash,
            commission=commission,
            fast_period=fast_period,
            slow_period=slow_period
        )
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


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





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)