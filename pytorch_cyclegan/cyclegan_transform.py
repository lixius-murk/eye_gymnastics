#transformer = CycleGANTransform(checkpoint_path="checkpoints/my_model/latest_net_G.pth")
#out_frame = transformer.transform(numpy_rgb_frame)


import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from PIL import Image
import torchvision.transforms as transforms


class ResnetBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.block = nn.Sequential(
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim),
            nn.ReLU(True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(dim, dim, 3),
            nn.InstanceNorm2d(dim),
        )

    def forward(self, x):
        return x + self.block(x)


class ResnetGenerator(nn.Module):
    def __init__(self, input_nc=3, output_nc=3, ngf=64, n_blocks=9):
        super().__init__()
        layers = [
            nn.ReflectionPad2d(3),
            nn.Conv2d(input_nc, ngf, 7),
            nn.InstanceNorm2d(ngf),
            nn.ReLU(True),
        ]
        for i in range(2):
            mult = 2 ** i
            layers += [
                nn.Conv2d(ngf * mult, ngf * mult * 2, 3, stride=2, padding=1),
                nn.InstanceNorm2d(ngf * mult * 2),
                nn.ReLU(True),
            ]
        mult = 4
        for _ in range(n_blocks):
            layers.append(ResnetBlock(ngf * mult))
        for i in range(2):
            mult = 2 ** (2 - i)
            layers += [
                nn.ConvTranspose2d(ngf * mult, ngf * mult // 2, 3,
                                   stride=2, padding=1, output_padding=1),
                nn.InstanceNorm2d(ngf * mult // 2),
                nn.ReLU(True),
            ]
        layers += [
            nn.ReflectionPad2d(3),
            nn.Conv2d(ngf, output_nc, 7),
            nn.Tanh(),
        ]
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)



class CycleGANTransform:

    #Loads a single CycleGAN generator checkpoint and transforms numpy frames
    def __init__(
        self,
        checkpoint_path: str,
        input_size: int | None = 256,
        n_blocks: int = 9,
    ):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.input_size = input_size

        self.net = ResnetGenerator(n_blocks=n_blocks).to(self.device)
        self._load_weights(checkpoint_path)
        self.net.eval()

        t = []
        if input_size:
            t.append(transforms.Resize(input_size, transforms.InterpolationMode.BICUBIC))
        t += [
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
        self.preprocess = transforms.Compose(t)

    def _load_weights(self, path: str):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        state = torch.load(path, map_location=self.device)
        if "state_dict" in state:
            state = state["state_dict"]
        self.net.load_state_dict(state)
        print(f"[CycleGANTransform] Loaded weights from {path}")

    @torch.no_grad()
    def transform(self, frame: np.ndarray) -> np.ndarray:
        """
        Transform a single HxWx3 uint8 RGB numpy frame.
        Returns HxWx3 uint8 RGB numpy array at the *original* input resolution.
        """
        orig_h, orig_w = frame.shape[:2]
        pil = Image.fromarray(frame)
        tensor = self.preprocess(pil).unsqueeze(0).to(self.device)  # 1x3xHxW

        out = self.net(tensor)  # 1x3xHxW, range [-1, 1]

        out = out.squeeze(0).cpu().float()
        out = (out * 0.5 + 0.5).clamp(0, 1)
        out_np = (out.permute(1, 2, 0).numpy() * 255).astype(np.uint8)

        if self.input_size and (orig_h != self.input_size or orig_w != self.input_size):
            out_pil = Image.fromarray(out_np).resize(
                (orig_w, orig_h), Image.BICUBIC
            )
            out_np = np.array(out_pil)

        return out_np


class CycleGANTransformRepo:
    def __init__(self, model_name: str, checkpoints_dir: str, input_size: int = 256):
        import sys
        cyclegan_root = Path(__file__).parent / "CycleGAN"
        if str(cyclegan_root) not in sys.path:
            sys.path.insert(0, str(cyclegan_root))

        from options.test_options import TestOptions
        from models import create_model

        opt = TestOptions().parse([]) #empty args to use defaults
        opt.name = model_name
        opt.checkpoints_dir = checkpoints_dir
        opt.model = "test"          # single-direction test model
        opt.no_dropout = True
        opt.num_threads = 0
        opt.batch_size = 1
        opt.serial_batches = True
        opt.no_flip = True
        opt.display_id = -1
        opt.isTrain = False
        opt.gpu_ids = [0] if torch.cuda.is_available() else []

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.opt = opt
        self.model = create_model(opt)
        self.model.setup(opt)
        self.model.eval()
        self.input_size = input_size

        self.preprocess = transforms.Compose([
            transforms.Resize(input_size, transforms.InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ])

    @torch.no_grad()
    def transform(self, frame: np.ndarray) -> np.ndarray:
        orig_h, orig_w = frame.shape[:2]
        pil = Image.fromarray(frame)
        tensor = self.preprocess(pil).unsqueeze(0)

        data = {"A": tensor, "A_paths": ["frame"]}
        self.model.set_input(data)
        self.model.test()
        visuals = self.model.get_current_visuals()

        out = visuals["fake_B"].squeeze(0).cpu().float()
        out = (out * 0.5 + 0.5).clamp(0, 1)
        out_np = (out.permute(1, 2, 0).numpy() * 255).astype(np.uint8)

        if orig_h != self.input_size or orig_w != self.input_size:
            out_np = np.array(
                Image.fromarray(out_np).resize((orig_w, orig_h), Image.BICUBIC)
            )
        return out_np
