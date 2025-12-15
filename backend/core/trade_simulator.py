"""
Numba-симулятор сделок с trailing take profit
"""
import numpy as np
from numba import njit


@njit
def simulate_trades_nb(direction_signals, open_arr, high_arr, low_arr, close_arr,
                       tp_pct, trail_pct, sl_pct, quote_size):
    """
    Симуляция торговли с точными ценами входа/выхода.
    
    Args:
        direction_signals: 1=long, -1=short, 0=нет сигнала
        open_arr, high_arr, low_arr, close_arr: OHLC данные
        tp_pct: Take Profit в долях (0.07 = 7%)
        trail_pct: Trail offset в долях (0.002 = 0.2%)
        sl_pct: Stop Loss в долях (0.14 = 14%)
        quote_size: Размер позиции в USDT
        
    Returns:
        order_size: массив размеров ордеров (+ buy, - sell)
        order_price: массив цен исполнения
    """
    n = len(close_arr)
    
    order_size = np.zeros(n)
    order_price = np.full(n, np.nan)
    
    in_position = False
    position_side = 0  # 1 = long, -1 = short
    position_size = 0.0
    entry_price = 0.0
    max_price = 0.0
    min_price = 999999999.0
    trail_active = False
    
    for i in range(n):
        # Проверяем выход (если в позиции)
        if in_position:
            exit_price = 0.0
            
            if position_side == 1:  # Long
                # Обновляем максимум
                if high_arr[i] > max_price:
                    max_price = high_arr[i]
                
                tp_level = entry_price * (1 + tp_pct)
                sl_level = entry_price * (1 - sl_pct)
                
                # Проверяем TP/Trailing
                if trail_pct > 0:
                    # Trailing режим
                    if not trail_active and max_price >= tp_level:
                        trail_active = True
                    
                    if trail_active:
                        trail_stop = max_price * (1 - trail_pct)
                        if low_arr[i] <= trail_stop:
                            exit_price = trail_stop
                else:
                    # Обычный TP (без trailing)
                    if high_arr[i] >= tp_level:
                        exit_price = tp_level
                
                # Проверяем SL
                if exit_price == 0.0 and low_arr[i] <= sl_level:
                    exit_price = sl_level
                    
            else:  # Short
                # Обновляем минимум
                if low_arr[i] < min_price:
                    min_price = low_arr[i]
                
                tp_level = entry_price * (1 - tp_pct)
                sl_level = entry_price * (1 + sl_pct)
                
                # Проверяем TP/Trailing
                if trail_pct > 0:
                    # Trailing режим
                    if not trail_active and min_price <= tp_level:
                        trail_active = True
                    
                    if trail_active:
                        trail_stop = min_price * (1 + trail_pct)
                        if high_arr[i] >= trail_stop:
                            exit_price = trail_stop
                else:
                    # Обычный TP (без trailing)
                    if low_arr[i] <= tp_level:
                        exit_price = tp_level
                
                # Проверяем SL
                if exit_price == 0.0 and high_arr[i] >= sl_level:
                    exit_price = sl_level
            
            # Выход
            if exit_price > 0:
                if position_side == 1:
                    order_size[i] = -position_size  # Sell
                else:
                    order_size[i] = position_size   # Buy to cover
                order_price[i] = exit_price
                
                in_position = False
                trail_active = False
                continue  # Не входим на том же баре
        
        # Проверяем вход
        if not in_position and direction_signals[i] != 0:
            in_position = True
            position_side = direction_signals[i]
            entry_price = close_arr[i]
            position_size = quote_size / entry_price
            max_price = high_arr[i]
            min_price = low_arr[i]
            trail_active = False
            
            if position_side == 1:
                order_size[i] = position_size   # Buy
            else:
                order_size[i] = -position_size  # Sell short
            order_price[i] = entry_price
    
    return order_size, order_price