"""
Модуль стратегий для бэктестинга
"""
import os
import importlib
import inspect
from typing import Dict, List, Any

def get_strategies_list() -> List[Dict[str, Any]]:
    """
    Сканирует папку strategies/str и возвращает список всех стратегий
    """
    strategies = []
    strategies_dir = os.path.dirname(__file__)
    str_dir = os.path.join(strategies_dir, 'str')
    
    if not os.path.exists(str_dir):
        return strategies
    
    for filename in os.listdir(str_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]
            
            try:
                module = importlib.import_module(f'strategies.str.{module_name}')
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, 'STRATEGY_INFO') and obj.__module__ == f'strategies.str.{module_name}':
                        strategy_info = obj.STRATEGY_INFO.copy()
                        strategy_info['module'] = f'str.{module_name}'
                        strategy_info['class_name'] = name
                        strategies.append(strategy_info)
                        
            except Exception as e:
                print(f"⚠️ Ошибка загрузки стратегии {filename}: {e}")
                
    return strategies

def get_strategy_class(module_name: str, class_name: str):
    """
    Получить класс стратегии по имени модуля и класса
    """
    try:
        module = importlib.import_module(f'strategies.{module_name}')
        return getattr(module, class_name, None)
    except Exception as e:
        print(f"❌ Ошибка загрузки класса стратегии: {e}")
        return None