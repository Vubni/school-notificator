import json
import time
from typing import Union, List, Dict, Optional, Any
import psycopg
from psycopg import sql, errors, OperationalError
from psycopg.rows import dict_row
from config import DATE_BASE_CONNECT, logger

class Database:
    MAX_RETRIES = 30
    RETRY_DELAY = 1  # seconds

    def __init__(self):
        self.connection = None
        self.cursor = None
        self._retry_count = 0
        self._in_transaction = False

    def __enter__(self):
        """Установка соединения с автоматическим переподключением"""
        self.connection = None
        self.cursor = None
        
        while self._retry_count < self.MAX_RETRIES:
            try:
                self.connection = psycopg.connect(**DATE_BASE_CONNECT)
                self.cursor = self.connection.cursor(row_factory=dict_row)
                self._retry_count = 0  # Сброс счетчика при успешном подключении
                self._in_transaction = True
                return self
            except OperationalError as e:
                self._retry_count += 1
                logger.error(f"Попытка подключения {self._retry_count}/{self.MAX_RETRIES} failed: {e}")
                time.sleep(self.RETRY_DELAY)
            except Exception as e:
                logger.error(f"Неожиданная ошибка подключения: {e}")
                break

        logger.error("Превышено максимальное количество попыток подключения")
        return None

    def __exit__(self, exc_type, exc_value, traceback):
        """Безопасное закрытие соединения"""
        try:
            if self._in_transaction:
                if exc_type is None:
                    try:
                        self.connection.commit()
                    except Exception as e:
                        logger.error(f"Ошибка при коммите транзакции: {e}")
                        self.connection.rollback()
                else:
                    try:
                        self.connection.rollback()
                    except Exception as e:
                        logger.error(f"Ошибка при откате транзакции: {e}")
        finally:
            if self.cursor:
                try:
                    self.cursor.close()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии курсора: {e}")
            if self.connection:
                try:
                    self.connection.close()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии соединения: {e}")
                finally:
                    self.connection = None
                    self.cursor = None
                    self._in_transaction = False

    def close_connection(self) -> None:
        """Явное закрытие соединения с обработкой ошибок"""
        if self._in_transaction:
            try:
                self.connection.commit()
            except Exception as e:
                logger.error(f"Ошибка при коммите при закрытии: {e}")
        if self.cursor:
            try:
                self.cursor.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии курсора: {e}")
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения: {e}")
            finally:
                self.connection = None
                self.cursor = None
                self._in_transaction = False

    def serialize(self, data) -> Union[int, str, float, List, Dict, None]:
        """Рекурсивная сериализация данных из БД"""
        try:
            if data is None:
                return None
                
            if isinstance(data, bytes):
                data = data.decode('utf-8')
                
            if isinstance(data, str):
                return data
                
            if isinstance(data, list):
                return [self.serialize(item) for item in data]
                
            if isinstance(data, dict):
                return {key: self.serialize(value) for key, value in data.items()}
                
            # Для psycopg3 результаты уже являются dict благодаря row_factory=dict_row
            return data
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка сериализации данных: {e}")
            return None

    def execute_all(self, sql: str, params: tuple = None) -> Optional[List[Dict]]:
        """Выполнение SELECT-запросов с множественным результатом"""
        if not self._check_connection():
            return None
            
        try:
            if sql.strip().lower().startswith('select'):
                self.cursor.execute(sql, params)
                result = self.cursor.fetchall()
                return self.serialize(result)
            else:
                self.cursor.execute(sql, params)
                return []
        except Exception as e:
            self._handle_exception(e, sql)
            return None

    def execute(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """Выполнение SELECT-запросов с единичным результатом"""
        if not self._check_connection():
            return None
            
        try:
            if sql.strip().lower().startswith('select'):
                self.cursor.execute(sql, params)
                result = self.cursor.fetchone()
                return self.serialize(result)
            else:
                self.cursor.execute(sql, params)
                return {}
        except Exception as e:
            self._handle_exception(e, sql)
            return None

    def fetchval(self, sql: str, params: tuple = None) -> Optional[int]:
        """Получение скалярного значения"""
        if not self._check_connection():
            return None
            
        try:
            if "RETURNING" not in sql.upper():
                sql = f"{sql} RETURNING id"
                
            self.cursor.execute(sql, params)
            result = self.cursor.fetchone()
            return result['id'] if result else None
        except Exception as e:
            self._handle_exception(e, sql)
            return None

    def executemany(self, sql: str, params: List[tuple] = None) -> Optional[bool]:
        """Выполнение массовых операций"""
        if not self._check_connection():
            return None
            
        try:
            if sql.strip().lower().startswith('select'):
                logger.error("Используйте execute() для SELECT-запросов")
                return None
            self.cursor.executemany(sql, params)
            return True
        except Exception as e:
            self._handle_exception(e, sql)
            return None

    def _check_connection(self) -> bool:
        """Проверка активности соединения"""
        if not self.connection or self.connection.closed:
            logger.error("Соединение с БД не установлено")
            return False
        return True

    def _handle_exception(self, exception: Exception, sql: str) -> None:
        """Единый обработчик ошибок с логированием"""
        error_msg = f"{exception.__class__.__name__}: {exception}\nSQL: {sql}"
        if isinstance(exception, (OperationalError, errors.InterfaceError)):
            logger.error(f"Ошибка подключения к БД: {error_msg}")
        else:
            logger.error(f"Ошибка выполнения запроса: {error_msg}")