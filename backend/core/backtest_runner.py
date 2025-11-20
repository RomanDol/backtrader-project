"""
Модуль для запуска бэктестов
"""
import logging
import backtrader as bt
from datetime import datetime
from typing import Dict, Any
from .binance_data_loader import binance_data_loader
from .backtest_results import backtest_results_manager
from strategies import get_strategy_class

logger = logging.getLogger(__name__)

class BacktestRunner:
    """Класс для запуска бэктестов"""
    
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
        
        Args:
            symbol: Торговая пара (например, BTCUSDT)
            timeframe: Таймфрейм (например, 1h)
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата окончания (YYYY-MM-DD)
            strategy_module: Имя модуля стратегии
            strategy_class: Имя класса стратегии
            strategy_params: Параметры стратегии
            initial_cash: Начальный капитал
            commission: Комиссия
            
        Returns:
            Dict с результатами бэктеста
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
            
            # Создаем Cerebro
            cerebro = bt.Cerebro(tradehistory=True)
            
            # Загружаем класс стратегии
            StrategyClass = get_strategy_class(strategy_module, strategy_class)
            if not StrategyClass:
                return {
                    'success': False,
                    'error': f'Стратегия {strategy_class} не найдена'
                }
            
            # Добавляем стратегию с параметрами
            strat_instance = cerebro.addstrategy(StrategyClass, **strategy_params, printlog=False)
            
            # Подготавливаем данные для backtrader
            data = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data)

            
            # Настройка брокера
            cerebro.broker.setcash(initial_cash)
            cerebro.broker.setcommission(commission=commission)
            
            # Добавление анализаторов
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            # Запуск бэктеста
            initial_value = cerebro.broker.getvalue()
            logger.info(f'💰 Начальный капитал: ${initial_value:.2f}')
            
            results = cerebro.run()
            strat = results[0]
            
            final_value = cerebro.broker.getvalue()
            logger.info(f'💰 Финальный капитал: ${final_value:.2f}')
            
            # Сбор сделок
            trades_list = self._collect_trades(strat)

            
            # Сохранение сделок в базу
            if trades_list:
                backtest_results_manager.save_trades(trades_list)
                logger.info(f"✅ Сохранено {len(trades_list)} сделок")
            
            # Формирование результатов
            return self._format_results(
                strat, 
                initial_value, 
                final_value, 
                len(trades_list)
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бэктеста: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _collect_trades(self, strat) -> list:
            """Собирает сделки из списка закрытых сделок стратегии"""
            trades_list = []
            
            if hasattr(strat, 'trade_list'):
                for trade in strat.trade_list:
                    # Проверяем наличие history
                    if not hasattr(trade, 'history') or not trade.history or len(trade.history) < 2:
                        logger.warning(f"⚠️ Trade без history, пропускаем")
                        continue
                    
                    # Получаем события входа и выхода
                    entry_event = trade.history[0]
                    exit_event = trade.history[-1]
                    
                    # Получаем размер и направление из entry
                    entry_size = entry_event['status']['size']
                    side = 'LONG' if entry_size > 0 else 'SHORT'
                    
                    # Получаем данные
                    entry_date = bt.num2date(entry_event['status']['dt']).replace(tzinfo=None)
                    entry_price = entry_event['event']['price']
                    entry_commission = entry_event['event']['commission']
                    
                    exit_date = bt.num2date(exit_event['status']['dt']).replace(tzinfo=None)
                    exit_price = exit_event['event']['price']
                    exit_commission = exit_event['event']['commission']
                    
                    total_commission = entry_commission + exit_commission
                    
                    trade_data = {
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_size': abs(entry_size),
                        'side': side,
                        'exit_date': exit_date,
                        'exit_price': exit_price,
                        'pnl': trade.pnl,
                        'pnl_percent': (trade.pnl / abs(entry_event['status']['value'])) * 100 if entry_event['status']['value'] != 0 else 0,
                        'commission': total_commission,
                        'bars_held': trade.barlen,
                        'mae': None,
                        'mfe': None
                    }
                    trades_list.append(trade_data)
                
                logger.info(f"📊 Собрано сделок: {len(trades_list)}")
            
            return trades_list

    
    
    def _format_results(self, strat, initial_value, final_value, trades_count) -> Dict:
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
        
        # Получаем данные из анализаторов
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        returns_analysis = strat.analyzers.returns.get_analysis()
        trades_analysis = strat.analyzers.trades.get_analysis()
        
        sharpe = sharpe_analysis.get('sharperatio', None) if sharpe_analysis else None
        drawdown = drawdown_analysis.get('max', {}).get('drawdown', None) if drawdown_analysis else None
        returns = returns_analysis.get('rtot', None) if returns_analysis else None
        
        return {
            'success': True,
            'results': {
                'initial_value': float(initial_value),
                'final_value': float(final_value),
                'profit': float(final_value - initial_value),
                'profit_percent': float(((final_value - initial_value) / initial_value) * 100),
                'sharpe_ratio': safe_float(sharpe, 0.0),
                'max_drawdown': safe_float(drawdown, 0.0),
                'total_return': safe_float(returns, 0.0) * 100,
                'trades_count': trades_count,
                'trades_analysis': trades_analysis if trades_analysis else {}
            }
        }

# Создаем глобальный экземпляр
backtest_runner = BacktestRunner()