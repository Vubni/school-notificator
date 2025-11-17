from database.database import Database
import os
from typing import Union, Optional
from config import logger

async def upload_image_to_db(image_path: str, additional_fields: Optional[dict] = None) -> Optional[int]:
    """
    Загружает изображение в базу данных в таблицу images.
    
    Args:
        image_path: Путь к файлу изображения
        additional_fields: Дополнительные поля для вставки (если есть в таблице)
        
    Returns:
        ID вставленной записи или None в случае ошибки
    """
    # Проверяем существование файла
    if not os.path.exists(image_path):
        logger.error(f"Файл не найден: {image_path}")
        return None
    
    try:
        # Читаем файл изображения в бинарном режиме
        with open(image_path, 'rb') as file:
            image_data = file.read()
        
        # Формируем SQL запрос и параметры
        if additional_fields:
            # Если есть дополнительные поля
            fields = ['image'] + list(additional_fields.keys())
            placeholders = ['$1'] + [f'${i+2}' for i in range(len(additional_fields))]
            values = [image_data] + list(additional_fields.values())
            
            sql = f"""
                INSERT INTO images ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
        else:
            # Если только изображение
            sql = "INSERT INTO images (image) VALUES ($1) RETURNING id"
            values = (image_data,)
        
        # Выполняем запрос через класс Database
        async with Database() as db:
            image_id = await db.fetchval(sql, values)
            return image_id
            
    except FileNotFoundError:
        logger.error(f"Файл изображения не найден: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения в БД: {e}")
        return None


async def upload_image_bytes_to_db(image_bytes: bytes, additional_fields: Optional[dict] = None) -> Optional[int]:
    """
    Загружает изображение из байтов в базу данных.
    
    Args:
        image_bytes: Байты изображения
        additional_fields: Дополнительные поля для вставки
        
    Returns:
        ID вставленной записи или None в случае ошибки
    """
    try:
        # Формируем SQL запрос и параметры
        if additional_fields:
            fields = ['image'] + list(additional_fields.keys())
            placeholders = ['$1'] + [f'${i+2}' for i in range(len(additional_fields))]
            values = [image_bytes] + list(additional_fields.values())
            
            sql = f"""
                INSERT INTO images ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
        else:
            sql = "INSERT INTO images (image) VALUES ($1) RETURNING id"
            values = (image_bytes,)
        
        # Выполняем запрос через класс Database
        async with Database() as db:
            image_id = await db.fetchval(sql, values)
            return image_id
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения в БД: {e}")
        return None


async def get_image_from_db(image_id: int) -> Optional[bytes]:
    """
    Получает изображение из базы данных по ID.
    
    Args:
        image_id: ID изображения в базе данных
        
    Returns:
        Байты изображения или None в случае ошибки
    """
    try:
        sql = "SELECT image FROM images WHERE id = $1"
        
        async with Database() as db:
            result = await db.execute(sql, (image_id,))
            
            if result and 'image' in result:
                return result['image']
            else:
                logger.error(f"Изображение с ID {image_id} не найдено")
                return None
                
    except Exception as e:
        logger.error(f"Ошибка при получении изображения из БД: {e}")
        return None
    

import asyncio
asyncio.run(upload_image_to_db("test.png"))