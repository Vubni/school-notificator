from database.database import Database

last_id = -1

def get_photo():
    global last_id
    try:
        with Database() as db:
            # Сначала получаем последний ID
            result = db.execute("SELECT id FROM images ORDER BY id DESC LIMIT 1")
            if result and len(result) > 0:
                current_id = result[0]["id"]
                
                # Если изображение обновилось, получаем новые данные
                if last_id != current_id:
                    result = db.execute("SELECT image FROM images ORDER BY id DESC LIMIT 1")
                    if result and len(result) > 0:
                        last_id = current_id
                        return result[0]["image"]
            
        return None
    except Exception as e:
        print(f"Ошибка при получении фото из БД: {e}")
        return None