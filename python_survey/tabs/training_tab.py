import os
from datetime import datetime
import subprocess
from pathlib import Path
import mmap
import struct
import threading
import time
import sys

from python_renderer.sharedMemoryFileWriter import SharedMemoryWriter
from pytorch_cyclegan.cyclegan_transform import CycleGANTransform  

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsView
)

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QThread, Signal, QTime
from PySide6.QtGui import QFont, QColor, QLinearGradient, QPainter, QPen, QPixmap, QImage
import numpy as np

class SharedMemoryReader:

    def __init__(self, name="frames"):
        self.name = name
        self.map_file = None
        self.fd = None
        self.path = f"/dev/shm/{self.name}"
        self.last_frame_id = -1
        self.HEADER_SIZE = SharedMemoryWriter.HEADER_SIZE
        self.HEADER_FORMAT = SharedMemoryWriter.HEADER_FORMAT
        self.total_size = 0
    def _connect(self):
        if self.map_file:
            return True

        if not os.path.exists(self.path):
            return False

        try:
            fd = os.open(self.path, os.O_RDONLY)
            header = os.read(fd, self.HEADER_SIZE)
            if len(header) < self.HEADER_SIZE:
                os.close(fd)
                return False

            counter, flag, w, h = struct.unpack(self.HEADER_FORMAT, header)

            if w == 0 or h == 0:
                os.close(fd)
                return False

            frame_size = w * h * 3
            self.total_size = self.HEADER_SIZE + frame_size
            self.map_file = mmap.mmap(fd, self.total_size, mmap.MAP_SHARED, mmap.PROT_READ)
            self.fd = fd

            self.last_frame_id = counter - 1

            print(f"[SharedMemoryReader] Connected ({w}x{h})")
            return True

        except Exception as e:
            print(f"[SharedMemoryReader] Connect error: {e}")
            return False

    def read_frame(self):
        if not self._connect():
            return None

        try:
            for _ in range(5):
                self.map_file.seek(0)
                header = self.map_file.read(self.HEADER_SIZE)
                counter, flag, w, h = struct.unpack(self.HEADER_FORMAT, header)

                if flag:
                    continue  # writer busy

                frame_size = w * h * 3

                self.map_file.seek(self.HEADER_SIZE)
                frame_data = self.map_file.read(frame_size)

                self.map_file.seek(0)
                header2 = self.map_file.read(self.HEADER_SIZE)
                counter2, flag2, _, _ = struct.unpack(self.HEADER_FORMAT, header2)

                if flag2:
                    continue

                if counter != counter2:
                    continue

                if counter == self.last_frame_id:
                    return None

                self.last_frame_id = counter

                print(f"[Reader] frame {counter}")

                frame = np.frombuffer(frame_data, dtype=np.uint8)
                return frame.reshape((h, w, 3))

            return None

        except Exception as e:
            print(f"[SharedMemoryReader] Read error: {e}")
            return None

    def close(self):
        if self.map_file:
            self.map_file.close()
            self.map_file = None
        if self.fd:
            os.close(self.fd)
            self.fd = None



class ProcessMonitorThread(QThread):
    def __init__(self, process):
        super().__init__()
        self.process = process

    def _read_stream(self, stream, prefix):
        while True:
            line = stream.readline()
            if not line:
                break
            print(f"{prefix} {line.decode(errors='ignore').rstrip()}")

    def run(self):
        threads = []

        if self.process.stdout:
            t_out = threading.Thread(
                target=self._read_stream,
                args=(self.process.stdout, "[Renderer]"),
                daemon=True
            )
            t_out.start()
            threads.append(t_out)

        if self.process.stderr:
            t_err = threading.Thread(
                target=self._read_stream,
                args=(self.process.stderr, "[Renderer STDERR]"),
                daemon=True
            )
            t_err.start()
            threads.append(t_err)

        self.process.wait()

        for t in threads:
            t.join(timeout=1)

        print(f"[ProcessMonitorThread] Exit code: {self.process.poll()}")

    def stop(self):
        self.wait(2000)


