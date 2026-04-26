import numpy as np
import io
import base64
from PIL import Image
import time
import requests
#transforms frame and gives numpy frame out
#connect with api_url


class ColabAPI:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.max_retries = 3
        self.retry_delay = 2
        # header to bypass ngrok warning page
        self.headers = {
            "ngrok-skip-browser-warning": "true",
            "Content-Type": "application/json"
        }
    
    def process_frame(self, frame, max_retries=None):
        retries = max_retries or self.max_retries
        
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        
        for attempt in range(retries):
            try:
                resp = requests.post(
                    self.api_url,
                    json={"mask": img_b64},
                    headers=self.headers, 
                    timeout=120
                )
                
                print(f"Response status: {resp.status_code}")
                resp.raise_for_status()
                
                result = resp.json()
                if 'error' in result:
                    raise Exception(f"API error: {result['error']}")
                
                img_data = base64.b64decode(result['image'])
                result_img = Image.open(io.BytesIO(img_data))
                return np.array(result_img)
                
            except requests.exceptions.ConnectionError as e:
                if attempt < retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Colab API not reachable. URL: {self.api_url}")
                    
            except requests.exceptions.Timeout:
                print(f"timeout (attempt {attempt + 1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise Exception("Request timed out")
    
    def health_check(self):
        try:
            resp = requests.get(f"{self.api_url}/health", headers=self.headers, timeout=5)
            return resp.status_code == 200
        except:
            return False
""""
class ColabAPI:
    def __init__(self, api_url: str, timeout: int = 10):
        self.api_url = api_url
        self.timeout = timeout
        self.prev_frame = None
        self.blend_coef = 0.5
    def reset(self):
        self.prev_frame = None

    @staticmethod
    def encode(array: np.ndarray) -> str:
        #handling blocks of bytes
        buf = BytesIO()
        img = Image.fromarray(array)
        img.save(buf, format='PNG')
        #return buf.getvalue()
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    
    @staticmethod
    def decode(b64: str) -> np.ndarray:
        data = base64.b64decode(b64)
        return np.array(Image.open(BytesIO(data)).convert("RGB"))
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        b64 = self.encode(frame)
        #send to api and get response
        resp = requests.post(self.api_url, 
                                json={'mask': b64},
                                timeout=self.timeout,
                                headers={"ngrok-skip-browser-warning": "true"},)
        resp.raise_for_status()
        out = self.decode(resp.json()['image'])        #resize
        if out.shape[:2] != frame.shape[:2]:
                out = np.array(
                    Image.fromarray(out).resize(
                        (frame.shape[1], frame.shape[0]), Image.BICUBIC)
                )
        #blendng with previous frame
        if self.prev_frame is not None:
            out = (
                    self.blend_coef * self.prev_frame.astype(np.float32) +
                                (1 - self.blend_coef) * out.astype(np.float32)
                ).astype(np.uint8)
            self.prev_frame = out
            return out



"""