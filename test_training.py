import sys
import time
from pathlib import Path

#sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from tabs.training_tab.training_tab import TrainingTab

def main():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Training Tab Test")
    window.setGeometry(100, 100, 1920, 1200)
    
    training_tab = TrainingTab()
    test_plan = {
            "disease": "Healthy",
            "scene": "test",
            "bl_type": "Healthy",
            "object_scale": 1.0,
            "speed_factor": 1.0,
            "exercise_duration": 60,
            "exercises": [
                {"name": "circle_left", "speed": "slow"}
            ],
            "notes": ["This is a test plan for the training tab."]}
    training_tab.apply_plan(test_plan)
    
    window.setCentralWidget(training_tab)
    window.show()
    
    training_tab._launch_gymnastics()
    
    
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