class FrameReaderThread(QThread):
    frameReady = Signal(QPixmap)

    def __init__(self, cyclegan_transform=None):

        super().__init__()
        self.reader = SharedMemoryReader("frames")
        self.running = False
        self.transform = cyclegan_transform  

    def run(self):
        self.running = True
        while self.running:
            frame = self.reader.read_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            try:
                if self.transform is not None:
                    frame = self.transform.transform(frame)

                h, w = frame.shape[:2]
                if not frame.flags['C_CONTIGUOUS']:
                    frame = np.ascontiguousarray(frame)

                qt_image = QImage(frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image.copy())
                if not pixmap.isNull():
                    self.frameReady.emit(pixmap)

            except Exception as e:
                print(f"[FrameReaderThread] Error: {e}")

            time.sleep(0.002)

        self.reader.close()

    def stop(self):
        self.running = False
        self.wait(2000)


def _shadow(blur=24, dy=6, alpha=80):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, dy)
    s.setColor(QColor(0, 0, 0, alpha))
    return s

class ParamCard(QFrame):
    def __init__(self, label: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                background: #1e1e1e;
                border-radius: 10px;
                border: none;
            }
        """)
        self.setGraphicsEffect(_shadow(16, 4, 60))

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 16, 0)
        row.setSpacing(14)

        strip = QFrame()
        strip.setFixedWidth(3)
        strip.setMinimumHeight(80)
        strip.setStyleSheet(f"background: {accent}; border-radius: 2px; border: none;")
        row.addWidget(strip)

        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 12, 0, 12)

        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {accent}; letter-spacing: 1.5px; background: transparent;")
        col.addWidget(lbl)

        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        val.setStyleSheet("color: #ffffff; background: transparent;")
        col.addWidget(val)

        row.addLayout(col)

class ExerciseCard(QFrame):
    SPEED_LABELS = {
        "very_slow":("Очень медленно", "#7C5CBF"),
        "slow":("Медленно", "#5B8DEF"),
        "medium":("Стандартно", "#3DB87A"),
    }
    EXERCISE_LABELS = {
        "circle_right": "Круг по часовой",
        "circle_left": "Круг против часовой",
        "horizontal": "Горизонталь",
        "vertical": "Вертикаль",
        "zigzag": "Зигзаг",
        "clock": "Циферблат",
        "two_diagonals": "Диагонали",
        "diagonal_up": "Диагональ вверх",
        "diagonal_down": "Диагональ вниз",
        "rectangle": "Прямоугольник",
    }

    def __init__(self, exercise: dict, index: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)

        speed = exercise.get("speed", "medium")
        name = exercise.get("name", "")
        label, color = self.SPEED_LABELS.get(speed, ("Стандартно", "#3DB87A"))
        ex_label = self.EXERCISE_LABELS.get(name, name)

        self.setStyleSheet("""
            QFrame {
                background: #181818;
                border-radius: 10px;
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(12)

        num = QLabel(f"{index:02d}")
        num.setFixedWidth(28)
        num.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        num.setStyleSheet(f"color: {color}; background: transparent;")
        row.addWidget(num)

        name_lbl = QLabel(ex_label)
        name_lbl.setFont(QFont("Segoe UI", 11))
        name_lbl.setStyleSheet("color: #cccccc; background: transparent;")
        row.addWidget(name_lbl, stretch=1)

        speed_lbl = QLabel(label)
        speed_lbl.setFont(QFont("Segoe UI", 9))
        speed_lbl.setStyleSheet(f"""
            color: {color};
            background: {color}22;
            border-radius: 6px;
            padding: 3px 10px;
        """)
        row.addWidget(speed_lbl)

class LaunchButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(52)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5B8DEF, stop:1 #7C5CBF
                );
                color: #ffffff;
                border: none;
                border-radius: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a7de0, stop:1 #6a4aaf
                );
            }
            QPushButton:pressed {
                background: #3a6dd0;
            }
            QPushButton:disabled {
                background: #222;
                color: #444;
            }
        """)
        self.setGraphicsEffect(_shadow(20, 6, 100))

class TrainingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._exercise_plan = {}
        self._frame_reader_thread = None
        self._process_monitor_thread = None
        self._renderer_process = None
        self._cyclegan = None 
        self._build_ui()
        self.setWindowModality(Qt.ApplicationModal)
        self.HEADER_SIZE = SharedMemoryWriter.HEADER_SIZE
        self.HEADER_FORMAT = SharedMemoryWriter.HEADER_FORMAT

        checkpoint = Path("checkpoints/my_model/latest_net_G.pth")
        if checkpoint.exists():
            try:
                self._cyclegan = CycleGANTransform(
                    checkpoint_path=str(checkpoint),
                    input_size=256,
                )
            except Exception as e:
                print(f"[TrainingTab] CycleGAN not loaded: {e}")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._video_frame = QFrame()
        self._video_frame.setVisible(False)
        self._video_frame.setStyleSheet("background: #000000; border: none;")
        video_lay = QVBoxLayout(self._video_frame)
        video_lay.setContentsMargins(0, 0, 0, 0)
        
        self._graphics_view = QGraphicsView()
        self._graphics_view.setStyleSheet("background: #000000; border: none;")
        self._graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._graphics_scene = QGraphicsScene()
        self._graphics_view.setScene(self._graphics_scene)
        self._graphics_pixmap_item = QGraphicsPixmapItem()
        self._graphics_scene.addItem(self._graphics_pixmap_item)
        
        video_lay.addWidget(self._graphics_view)
        
        stop_btn_container = QFrame()
        stop_btn_container.setFixedHeight(60)
        stop_btn_container.setStyleSheet("background: rgba(0, 0, 0, 200); border: none;")
        stop_lay = QHBoxLayout(stop_btn_container)
        stop_lay.setContentsMargins(24, 0, 24, 0)
        stop_lay.addStretch()
        
        self._stop_btn = LaunchButton("Остановить")
        self._stop_btn.setFixedWidth(200)
        self._stop_btn.clicked.connect(self._stop_training)
        stop_lay.addWidget(self._stop_btn)
        video_lay.addWidget(stop_btn_container, alignment=Qt.AlignmentFlag.AlignBottom)
        
        root.addWidget(self._video_frame)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(48, 36, 48, 48)
        lay.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        self._title = QLabel("Программа тренировок")
        self._title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self._title.setStyleSheet("color: #ffffff; background: transparent;")
        title_col.addWidget(self._title)

        self._subtitle = QLabel("Пройдите тестирование для загрузки персонального плана")
        self._subtitle.setFont(QFont("Segoe UI", 11))
        self._subtitle.setStyleSheet("color: #444; background: transparent;")
        title_col.addWidget(self._subtitle)

        header.addLayout(title_col, stretch=1)

        self._launch_btn = LaunchButton("Запустить гимнастику")
        self._launch_btn.setFixedWidth(240)
        self._launch_btn.clicked.connect(self._launch_gymnastics)
        header.addWidget(self._launch_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        lay.addLayout(header)
        lay.addSpacing(32)

        self._params_frame = QFrame()
        self._params_frame.setVisible(False)
        params_lay = QVBoxLayout(self._params_frame)
        params_lay.setContentsMargins(0, 0, 0, 0)
        params_lay.setSpacing(16)

        section_lbl = QLabel("ПАРАМЕТРЫ ПЛАНА")
        section_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        section_lbl.setStyleSheet("color: #888; letter-spacing: 2px; background: transparent;")
        params_lay.addWidget(section_lbl)

        self._params_grid = QGridLayout()
        self._params_grid.setSpacing(12)
        params_lay.addLayout(self._params_grid)

        lay.addWidget(self._params_frame)
        lay.addSpacing(32)

        self._exercises_frame = QFrame()
        self._exercises_frame.setVisible(False)
        ex_lay = QVBoxLayout(self._exercises_frame)
        ex_lay.setContentsMargins(0, 0, 0, 0)
        ex_lay.setSpacing(16)

        ex_header = QHBoxLayout()
        ex_section = QLabel("СПИСОК УПРАЖНЕНИЙ")
        ex_section.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        ex_section.setStyleSheet("color: #888; letter-spacing: 2px; background: transparent;")
        ex_header.addWidget(ex_section)
        ex_header.addStretch()

        self._ex_count = QLabel("")
        self._ex_count.setFont(QFont("Segoe UI", 9))
        self._ex_count.setStyleSheet("color: #444; background: transparent;")
        ex_header.addWidget(self._ex_count)
        ex_lay.addLayout(ex_header)

        self._exercises_lay = QVBoxLayout()
        self._exercises_lay.setSpacing(8)
        ex_lay.addLayout(self._exercises_lay)

        lay.addWidget(self._exercises_frame)
        lay.addSpacing(32)

        self._notes_frame = QFrame()
        self._notes_frame.setVisible(False)
        self._notes_frame.setStyleSheet("""
            QFrame {
                background: #0d1f35;
                border-radius: 14px;
            }
        """)
        notes_lay = QVBoxLayout(self._notes_frame)
        notes_lay.setContentsMargins(20, 16, 20, 16)
        notes_lay.setSpacing(8)

        notes_title = QLabel("РЕКОМЕНДАЦИИ")
        notes_title.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        notes_title.setStyleSheet("color: #5B8DEF; letter-spacing: 1.5px; background: transparent;")
        notes_lay.addWidget(notes_title)

        self._notes_label = QLabel("")
        self._notes_label.setFont(QFont("Segoe UI", 10))
        self._notes_label.setStyleSheet("color: #8aabde; background: transparent;")
        self._notes_label.setWordWrap(True)
        notes_lay.addWidget(self._notes_label)

        lay.addWidget(self._notes_frame)
        lay.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def apply_plan(self, plan: dict):
        self._exercise_plan = plan

        disease = plan.get("disease", "")
        level = plan.get("level", "")

        if disease and disease != "healthy":
            self._subtitle.setText(
                f"Персональный план  ·  {disease.capitalize()}  {level}"
            )

        self._clear_grid()
        params = [
            ("Диагноз", f"{disease} {level}", "#5B8DEF"),
            ("Фон", plan.get("background", "—"), "#7C5CBF"),
            ("Объект", plan.get("object_hex", "—"), "#3DB87A"),
            ("Масштаб", str(plan.get("object_scale", 1.0)), "#F4A261"),
            ("Скорость", f"{plan.get('speed_ms', 10)} мс", "#E63946"),
            ("Механика", plan.get("mechanic", "—"), "#48CAE4"),
        ]
        for i, (label, value, accent) in enumerate(params):
            card = ParamCard(label, value, accent)
            self._params_grid.addWidget(card, i // 3, i % 3)

        self._params_frame.setVisible(True)

        self._clear_exercises()
        exercises = plan.get("exercises", [])
        self._ex_count.setText(f"{len(exercises)} упражнений")
        for i, ex in enumerate(exercises, 1):
            card = ExerciseCard(ex, i)
            self._exercises_lay.addWidget(card)
        self._exercises_frame.setVisible(bool(exercises))

        notes = plan.get("notes", [])
        if notes:
            self._notes_label.setText("\n".join(f"• {n}" for n in notes))
            self._notes_frame.setVisible(True)

        print(f"[TrainingTab] план: {disease} {level}, "
              f"фон={plan.get('background')}, "
              f"скорость={plan.get('speed_ms')}мс")

    def _clear_grid(self):
        while self._params_grid.count():
            item = self._params_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_exercises(self):
        while self._exercises_lay.count():
            item = self._exercises_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _get_plan(self) -> dict:
        return self._exercise_plan or {
            "background": "plain_white.png",
            "object_hex": "#FFFFFF",
            "object_scale": 1.0,
            "speed_ms": 10,
        }
    def _wait_for_shared_memory(self, timeout=5.0):
        #todo windows case
        path = "/dev/shm/frames"
        start = time.time()

        while time.time() - start < timeout:
            if os.path.exists(path):
                try:
                    fd = os.open(path, os.O_RDONLY)
                    header = os.read(fd, self.HEADER_SIZE)
                    os.close(fd)

                    if len(header) == self.HEADER_SIZE:
                        counter, flag, w, h = struct.unpack(self.HEADER_FORMAT, header)
                        if w > 0 and h > 0:
                            print(f"[TrainingTab] Shared memory ready ({w}x{h})")
                            return True
                except:
                    pass

            time.sleep(0.05)

        return False
    def _launch_gymnastics(self):

        if self._renderer_process:
            self._stop_training()
            time.sleep(0.3)

        plan = self._get_plan()
        exercise = plan.get("exercises", [{}])[0]

        exercise_name = exercise.get("name", "circle_right")
        bl_type = plan.get("bl_type", "Healthy")
        scene = plan.get("background", "star").replace(".json", "").replace(".png", "")
        speed = plan.get("speed_ms", 10)

        width, height = 2000, 1000

        renderer_dir = Path(__file__).resolve().parent / "../../python_renderer"
        
        if sys.platform == "win32":
            python_exe = renderer_dir / ".venv" / "Scripts" / "python.exe"
            clean_script = renderer_dir.parent / "clean.bat"
        else:
            python_exe = renderer_dir / ".venv" / "bin" / "python3"
            clean_script = renderer_dir.parent / "clean.sh"
        
        renderer_script = renderer_dir / "renderer.py"
        
        if clean_script.exists():
            try:
                if sys.platform == "win32":
                    p = subprocess.Popen([str(clean_script)], shell=True)
                else:
                    p = subprocess.Popen([str(clean_script)])
                p.wait(timeout=5)
                print(f"[TrainingTab] Cleaned environment")
            except Exception as e:
                print(f"[TrainingTab] Warning: Clean script failed: {e}")
        args = [
            str(python_exe),
            str(renderer_script),
            "1",
            bl_type,
            exercise_name,
            scene,
            str(speed),
            str(width),
            str(height),
        ]

        print("[TrainingTab] Launching renderer", speed)
        venv_bin = renderer_dir / ".venv" / "bin"
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(renderer_dir / ".venv")
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["PYTHONPATH"] = str(renderer_dir.parent)

        self._renderer_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(renderer_dir),
            bufsize=1,
            text=True
        )
        self._video_frame.setVisible(True)

        # monitor
        self._process_monitor_thread = ProcessMonitorThread(self._renderer_process)
        self._process_monitor_thread.start()
        # frame reader
        self._frame_reader_thread = FrameReaderThread(cyclegan_transform=self._cyclegan)
        self._frame_reader_thread.frameReady.connect(
    self._update_frame, Qt.ConnectionType.QueuedConnection
)
        self._frame_reader_thread.start()
    def _update_frame(self, pixmap: QPixmap):
        print("UI GOT FRAME", pixmap.size())
        if pixmap.isNull():
            return
        self._graphics_pixmap_item.setPixmap(pixmap)
        self._graphics_view.fitInView(
            self._graphics_pixmap_item,
            Qt.AspectRatioMode.KeepAspectRatio
        )

    def _stop_training(self):
        print("[TrainingTab] Stopping")

        if self._renderer_process:
            try:
                self._renderer_process.terminate()
                self._renderer_process.wait(timeout=1)
            except:
                self._renderer_process.kill()
            self._renderer_process = None

        if self._frame_reader_thread:
            self._frame_reader_thread.stop()
            self._frame_reader_thread = None

        if self._process_monitor_thread:
            self._process_monitor_thread.stop()
            self._process_monitor_thread = None

        self._video_frame.setFrameShape(QFrame.NoFrame)
        self._video_frame.setVisible(False)
        def _cleanup(self):
            print("[TrainingTab] Cleaning up resources...")
            try:
                self._stop_training()
            except Exception as e:
                print(f"[TrainingTab] Error during cleanup: {e}")
            print("[TrainingTab] Cleanup complete")

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
        super().closeEvent(event)
