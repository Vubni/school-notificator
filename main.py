import os
import sys
import tempfile
from datetime import datetime, timedelta

import asyncio
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtGui import QPixmap, QKeyEvent, QImage, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QStackedLayout,
    QSizePolicy
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from qasync import QEventLoop, asyncSlot
from database.functions import init_db
from functions import get_photo, get_video   # обе функции асинхронные


class ImageDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()

        loop = asyncio.get_event_loop()

        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)

        # ---------- видео фон ----------
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # (если нужен звук, уберите строку ниже и регулируйте громкость иначе)
        self.audio_output.setVolume(0.0)

        self.media_player.mediaStatusChanged.connect(
            self.on_media_status_changed
        )

        self.video_temp_path = None

        # ---------- фото поверх видео ----------
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.image_label.setStyleSheet("background-color: transparent;")

        # ---------- стек для наложения ----------
        container = QWidget()
        stacked = QStackedLayout(container)
        stacked.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stacked.addWidget(self.video_widget)
        stacked.addWidget(self.image_label)
        self.setCentralWidget(container)

        # загрузки при старте
        loop.create_task(self.load_video())
        loop.create_task(self.load_image())

        # таймер проверки «каждую минуту»
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_time_and_update)
        self.timer.start(60_000)

        self.schedule_next_update()

    # ---------- обработчики ----------

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.restoreOverrideCursor()
            QApplication.quit()

    def closeEvent(self, event):
        self.media_player.stop()
        self.media_player.setVideoOutput(None)        # отключаем видео-выход
        self.media_player.setSource(QUrl())           # сбрасываем источник
        self.audio_output.deleteLater()
        self.media_player.deleteLater()

        if self.video_temp_path and os.path.exists(self.video_temp_path):
            try:
                os.remove(self.video_temp_path)
            except PermissionError:
                pass                                   # крайний случай – можно перезапланировать удаление

        super().closeEvent(event)

    def mousePressEvent(self, event): pass
    def mouseDoubleClickEvent(self, event): pass
    def contextMenuEvent(self, event): pass

    # ---------- работа с БД ----------

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
            final_pixmap.fill(Qt.GlobalColor.transparent)

            x = (screen_size.width() - scaled_pixmap.width()) // 2
            y = (screen_size.height() - scaled_pixmap.height()) // 2

            painter = QPainter(final_pixmap)
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()

            self.image_label.setPixmap(final_pixmap)
            print("Изображение успешно загружено из базы данных")

        except Exception as e:
            print(f"Ошибка при загрузке изображения: {e}")

    async def load_video(self):
        try:
            video_data = await get_video()
            if not video_data:
                print("Ошибка: Не удалось получить видео из базы данных")
                return

            if self.video_temp_path and os.path.exists(self.video_temp_path):
                os.remove(self.video_temp_path)

            fd, path = tempfile.mkstemp(suffix=".mp4")
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(video_data)

            self.video_temp_path = path
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.media_player.play()
            print("Видео успешно загружено из базы данных и запущено")

        except Exception as e:
            print(f"Ошибка при загрузке видео: {e}")

    # ---------- видео по кругу ----------

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.media_player.setPosition(0)
            self.media_player.play()

    # ---------- обновление фото по расписанию ----------

    def schedule_next_update(self):
        now = datetime.now()
        if now.minute < 30:
            next_update = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_update = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )

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


def main():
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    loop.run_until_complete(init_db())

    window = ImageDisplayApp()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()