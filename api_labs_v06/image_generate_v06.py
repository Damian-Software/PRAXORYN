#!/usr/bin/env python3
"""Controlled local-only image generation using a previously approved pipeline.

Install compatible torch/diffusers packages separately; model files must already
be present. Pipeline support varies by model and library version.
"""
import argparse
import os
from pathlib import Path
from uuid import uuid4


def validate(width: int, height: int, steps: int) -> None:
    if width < 256 or height < 256 or width > 1536 or height > 1536:
        raise ValueError('Image dimensions must be 256..1536')
    if width % 64 or height % 64:
        raise ValueError('Image dimensions must be divisible by 64')
    if not 1 <= steps <= 80:
        raise ValueError('Step count must be 1..80')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--prompt', default='A minimal geometric landscape, clean composition')
    parser.add_argument('--seed', type=int, default=73)
    parser.add_argument('--steps', type=int, default=20)
    parser.add_argument('--width', type=int, default=768)
    parser.add_argument('--height', type=int, default=768)
    parser.add_argument('--cpu-offload', action='store_true')
    args = parser.parse_args()
    validate(args.width, args.height, args.steps)
    if not args.model_dir.is_dir():
        parser.error('Model directory does not exist locally')
    if len(args.prompt) > 1000:
        parser.error('Prompt exceeds local lab limit')
    import torch
    from diffusers import DiffusionPipeline
    if not torch.cuda.is_available():
        parser.error('CUDA is not available; verify the Windows driver and WSL runtime')
    pipe = DiffusionPipeline.from_pretrained(
        str(args.model_dir), torch_dtype=torch.float16, local_files_only=True,
    )
    if args.cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe.to('cuda')
    generator = torch.Generator(device='cuda').manual_seed(args.seed)
    with torch.inference_mode():
        image = pipe(prompt=args.prompt, height=args.height, width=args.width,
                     num_inference_steps=args.steps, generator=generator).images[0]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    final = args.output_dir / (str(uuid4()) + '.png')
    temp = final.with_suffix('.tmp.png')
    image.save(temp, format='PNG')
    os.replace(temp, final)
    print('Created:', final.name)
    # The prompt and credentials are intentionally not logged.


if __name__ == '__main__':
    main()
