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


async def upload_video_to_db(video_path: str, additional_fields: Optional[dict] = None) -> Optional[int]:
    """
    Загружает видео в базу данных в таблицу videos.
    
    Args:
        video_path: Путь к видеофайлу
        additional_fields: Дополнительные поля для вставки (если есть в таблице)
        
    Returns:
        ID вставленной записи или None в случае ошибки
    """
    # Проверяем существование файла
    if not os.path.exists(video_path):
        logger.error(f"Файл не найден: {video_path}")
        return None
    
    try:
        # Читаем файл видео в бинарном режиме
        with open(video_path, 'rb') as file:
            video_data = file.read()
        
        # Формируем SQL запрос и параметры
        if additional_fields:
            fields = ['video'] + list(additional_fields.keys())
            placeholders = ['$1'] + [f'${i+2}' for i in range(len(additional_fields))]
            values = [video_data] + list(additional_fields.values())
            
            sql = f"""
                INSERT INTO videos ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """
        else:
            sql = "INSERT INTO videos (video) VALUES ($1) RETURNING id"
            values = (video_data,)
        
        # Выполняем запрос через класс Database
        async with Database() as db:
            video_id = await db.fetchval(sql, values)
            return video_id
            
    except FileNotFoundError:
        logger.error(f"Файл видео не найден: {video_path}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при загрузке видео в БД: {e}")
        return None
