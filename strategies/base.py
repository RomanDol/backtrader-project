"""
Базовый класс для всех стратегий VectorBT
"""
import pandas as pd
from typing import Dict, Any, Optional


class BaseStrategy:
    """Базовый класс для стратегий VectorBT"""
    
    # Переопределяется в дочерних классах
    STRATEGY_INFO = {
        'id': 'base',
        'name': 'Base Strategy',
        'description': '',
        'params': {}
    }
    
    def __init__(self, **kwargs):
        """Сохраняет параметры стратегии"""
        self.params = kwargs
    
    def generate_signals(self, df: pd.DataFrame, df_sar: Optional[pd.DataFrame] = None) -> pd.Series:
        """
        Генерирует торговые сигналы
        
        Args:
            df: DataFrame с OHLCV данными основного таймфрейма
            df_sar: DataFrame с данными для SAR (опционально)
            
        Returns:
            pd.Series: 1 = LONG, -1 = SHORT, 0 = нет сигнала
        """
        raise NotImplementedError("Метод generate_signals должен быть реализован")
    
    def get_exit_params(self) -> Dict[str, float]:
        """
        Возвращает параметры выхода (TP/SL)
        
        Returns:
            Dict с ключами 'take_profit' и 'stop_loss' (в долях, не процентах)
        """
        return {
            'take_profit': self.params.get('take_profit', 0.01),
            'stop_loss': self.params.get('stop_loss', 0.01)
        }