import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import QTimer, QDateTime, Qt
from PyQt6.QtGui import QPixmap, QKeyEvent, QImage, QPainter
from datetime import datetime, timedelta
import qasync, asyncio
from qasync import QEventLoop, asyncSlot

from database.functions import init_db
from functions import get_photo   # теперь это async def get_photo()

class ImageDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        loop = asyncio.get_event_loop()
        loop.create_task(self.load_image())

        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.setCentralWidget(self.image_label)

        # загрузка первого кадра
        loop.create_task(self.load_image())

        # таймер проверки “каждую минуту”
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_time_and_update)
        self.timer.start(60_000)

        self.schedule_next_update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.restoreOverrideCursor()
            QApplication.quit()

    async def load_image(self):
        try:
            image_data = await get_photo()
            if not image_data:
                print("Ошибка: Не удалось получить изображение из базы данных")
                return

            image = QImage()
            image.loadFromData(image_data)
            pixmap = QPixmap.fromImage(image)

            if pixmap.isNull():
                print("Ошибка: Не удалось создать QPixmap из данных")
                return

            screen_size = self.screen().size()
            scaled_pixmap = pixmap.scaled(
                screen_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            final_pixmap = QPixmap(screen_size)
            final_pixmap.fill(Qt.GlobalColor.black)

            x = (screen_size.width() - scaled_pixmap.width()) // 2
            y = (screen_size.height() - scaled_pixmap.height()) // 2

            painter = QPainter(final_pixmap)
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
            print("Изображение успешно загружено из базы данных")

        except Exception as e:
            print(f"Ошибка при загрузке изображения: {e}")

    def schedule_next_update(self):
        now = datetime.now()
        if now.minute < 30:
            next_update = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_update = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        time_diff = (next_update - datetime.now()).total_seconds()
        print(f"Следующее обновление в: {next_update.strftime('%H:%M:%S')}")

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(
            lambda: asyncio.create_task(self.update_image())
        )
        self.update_timer.start(int(time_diff * 1000))

    def check_time_and_update(self):
        now = datetime.now()
        if now.minute in (0, 30) and now.second == 0:
            asyncio.create_task(self.update_image())

    @asyncSlot()
    async def update_image(self):
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()

        print(f"Обновление изображения в: {datetime.now().strftime('%H:%M:%S')}")
        await self.load_image()
        self.schedule_next_update()

    # остальные обработчики мыши без изменений
    def mousePressEvent(self, event): pass
    def mouseDoubleClickEvent(self, event): pass
    def contextMenuEvent(self, event): pass


def main():
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # всё, что надо выполнить «до» запуска GUI
    loop.run_until_complete(init_db())

    window = ImageDisplayApp()
    window.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()