import dearpygui.dearpygui as dpg
import os
from pycardcon import util

def run(root_dir, resource_dir, out_dir):
    dpg.create_context()
    dpg.create_viewport(title='Custom Title', width=1200, height=900)

    def card_click_callback(sender, app_data, user_data):
        card_path = f"{root_dir}/{user_data['card_fn']}"
        card_obj = util.read_card(card_path, resource_dir)['data']
        # card_ui_info = list(reversed(util.read_card_for_gui(card_path, resource_dir)))
        card_ui_info = util.read_card_for_gui(card_path, resource_dir)
        card_img_path = f"{out_dir}/{card_obj['textRegions']['display-title']['text']}.png"

        width, height, channels, data = dpg.load_image(card_img_path)

        # dpg.delete_item("card_img_tag", children_only=False)
        if dpg.does_alias_exist("card_img_tag"):
            dpg.remove_alias("card_img_tag")
        with dpg.texture_registry():
            dpg.add_static_texture(width=width, height=height, default_value=data, tag="card_img_tag")

        card_w = int(card_obj['card']['width'] * 0.40)
        card_h = int(card_obj['card']['height'] * 0.40)
        card_win_x = int(1200 - card_w * 1.05)
        card_data_w = card_win_x - 200

        cur_y = 10
        dpg.delete_item("card-data", children_only=False)
        with dpg.window(label="Card-Data", tag="card-data", width=card_data_w, pos=(200, 0), height=900):

            with dpg.table(header_row=True,
                           borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
                dpg.add_table_column(label="Name")

                to_render = [(card_ui_info.pop(0), 0)]
                while len(to_render) > 0:
                    ui_item, il = to_render.pop(0)
                    with dpg.table_row():
                        with dpg.table_cell():
                            dpg.add_text(f"{'  ' * il}{ui_item['title']}")

                    if 'children' in ui_item:
                        for c in ui_item['children']:
                            to_render.insert(0, (c, il + 1))

                    if len(card_ui_info) > 0:
                        to_render.append((card_ui_info.pop(0), 0))

        dpg.delete_item("card-preview", children_only=False)
        with dpg.window(label="Card-Preview", tag="card-preview", width=int(card_w * 1.05), height=int(card_h * 1.05),
                        pos=(card_win_x, 0)):
            dpg.add_image("card_img_tag", width=card_w, height=card_h)

    with dpg.window(label="Cards", width=200):

        with dpg.table(header_row=True,
                       borders_outerH=True, borders_innerV=True, borders_innerH=True, borders_outerV=True):
            dpg.add_table_column(label="Name")
            for item in os.listdir(root_dir):
                if ".json" in item:
                    with dpg.table_row():
                        with dpg.table_cell():
                            # dpg.add_text(f"{item}")
                            dpg.add_button(label=f"{item}", callback=card_click_callback, user_data={
                                'card_fn': item
                            })

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()