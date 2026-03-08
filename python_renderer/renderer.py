import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.render.render import EyeGymnasticsOne, EyeGymnasticsTwo
from enumData.bltype import blType
import src.render.movements

def launch_app(argv):
    user_vision       = blType[argv[2]]
    selected_movement = src.render.movements.movements[argv[3]]
    width             = int(argv[4])
    height            = int(argv[5])

    if argv[1] == "1":
        app = EyeGymnasticsOne(bl_type=user_vision, movement_func=selected_movement,
                               width=width, height=height)
    else:
        app = EyeGymnasticsTwo(bl_type=user_vision, movement_func=selected_movement,
                               width=width, height=height)
    try:
        print(f"Starting session for {user_vision.name}...")
        app.run()
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    launch_app(sys.argv)