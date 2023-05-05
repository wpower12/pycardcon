import argparse
from pycardcon import render
from pycardcon.errors import InvalidTextRegion
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import json

ap = argparse.ArgumentParser()
ap.add_argument('root_dir', type=str)
ap.add_argument('resource_dir', type=str)
ap.add_argument('output_dir', type=str)
args = ap.parse_args()

root_dir = args.root_dir
resource_dir = args.resource_dir
out_dir = args.output_dir


class CardRenderHandler(FileSystemEventHandler):

    def __init__(self, dir_to_watch, dir_of_resources, dir_to_output_to):
        super().__init__()
        self.dir = dir_to_watch
        self.dir_resources = dir_of_resources
        self.dir_output = dir_to_output_to
        self.fn_cache = dict()
        self.render_timeout = 2.0

    def on_modified(self, event):
        if not event.is_directory and '~' not in event.src_path:
            card_fn = event.src_path.split("/")[-1]

            if card_fn not in self.fn_cache or (time.monotonic() - self.fn_cache[card_fn]) > self.render_timeout:
                self.fn_cache[card_fn] = time.monotonic()
                print(f"rendering: {card_fn}")
                try:
                    render.render_card_json(self.dir, card_fn, self.dir_resources, self.dir_output)
                    print(f"rendered:  {card_fn}")
                    self.rendering = False
                except json.decoder.JSONDecodeError as e_json:
                    print(f"error reading {card_fn}:")
                    print(e_json)
                except InvalidTextRegion as e_invalidtr:
                    print(f"malformed text region in {card_fn}.")
                    print(e_invalidtr)
                except FileNotFoundError as e_fnf:
                    # TODO - Custom error that includes what part of the pipeline had the error.
                    # TODO - Suggested fixes like the other custom exception
                    print(f"error loading resource while rendering {card_fn}.")
                    print(e_fnf)
                except KeyError as e_ke:
                    # TODO - Custom error that include what part of the pipeline/json file had the error.
                    # TODO - Suggested fixes...
                    print(f"missing json key while rendering {card_fn}.")
                    print(e_ke)


print(f"watching: {root_dir}")
event_handler = CardRenderHandler(root_dir, resource_dir, out_dir)
observer = Observer()
observer.schedule(event_handler, root_dir)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
