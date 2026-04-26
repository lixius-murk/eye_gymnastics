from PIL import Image

import requests
import numpy as np
from colab_api import ColabAPI

transform = ColabAPI("https://send-krypton-straining.ngrok-free.dev")

# Optional: Check if the API is reachable first
if transform.health_check():
    real_mask = Image.open("image.png").convert("L")
    real_mask = real_mask.resize((256, 256))
    mask_np = np.array(real_mask)

    mask_np = np.clip(mask_np, 0, 150)
    #dummy_frame = np.zeros((256, 256, 3), dtype=np.uint8)
    #dummy_frame[::2, ::2] = [255, 255, 255]  

    result = transform.process_frame(mask_np)
    Image.fromarray(result).save("generated_output.png")
    print("Saved to generated_output.png")
else:
    print("Cannot reach Colab API")
