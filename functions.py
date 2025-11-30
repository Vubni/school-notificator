from database.database import Database

last_id = -1
last_video_id = -1

async def get_photo():
    global last_id
    try:
        async with Database() as db:
            # Сначала получаем последний ID
            result = await db.execute("SELECT id FROM images ORDER BY id DESC")
            if result["id"]:
                
                # Если изображение обновилось, получаем новые данные
                if last_id != result["id"]:
                    last_id = result["id"]
                    result = await db.execute("SELECT image FROM images ORDER BY id DESC")
                    return result["image"]
            
        return None
    except Exception as e:
        print(f"Ошибка при получении фото из БД: {e}")
        return None
    
async def get_video():
    global last_video_id
    try:
        async with Database() as db:
            # Получаем последний ID из таблицы videos
            result = await db.execute("SELECT id FROM videos ORDER BY id DESC")
            if result["id"]:
                
                # Если видео обновилось (id изменился), загружаем новое значение
                if last_video_id != result["id"]:
                    last_video_id = result["id"]
                    result = await db.execute("SELECT video FROM videos ORDER BY id DESC")
                    return result["video"]
            
        return None
    except Exception as e:
        print(f"Ошибка при получении видео из БД: {e}")
        return None