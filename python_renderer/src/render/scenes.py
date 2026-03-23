import os


ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../assets")
SCENE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../scenes")


scenes = {
    "boat": os.path.join(SCENE_DIR, "boat.json"),
    "bubble":  os.path.join(SCENE_DIR, "bubble.json"),
    "bug-on-grass": os.path.join(SCENE_DIR, "bug-on-grass.json"),
    "butterfly": os.path.join(SCENE_DIR, "butterfly.json"),
    "mouse": os.path.join(SCENE_DIR, "mouse.json"),
    "plane-in-sky": os.path.join(SCENE_DIR, "plane-in-sky.json"),
    "star-in-sky": os.path.join(SCENE_DIR, "star-in-sky.json"),
}
