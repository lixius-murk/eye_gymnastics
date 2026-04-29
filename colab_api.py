import base64, threading, time
import numpy as np
import requests
from io import BytesIO
from PIL import Image


class ColabSDMTransform:
    def __init__(self, api_url: str, timeout: int = 30):
        self.url = api_url
        self.health_url = api_url.rstrip("/") + "/health"
        self.timeout = timeout
        self.headers = {"ngrok-skip-browser-warning": "true"}

        self._lock = threading.Lock()
        self._latest: np.ndarray | None = None
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

    def transform(self, frame: np.ndarray) -> np.ndarray:
        # fire async request if none in flight
        if not self._in_flight:
            self._in_flight = True
            threading.Thread(
                target=self._call_api, args=(frame.copy(),), daemon=True
            ).start()
        print(f"[SDMTransform] Request sent, in-flight: {self._in_flight}")
        #latest stylized frame or raw fallback
        with self._lock:
            return self._latest if self._latest is not None else frame

    def reset(self):
        with self._lock:
            self._latest = None
        self._in_flight = False

    def _call_api(self, frame: np.ndarray):
        try:
            buf = BytesIO()
            Image.fromarray(frame).save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode()

            resp = requests.post(
                self.url,
                json={"mask": b64},
                timeout=self.timeout,
                headers=self.headers,
            )
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                print(f"[SDMTransform] Server error: {result['error']}")
                return

            data = base64.b64decode(result["image"])
            out = np.array(Image.open(BytesIO(data)).convert("RGB"))

            with self._lock:
                self._latest = out

        except Exception as e:
            print(f"[SDMTransform] Request failed: {e}")
        finally:
            self._in_flight = False