# hypergan_transform.py
import sys
import numpy as np
import torch
from pathlib import Path
from PIL import Image
import torchvision.transforms as T

class HyPERGANTransform:
    def __init__(
        self,
        repo_path: str,
        checkpoint_path: str,
        input_size: int | None = 512,
    ):
        repo_path = str(Path(repo_path).resolve())
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)

        from main import UNetGenerator
        self.GeneratorClass = UNetGenerator
        
        self.device = torch.device("cpu")
        self.input_size = input_size

        self.net = self.GeneratorClass().to(self.device)
        
        state = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        
        if "generator" in state:
            state = state["generator"]
        elif "state_dict" in state:
            state = state["state_dict"]
        elif "model" in state:
            state = state["model"]
        
        self.net.load_state_dict(state)
        self.net.eval()
        t = []
        if input_size:
            t.append(T.Resize((input_size, input_size), T.InterpolationMode.BICUBIC))
        t += [
            T.ToTensor(),
            T.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
        self.preprocess = T.Compose(t)

    def _create_unet_generator(self):
        """Define UNet generator if import fails"""
        import torch.nn as nn
        
        class DoubleConv(nn.Module):
            def __init__(self, in_ch, out_ch):
                super().__init__()
                self.conv = nn.Sequential(
                    nn.Conv2d(in_ch, out_ch, 3, padding=1),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(inplace=True),
                    nn.Conv2d(out_ch, out_ch, 3, padding=1),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(inplace=True)
                )
            def forward(self, x):
                return self.conv(x)
        
        class UNetGenerator(nn.Module):
            def __init__(self, in_ch=3, out_ch=3, features=[64, 128, 256, 512]):
                super().__init__()
                self.downs = nn.ModuleList()
                self.ups = nn.ModuleList()
                self.pool = nn.MaxPool2d(2)
                
                #downsampling
                for feature in features:
                    self.downs.append(DoubleConv(in_ch, feature))
                    in_ch = feature
                
                self.bottleneck = DoubleConv(features[-1], features[-1] * 2)
                
                #upsampling
                for feature in reversed(features):
                    self.ups.append(
                        nn.ConvTranspose2d(feature * 2, feature, kernel_size=2, stride=2)
                    )
                    self.ups.append(DoubleConv(feature * 2, feature))
                
                self.final_conv = nn.Conv2d(features[0], out_ch, kernel_size=1)
            
            def forward(self, x):
                skip_connections = []
                for down in self.downs:
                    x = down(x)
                    skip_connections.append(x)
                    x = self.pool(x)
                
                x = self.bottleneck(x)
                skip_connections = skip_connections[::-1]
                
                for idx in range(0, len(self.ups), 2):
                    x = self.ups[idx](x)
                    skip = skip_connections[idx // 2]
                    if x.shape != skip.shape:
                        x = nn.functional.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=True)
                    concat = torch.cat((skip, x), dim=1)
                    x = self.ups[idx + 1](concat)
                
                return self.final_conv(x)
        
        return UNetGenerator

    @torch.no_grad()
    def transform(self, frame: np.ndarray) -> np.ndarray:
        """Process a single frame"""
        orig_h, orig_w = frame.shape[:2]
        pil = Image.fromarray(frame)
        tensor = self.preprocess(pil).unsqueeze(0).to(self.device)

        out = self.net(tensor)
        out = (out * 0.5 + 0.5).clamp(0, 1)
        out_np = (out.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

        if self.input_size and (orig_h != self.input_size or orig_w != self.input_size):
            out_np = np.array(
                Image.fromarray(out_np).resize((orig_w, orig_h), Image.BICUBIC)
            )
        return out_np

    def reset(self):
        pass