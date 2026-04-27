from datasets import base_dataset
from models import base_model, create_model
from options import base_options
import torch
from pathlib import Path
from util import html
from options.test_options import TestOptions
from util.visualizer import save_images

def run_inference(model_name: str, dataset_name: str, checkpoint_path: str, output_dir: str):
    opt = base_options.TestOptions().parse()
    opt.name = model_name
    opt.results_dir = output_dir
    opt.dataset_mode = dataset_name
    opt.set_input(data)
    opt.model = 'test'

    opt.no_dropout = True #necessary for CycleGAN
    opt.num_test = float('inf')   
    
    opt.num_threads = 0
    opt.batch_size = 1
    opt.serial_batches = True
    opt.no_flip = True
    opt.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    dataset = base_dataset.create_dataset(opt)
    model = create_model(opt)
    model.setup(opt)
    
    web_dir = Path(opt.results_dir) / opt.name / "test_latest"
    webpage = html.HTML(web_dir, f"Experiment = {opt.name}")
    
    if opt.eval:
        model.eval()
    
    for i, data in enumerate(dataset):
        model.set_input(data)
        model.test()
        visuals = model.get_current_visuals()
        img_path = model.get_image_paths()
        save_images(webpage, visuals, img_path, aspect_ratio=opt.aspect_ratio, width=opt.display_winsize)
        print(f'Processing image {i+1}: {img_path[0]}')
    
    webpage.save()
    print(f"Results saved to {web_dir}")

if __name__ == "__main__":
    run_inference(
        model_name="horse2zebra_pretrained",
        dataset_name="test",
        checkpoint_path="./checkpoints/horse2zebra_pretrained/latest_net_G.pth",
        output_dir="./my_results"
    )