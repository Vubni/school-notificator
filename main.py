import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import QTimer, QDateTime, Qt
from PyQt6.QtGui import QPixmap, QKeyEvent, QImage
from datetime import datetime, timedelta
import qasync, asyncio
from database.functions import init_db
from functions import get_photo

class ImageDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Устанавливаем полноэкранный режим
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Скрываем курсор мыши
        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        
        # Создаем виджет для отображения изображения
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.setCentralWidget(self.image_label)
        
        # Загружаем изображение при запуске
        self.load_image()
        
        # Настраиваем таймер для проверки времени каждую минуту
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_time_and_update)
        self.timer.start(60000)  # Проверка каждую минуту
        
        # Вызываем сразу после запуска для первоначальной настройки
        self.schedule_next_update()

    def keyPressEvent(self, event: QKeyEvent):
        # Выход только по нажатию Esc
        if event.key() == Qt.Key.Key_Escape:
            QApplication.restoreOverrideCursor()  # Восстанавливаем курсор
            QApplication.quit()

    def load_image(self):
        try:
            # Получаем фото из базы данных
            image_data = get_photo()
            
            if image_data:
                # Создаем QImage из байтов
                image = QImage()
                image.loadFromData(image_data)
                
                # Конвертируем QImage в QPixmap
                pixmap = QPixmap.fromImage(image)
                
                if not pixmap.isNull():
                    # Получаем размеры экрана и изображения
                    screen_size = self.screen().size()
                    img_size = pixmap.size()
                    
                    # Вычисляем коэффициенты масштабирования
                    width_ratio = screen_size.width() / img_size.width()
                    height_ratio = screen_size.height() / img_size.height()
                    
                    # Выбираем максимальный коэффициент, чтобы изображение заполнило весь экран
                    # и обрезалось, а не сжималось
                    scale_ratio = max(width_ratio, height_ratio)
                    
                    # Масштабируем изображение
                    scaled_pixmap = pixmap.scaled(
                        screen_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    # Создаем pixmap размером с экран
                    final_pixmap = QPixmap(screen_size)
                    final_pixmap.fill(Qt.GlobalColor.black)  # Черный фон
                    
                    # Вычисляем позицию для центрирования масштабированного изображения
                    x = (screen_size.width() - scaled_pixmap.width()) // 2
                    y = (screen_size.height() - scaled_pixmap.height()) // 2
                    
                    # Рисуем масштабированное изображение на финальном pixmap
                    from PyQt6.QtGui import QPainter
                    painter = QPainter(final_pixmap)
                    painter.drawPixmap(x, y, scaled_pixmap)
                    painter.end()
                    
                    self.image_label.setPixmap(final_pixmap)
                    print("Изображение успешно загружено из базы данных")
                else:
                    print("Ошибка: Не удалось создать QPixmap из данных")
            else:
                print("Ошибка: Не удалось получить изображение из базы данных")
        except Exception as e:
            print(f"Ошибка при загрузке изображения: {e}")

    def schedule_next_update(self):
        now = datetime.now()
        current_minute = now.minute
        
        if current_minute < 30:
            next_update_minute = 30
            next_update = now.replace(minute=next_update_minute, second=0, microsecond=0)
        else:
            next_update_minute = 0
            next_update = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        
        time_diff = (next_update - datetime.now()).total_seconds()
        
        print(f"Следующее обновление в: {next_update.strftime('%H:%M:%S')}")
        
        # Устанавливаем одноразовый таймер на следующее обновление
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_image)
        self.update_timer.start(int(time_diff * 1000))

    def check_time_and_update(self):
        # Проверяем, не настало ли время обновления
        now = datetime.now()
        if now.minute == 0 or now.minute == 30:
            if now.second == 0:  # Обновляем точно в начале минуты
                self.update_image()

    def update_image(self):
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        print(f"Обновление изображения в: {datetime.now().strftime('%H:%M:%S')}")
        self.load_image()
        self.schedule_next_update()

    def mousePressEvent(self, event):
        # Игнорируем все клики мышкой
        pass

    def mouseDoubleClickEvent(self, event):
        # Игнорируем двойные клики
        pass

    def contextMenuEvent(self, event):
        # Отключаем контекстное меню
        pass

async def main():
    """Асинхронная главная функция"""
    await init_db()
    
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = ImageDisplayApp()
    window.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted")
    except Exception as e:
        print(f"Application error: {e}")
    finally:
        print("Application closed")