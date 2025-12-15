"""
Модуль для запуска бэктестов на VectorBT
"""
import logging
import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime
from typing import Dict, Any
from .binance_data_loader import binance_data_loader
from .backtest_results import backtest_results_manager
from strategies import get_strategy_class

logger = logging.getLogger(__name__)



class BacktestRunner:
    """Класс для запуска бэктестов на VectorBT"""

    

        
    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        strategy_module: str,
        strategy_class: str,
        strategy_params: Dict[str, Any],
        initial_cash: float = 100.0,
        commission: float = 0.05
    ) -> Dict[str, Any]:
        """
        Запускает бэктест с указанными параметрами
        """
        try:
            # Очищаем таблицу результатов
            backtest_results_manager.clear_results()
            
            # Загружаем данные из базы
            logger.info(f"📊 Загрузка данных: {symbol} {timeframe} {start_date} - {end_date}")
            df = binance_data_loader.load_data_for_backtest(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                return {
                    'success': False,
                    'error': 'Нет данных для указанного периода'
                }
            
            logger.info(f"✅ Загружено {len(df)} свечей")
            
            # Загружаем класс стратегии
            StrategyClass = get_strategy_class(strategy_module, strategy_class)
            if not StrategyClass:
                return {
                    'success': False,
                    'error': f'Стратегия {strategy_class} не найдена'
                }
            
            # Создаём экземпляр стратегии
            strategy = StrategyClass(**strategy_params)
            
            # Загружаем данные для SAR если указан другой таймфрейм
            df_sar = None
            sar_timeframe = strategy_params.get('sar_timeframe', '')
            
            if sar_timeframe and sar_timeframe != timeframe:
                logger.info(f"📊 Загрузка SAR данных: {symbol} {sar_timeframe}")
                df_sar = binance_data_loader.load_data_for_backtest(
                    symbol=symbol,
                    timeframe=sar_timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df_sar is None or df_sar.empty:
                    return {
                        'success': False,
                        'error': f'Нет данных для SAR таймфрейма {sar_timeframe}'
                    }
                
                logger.info(f"✅ Загружено {len(df_sar)} SAR свечей")
            
            # Генерируем сигналы
            signals = strategy.generate_signals(df, df_sar)

            
            # Получаем параметры выхода
            exit_params = strategy.get_exit_params()

            # Параметры trailing (если есть)
            tp_level = exit_params['take_profit']  # уровень активации trailing
            trail_offset = exit_params.get('trail_offset', 0)  # отступ trailing
            



            # trail_offset = 0


            
            # Импортируем симулятор
            from .trade_simulator import simulate_trades_nb
            
            # Конвертируем сигналы в numpy array
            direction_signals = signals.values.astype(np.float64)
            
            # Запускаем симуляцию
            order_size, order_price = simulate_trades_nb(
                direction_signals,
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values,
                tp_level,
                trail_offset,
                exit_params['stop_loss'],
                strategy_params.get('quote', initial_cash)
            )
            
            # Создаём Portfolio через from_orders
            pf = vbt.Portfolio.from_orders(
                close=df['close'],
                size=pd.Series(order_size, index=df.index),
                price=pd.Series(order_price, index=df.index),
                init_cash=initial_cash,
                fees=commission,
                freq=timeframe,
            )
            

            # Собираем сделки
            trades_list = self._collect_trades(pf, df)
            
            # Сохраняем сделки в базу
            if trades_list:
                backtest_results_manager.save_trades(trades_list)
                logger.info(f"✅ Сохранено {len(trades_list)} сделок")
            
            # Формируем результаты
            return self._format_results(pf, initial_cash, len(trades_list))
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бэктеста: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_trades(self, pf, df: pd.DataFrame) -> list:
        """Собирает сделки из VectorBT Portfolio"""
        trades_list = []
        
        try:
            trades_df = pf.trades.records_readable
            
            if trades_df.empty:
                return trades_list
            
            # Получаем информацию о стопах из orders
            orders_df = pf.orders.records_readable
            
            for _, trade in trades_df.iterrows():
                entry_ts = trade['Entry Timestamp']
                exit_ts = trade['Exit Timestamp']
                
                # Считаем bars_held по индексу
                try:
                    entry_idx = df.index.get_loc(entry_ts)
                    exit_idx = df.index.get_loc(exit_ts)
                    bars_held = exit_idx - entry_idx
                except:
                    bars_held = None
                
                trade_data = {
                    'entry_date': entry_ts,
                    'entry_price': float(trade['Avg Entry Price']),
                    'entry_size': float(trade['Size']),
                    'side': 'LONG' if trade['Direction'] == 'Long' else 'SHORT',
                    'exit_date': exit_ts,
                    'exit_price': float(trade['Avg Exit Price']),
                    'pnl': float(trade['PnL']),
                    'pnl_percent': float(trade['Return'] * 100),
                    'commission': float(trade['Entry Fees'] + trade['Exit Fees']),
                    'bars_held': bars_held,
                    'mae': None,
                    'mfe': None,
                    'trade_history': {},
                    'exit_reason': trade['Status'],  # Closed или Open
                }
                trades_list.append(trade_data)
            
            logger.info(f"📊 Собрано сделок: {len(trades_list)}")
   

            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка сбора сделок: {e}")
        
        return trades_list
    
    def _format_results(self, pf, initial_cash: float, trades_count: int) -> Dict:
        """Форматирует результаты бэктеста"""
        import math
        
        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                if isinstance(value, (int, float)):
                    if math.isnan(value) or math.isinf(value):
                        return default
                    return float(value)
                return default
            except (TypeError, ValueError):
                return default
        
        stats = pf.stats()
        final_value = float(pf.final_value())
        
        return {
            'success': True,
            'results': {
                'initial_value': float(initial_cash),
                'final_value': final_value,
                'profit': final_value - initial_cash,
                'profit_percent': ((final_value / initial_cash) - 1) * 100,
                'sharpe_ratio': safe_float(stats.get('Sharpe Ratio', 0)),
                'max_drawdown': safe_float(stats.get('Max Drawdown [%]', 0)),
                'total_return': safe_float(stats.get('Total Return [%]', 0)),
                'trades_count': trades_count,
                'win_rate': safe_float(stats.get('Win Rate [%]', 0)),
                'trades_analysis': {}
            }
        }


# Создаём глобальный экземпляр
backtest_runner = BacktestRunner()