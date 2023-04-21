import argparse
import os
from pymse import util
from pymse import render
import dearpygui.dearpygui as dpg

from pymse import app

ap = argparse.ArgumentParser()
ap.add_argument('root_dir', type=str)
ap.add_argument('resource_dir', type=str)
ap.add_argument('output_dir', type=str)
args = ap.parse_args()

# root_dir = args.root_dir
# resource_dir = args.resource_dir
# out_dir = args.output_dir

# app.run(args.root_dir, args.resource_dir, args.output_dir)

for item in os.listdir(args.root_dir):
    if ".json" in item:
        print(item)
        render.render_card_json(args.root_dir,
                                item,
                                args.resource_dir,
                                args.output_dir)
