"""
Модуль для аутентификации
"""
import os
from flask import request, Response
from dotenv import load_dotenv

load_dotenv()

class AuthManager:
    """Класс для управления аутентификацией"""
    
    def __init__(self):
        self.username = os.getenv('UI_USERNAME', 'admin')
        self.password = os.getenv('UI_PASSWORD', 'admin')
    
    def check_auth(self, username: str, password: str) -> bool:
        """Проверка учетных данных"""
        return username == self.username and password == self.password
    
    def authenticate(self) -> Response:
        """Запрос аутентификации"""
        return Response(
            'Authentication required', 401,
            {'WWW-Authenticate': 'Basic realm="Backtrader Login Required"'}
        )
    
    def require_auth(self) -> Response or None:
        """
        Middleware для проверки аутентификации
        
        Returns:
            Response or None: Response с запросом авторизации или None если авторизован
        """
        # Пропускаем статические файлы
        if request.path.startswith('/static/'):
            return None
        
        auth = request.authorization
        if not auth or not self.check_auth(auth.username, auth.password):
            return self.authenticate()
        
        return None

auth_manager = AuthManager()