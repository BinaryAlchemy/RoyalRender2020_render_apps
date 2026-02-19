# Author: Royal Render, Holger Schoenberger, Binary Alchemy
# Last change: %rrVersion%
# Copyright (c) Holger Schoenberger - Binary Alchemy
#
# Installation:
# Please copy the RR_ComfyUI_Plugin folder into your custom_nodes folder of ComfyUI.
# Note: If the RR_ROOT environment variable ist not defined (created when installing something via rrWorkstationInstaller), 
# then you need to edit the function "def getRR_Root()" top update the path to RR.
#
# custom_nodes/
#     └── RR_ComfyUI_Plugin/
#         ├── __init__.py
#         ├── rrSubmit.py
#         ├── rrNodes.py
#         └── js/
#             ├── rr_nodes.js
#             └── rr_ui.js


import os
import json
import torch
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

#####################################################################################
# This function has to be changed if an app should show info and error dialog box   #
#####################################################################################

def writeInfo(msg):
    print(msg)

def writeError(msg):
    print(msg)





        
##############################################
# ComfyUI nodes                              #
##############################################        


class rrSeed:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "iteration_idx": ("INT", {"default": 1, "min": 0, "max": 999999}),
            },
            "hidden": {"is_commandline": ("BOOLEAN", {"default": False})}
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("SEED", "SEED_2", "iteration_idx")
    FUNCTION = "generate_seed"
    CATEGORY = "RoyalRender"

    def generate_seed(self, base_seed, iteration_idx, is_commandline=False):
        
        
        def calc(seed, iteration, offset):
            mask = 0xFFFFFFFFFFFFFFFF
            prime = 2654435761
            # combine Seed, iteration_idx and offset
            # Simulate 32-bit multiplication overflow
            scrambled_iter = iteration * prime           
            s = (seed ^ scrambled_iter ^ offset) & mask
            if s == 0: s = 0x5B6A6A55544C46B7
            s ^= (s >> 12) & mask
            s ^= (s << 25) & mask
            s ^= (s >> 27) & mask
            return (s * 0x2545f4914f6cdd1d) & mask

        # Berechne zwei verschiedene Seeds
        seed_1 = calc(base_seed, iteration_idx, 0)
        seed_2 = calc(base_seed, iteration_idx, 0xACE) # Ein fester Offset für den zweiten Seed
        #Debug print to the console
        print(f"[rrSeed] Start: {base_seed} | Iter: {iteration_idx} | Final: {seed_1}")
        return  (seed_1, seed_2, iteration_idx)
        
        
class rrSaveImage:
    def __init__(self):
        self.output_dir = "output"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "Comfy"}),
                "iteration_idx": ("INT", {"default": 1, "min": 0, "max": 999999}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "RoyalRender"

    def save_images(self, images, filename_prefix="[workflowName]", iteration_idx=1, prompt=None, extra_pnginfo=None):
        results = list()
        for image in images:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for x in extra_pnginfo:
                    metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            # Format: Prefix.####.png (Standard for Render Farm image sequences)
            file = f"{filename_prefix}.{iteration_idx:04d}.png"
            full_path = os.path.join(self.output_dir, file)
            
            img.save(full_path, pnginfo=metadata, compress_level=4)
            results.append({"filename": file, "subfolder": "", "type": "output"})

        return {"ui": {"images": results}}

class rrSaveVideo:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("VIDEO",),
                "filename_prefix": ("STRING", {"default": "Comfy"}),
                # Added 'auto' and 'mp4' to match original node options
                "format": (["auto", "mp4"],),
                # Added 'auto' and 'h264' to match original node options
                "codec": (["auto", "h264", "libx264", "libx265"],),
            },
            "optional": {
                "iteration_idx": ("INT", {"default": 1}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video_output"
    OUTPUT_NODE = True
    CATEGORY = "RoyalRender"

    def save_video_output(self, video, filename_prefix, format, codec, iteration_idx=1, prompt=None, extra_pnginfo=None):
        # LOGIC: Royal Render requires sequences for frame-by-frame rendering.
        # Even if 'mp4' or 'auto' is selected, we output PNGs. 
        # The filename_prefix will indicate the intended format for the RR Assembler.
        
        is_video = format in ["auto", "mp4"]
        prefix = f"{filename_prefix}_seq" if is_video else filename_prefix
        
        # Always use rrSaveImage logic for farm stability
        return rrSaveImage().save_images(
            images=video, 
            filename_prefix=prefix, 
            iteration_idx=iteration_idx, 
            prompt=prompt, 
            extra_pnginfo=extra_pnginfo
        )
        

NODE_CLASS_MAPPINGS = {
    "rrSeed": rrSeed,
    "rrSaveImage": rrSaveImage,
    "rrSaveVideo": rrSaveVideo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "rrSeed": "rrSeed",
    "rrSaveImage": "rrSaveImage",
    "rrSaveVideo": "rrSaveVideo (or Sequence)"
}
    