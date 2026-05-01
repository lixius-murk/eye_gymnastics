import base64
import threading
import time
import numpy as np
import requests
from io import BytesIO
from PIL import Image
import os

class ColabSDMTransform:
    def __init__(self, api_url: str, timeout: int = 120):
        self.batch_url = api_url.rstrip("/") + "/generate_batch"
        self.single_url = api_url.rstrip("/") + "/generate"
        self.health_url = api_url.rstrip("/") + "/health"
        self.timeout = timeout
        self.headers = {
            "ngrok-skip-browser-warning": "true",
            "Content-Type": "application/json"
        }
        self._latest_results = []
        self._in_flight = False

    def check_connection(self) -> bool:
        try:
            r = requests.get(self.health_url, headers=self.headers, timeout=5)
            ok = r.status_code == 200
            print(f"[SDMTransform] {'Connected' if ok else 'Failed'}")
            return ok
        except Exception as e:
            print(f"[SDMTransform] Connection failed: {e}")
            return False

    def send_batch_sync(self, frames_batch):
        valid_frames = []
        
        if len(valid_frames) == 0:
            print("[SDMTransform] No valid frames to send")
            return []
        
        batch_b64 = []
        for frame in valid_frames:
            try:
                buf = BytesIO()
                #frame is uint8 RGB
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                if len(frame.shape) == 2 or frame.shape[-1] != 3:
                    frame = np.stack([frame, frame, frame], axis=-1)
                Image.fromarray(frame).save(buf, format="PNG")
                batch_b64.append(base64.b64encode(buf.getvalue()).decode())
            except Exception as e:
                print(f"[SDMTransform] Error encoding frame: {e}")
                batch_b64.append(None)
        
        batch_b64 = [b for b in batch_b64 if b is not None]
        
        if len(batch_b64) == 0:
            print("[SDMTransform] No frames encoded successfully")
            return []
        
        try:
            start_time = time.time()
            resp = requests.post(
                self.batch_url,
                json={"frames": batch_b64},
                headers=self.headers,
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            
            print(f"[SDMTransform] Response status={resp.status_code}, time={elapsed:.2f}s")
            resp.raise_for_status()
            
            result = resp.json()
            
            if "error" in result:
                print(f"[SDMTransform] Server error: {result['error']}")
                return []
            
            if "frames" not in result:
                print(f"[SDMTransform] Unexpected response format: {result.keys()}")
                return []
            
            generated_images = []
            for idx, img_b64 in enumerate(result["frames"]):
                if img_b64 is None:
                    print(f"[SDMTransform] Frame {idx} result is None")
                    generated_images.append(None)
                else:
                    try:
                        img_data = base64.b64decode(img_b64)
                        img = Image.open(BytesIO(img_data)).convert("RGB")
                        generated_images.append(np.array(img))
                    except Exception as e:
                        print(f"[SDMTransform] Error decoding frame {idx}: {e}")
                        generated_images.append(None)
            
            print(f"[SDMTransform] Received {len(generated_images)} images")
            return generated_images
            
        except requests.exceptions.Timeout:
            print(f"[SDMTransform] Request timeout after {self.timeout}s")
            return []
        except Exception as e:
            print(f"[SDMTransform] Request failed: {e}")
            return []