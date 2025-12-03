import os
import sys
import tempfile
import asyncio
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QSizePolicy
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from qasync import QEventLoop
from database.functions import init_db
from functions import get_video


class VideoDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)

        # ---------- видео виджет ----------
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # ---------- медиа плеер ----------
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.0)
        
        # Настройка медиаплеера
        self.media_player.setPlaybackRate(1.0)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Подключаем обработчики
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_media_error)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        # Для отслеживания позиции при перезапуске
        self.video_duration = 0
        self.video_temp_path = None
        
        # Таймер для отслеживания позиции видео
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.check_position_and_loop)
        self.position_timer.start(100)  # проверяем каждые 100мс
        
        # Устанавливаем видео виджет как центральный
        self.setCentralWidget(self.video_widget)
        
        # Таймер для обновления видео
        self.setup_refresh_timer()
        
        # Запускаем загрузку видео через небольшой таймер
        QTimer.singleShot(100, self.start_video_loading)

    def start_video_loading(self):
        """Запуск загрузки видео через asyncio"""
        asyncio.create_task(self.load_and_play_video())

    def setup_refresh_timer(self):
        """Настройка таймера для периодического обновления видео"""
        # Проверяем каждые 30 минут, нужно ли обновить видео
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(lambda: asyncio.create_task(self.load_and_play_video()))
        self.refresh_timer.start(30 * 60 * 1000)  # 30 минут

    async def load_and_play_video(self):
        """Загружает и воспроизводит видео из БД"""
        try:
            video_data = await get_video()
            if not video_data:
                print("Ошибка: Не удалось получить видео из базы данных")
                QTimer.singleShot(5000, self.start_video_loading)
                return

            # Удаляем предыдущий временный файл, если существует
            if self.video_temp_path and os.path.exists(self.video_temp_path):
                try:
                    os.remove(self.video_temp_path)
                except (PermissionError, OSError):
                    pass

            # Создаем новый временный файл
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.mp4') as tmp:
                tmp.write(video_data)
                self.video_temp_path = tmp.name

            # Останавливаем текущее воспроизведение
            if self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                self.media_player.stop()
            
            # Загружаем новое видео
            self.media_player.setSource(QUrl.fromLocalFile(self.video_temp_path))
            
            print("Видео успешно загружено")

        except Exception as e:
            print(f"Ошибка при загрузке видео: {e}")
            QTimer.singleShot(10000, self.start_video_loading)

    def on_media_status_changed(self, status):
        """Обработка изменений статуса медиа"""
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # Получаем длительность видео
            self.video_duration = self.media_player.duration()
            print(f"Медиа загружено, длительность: {self.video_duration} мс")
            
            # Запускаем воспроизведение
            self.media_player.play()
            
        elif status == QMediaPlayer.MediaStatus.BufferedMedia:
            print("Медиа буферизировано")
            
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            print("Неверный медиафайл, попытка перезагрузки")
            self.start_video_loading()

    def check_position_and_loop(self):
        """Проверяет текущую позицию и перематывает видео до конца, если нужно"""
        if self.video_duration > 0:
            current_pos = self.media_player.position()
            # Если текущая позиция близка к концу (например, за 200мс до конца)
            if current_pos >= (self.video_duration - 200):
                self.media_player.setPosition(0)

    def on_media_error(self, error, error_string):
        """Обработка ошибок воспроизведения"""
        print(f"Ошибка медиаплеера ({error}): {error_string}")
        QTimer.singleShot(3000, self.start_video_loading)

    def on_playback_state_changed(self, state):
        """Обработка изменений состояния воспроизведения"""
        states = {
            QMediaPlayer.PlaybackState.StoppedState: "Остановлено",
            QMediaPlayer.PlaybackState.PlayingState: "Воспроизводится",
            QMediaPlayer.PlaybackState.PausedState: "На паузе"
        }
        print(f"Состояние воспроизведения: {states.get(state, 'Неизвестно')}")

    def cleanup_resources(self):
        """Очистка ресурсов при закрытии"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'position_timer'):
            self.position_timer.stop()
        
        if self.media_player:
            self.media_player.stop()
            self.media_player.setVideoOutput(None)
            self.media_player.setSource(QUrl())
        
        if self.video_temp_path and os.path.exists(self.video_temp_path):
            try:
                # Даем время на освобождение файла
                QTimer.singleShot(100, lambda: self.safe_remove_file(self.video_temp_path))
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")

    def safe_remove_file(self, filepath):
        """Безопасное удаление файла"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Не удалось удалить файл {filepath}: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cleanup_and_exit()

    def closeEvent(self, event):
        self.cleanup_resources()
        super().closeEvent(event)

    def cleanup_and_exit(self):
        """Очистка и выход из приложения"""
        self.cleanup_resources()
        QApplication.restoreOverrideCursor()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Инициализация БД
    loop.run_until_complete(init_db())

    window = VideoDisplayApp()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()