from database.database import Database

last_id = -1

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