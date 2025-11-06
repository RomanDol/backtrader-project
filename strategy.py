import backtrader as bt
import datetime
import pandas as pd


class SimpleMovingAverageStrategy(bt.Strategy):
    """
    Простая стратегия на основе скользящих средних (SMA)
    Сигнал на покупку: быстрая SMA пересекает медленную снизу вверх
    Сигнал на продажу: быстрая SMA пересекает медленную сверху вниз
    """
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('printlog', False),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Индикаторы
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period)
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period)
        
        # Сигнал кроссовера
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    def log(self, txt, dt=None):
        """Логирование"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'ПОКУПКА ИСПОЛНЕНА, Цена: {order.executed.price:.2f}, '
                    f'Стоимость: {order.executed.value:.2f}, '
                    f'Комиссия: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    f'ПРОДАЖА ИСПОЛНЕНА, Цена: {order.executed.price:.2f}, '
                    f'Стоимость: {order.executed.value:.2f}, '
                    f'Комиссия: {order.executed.comm:.2f}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Ордер Отменен/Маржа/Отклонен')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'ПРИБЫЛЬ ПО СДЕЛКЕ, Валовая: {trade.pnl:.2f}, Чистая: {trade.pnlcomm:.2f}')

    def next(self):
        self.log(f'Закрытие: {self.dataclose[0]:.2f}')

        if self.order:
            return

        if not self.position:
            if self.crossover > 0:
                self.log(f'СИГНАЛ НА ПОКУПКУ, Цена: {self.dataclose[0]:.2f}')
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.log(f'СИГНАЛ НА ПРОДАЖУ, Цена: {self.dataclose[0]:.2f}')
                self.order = self.sell()


def run_backtest(data_file=None, initial_cash=10000.0, commission=0.001, 
                 fast_period=10, slow_period=30):
    """
    Запуск бэктеста
    
    Args:
        data_file: путь к CSV файлу с данными
        initial_cash: начальный капитал
        commission: комиссия брокера
        fast_period: период быстрой MA
        slow_period: период медленной MA
    
    Returns:
        dict с результатами
    """
    import numpy as np
    import math
    
    cerebro = bt.Cerebro()
    
    # Добавление стратегии
    cerebro.addstrategy(SimpleMovingAverageStrategy, 
                       fast_period=fast_period,
                       slow_period=slow_period,
                       printlog=True)
    
    # Загрузка данных
    if data_file:
        df = pd.read_csv(data_file, parse_dates=True, index_col=0)
    else:
        # Генерация тестовых данных с волатильностью
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
        base_price = 100
        prices = []
        
        for i in range(len(dates)):
            # Добавляем случайное изменение для реалистичности
            change = np.random.randn() * 2  # случайное изменение
            base_price = base_price + change
            prices.append(base_price)
        
        df = pd.DataFrame({
            'open': [p * 0.99 for p in prices],
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': [1000000 + np.random.randint(-100000, 100000) for _ in prices]
        }, index=dates)
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Настройки
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=commission)
    
    # Добавление анализаторов
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    print(f'Начальный капитал: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f'Финальный капитал: {final_value:.2f}')
    
    # Получение результатов анализа
    strat = results[0]
    
    # Функция для безопасного получения числовых значений
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
        'initial_value': float(initial_cash),
        'final_value': float(final_value),
        'profit': float(final_value - initial_cash),
        'profit_percent': float(((final_value - initial_cash) / initial_cash) * 100),
        'sharpe_ratio': safe_float(sharpe, 0.0),
        'max_drawdown': safe_float(drawdown, 0.0),
        'total_return': safe_float(returns, 0.0) * 100,
        'trades': trades_analysis if trades_analysis else {}
    }


if __name__ == '__main__':
    results = run_backtest()
    print("\n=== РЕЗУЛЬТАТЫ БЭКТЕСТА ===")
    print(f"Прибыль: ${results['profit']:.2f} ({results['profit_percent']:.2f}%)")
    print(f"Коэффициент Шарпа: {results['sharpe_ratio']:.2f}")
    print(f"Максимальная просадка: {results['max_drawdown']:.2f}%")
    print(f"Общая доходность: {results['total_return']:.2f}%")