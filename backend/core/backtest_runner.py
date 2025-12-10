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
from numba import njit

logger = logging.getLogger(__name__)

@njit
def adjust_sl_func_nb(c, tp_level, trail_offset, high_arr, low_arr):
    """
    Trailing активируется после достижения TP уровня по high/low.
    """
    if c.curr_trail:
        return trail_offset, True
    
    if c.position_now > 0:  # Long
        high_price = high_arr[c.i]
        tp_price = c.init_price * (1 + tp_level)
        if high_price >= tp_price:
            return trail_offset, True
    elif c.position_now < 0:  # Short
        low_price = low_arr[c.i]
        tp_price = c.init_price * (1 - tp_level)
        if low_price <= tp_price:
            return trail_offset, True
    
    return c.curr_stop, c.curr_trail

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
        initial_cash: float = 10000.0,
        commission: float = 0.001
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
            print(f"Signal на 11:03: {signals.loc['2025-09-18 11:03:00']}")
            print(f"Signal на 11:04: {signals.loc['2025-09-18 11:04:00']}")
            
            # Получаем параметры выхода
            exit_params = strategy.get_exit_params()

            # Параметры trailing (если есть)
            tp_level = exit_params['take_profit']  # уровень активации trailing
            trail_offset = exit_params.get('trail_offset', 0)  # отступ trailing
            
            # Точки входа/выхода
            entries_long = signals == 1
            entries_short = signals == -1

            # DEBUG
            print(f"entries_long на 11:02: {entries_long.loc['2025-09-18 11:02:00']}")
            print(f"entries_long на 11:03: {entries_long.loc['2025-09-18 11:03:00']}")
            print(f"entries_short на 11:02: {entries_short.loc['2025-09-18 11:02:00']}")
            print(f"entries_short на 11:03: {entries_short.loc['2025-09-18 11:03:00']}")

            # Выход ТОЛЬКО по TP/SL/Trailing - как в TradingView
            exits_long = pd.Series(False, index=df.index)
            exits_short = pd.Series(False, index=df.index)

            # trail_offset = 0


            
            # Запуск VectorBT Portfolio
            if trail_offset > 0:
                # С trailing - БЕЗ tp_stop
                pf = vbt.Portfolio.from_signals(
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    entries=entries_long,
                    exits=exits_long,
                    short_entries=entries_short,
                    short_exits=exits_short,
                    init_cash=initial_cash,
                    fees=commission,
                    sl_stop=exit_params['stop_loss'],
                    # tp_stop НЕ указываем - выход только по trailing SL
                    adjust_sl_func_nb=adjust_sl_func_nb,
                    adjust_sl_args=(tp_level, trail_offset, df['high'].values, df['low'].values),
                    use_stops=True,
                    size=strategy_params.get('quote', initial_cash),
                    size_type='value',
                    freq=timeframe,
                    upon_opposite_entry='Ignore'
                )
            else:
                # Без trailing - обычный TP/SL
                pf = vbt.Portfolio.from_signals(
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    entries=entries_long,
                    exits=exits_long,
                    short_entries=entries_short,
                    short_exits=exits_short,
                    init_cash=initial_cash,
                    fees=commission,
                    sl_stop=exit_params['stop_loss'],
                    tp_stop=exit_params['take_profit'],
                    stop_exit_price='stoplimit',
                    use_stops=True,
                    size=strategy_params.get('quote', initial_cash),
                    size_type='value',
                    freq=timeframe,
                    upon_opposite_entry='Ignore'
                )
            
            # DEBUG trades
            print("\n--- VectorBT первые 5 сделок ---")
            print(pf.trades.records_readable[['Entry Timestamp', 'Exit Timestamp', 'Direction', 'Avg Entry Price', 'Avg Exit Price', 'PnL']].head())
            
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