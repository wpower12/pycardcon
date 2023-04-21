import json
from PIL import Image, ImageDraw, ImageFont
from cairosvg import svg2png
from io import BytesIO

from pymse.text import parse
from pymse.util import read_card

SYMBOL_RATIO = 0.865
DROP_SHADOW_RATIO = 0.1
LINE_MARGIN_RATIO = 0.02
DESCENDER_ADJUSTMENT_RATIO = 0.1
FONT_REDUCTION_ON_FAIL_RATIO = 0.9

def draw_art(card_img, art_obj, img_root):
    art_fn = f"{img_root}/{art_obj['src']}"
    art_img = Image.open(art_fn)

    art_x = int(art_obj['x']*card_img.size[0])
    art_y = int(art_obj['y']*card_img.size[1])
    art_w = int(art_img.size[0]*art_obj['zoom'])
    art_h = int(art_img.size[1]*art_obj['zoom'])

    card_img.paste(art_img.resize((art_w, art_h)), (art_x, art_y))
    return card_img


def draw_frames(card_img, frames):
    for frame in frames:
        frame_padded = Image.new("RGBA", (card_img.size[0], card_img.size[1]), (0, 0, 0, 0))
        f_x = frame['bounds']['x'] * card_img.size[0]
        f_y = frame['bounds']['y'] * card_img.size[1]
        f_w = frame['bounds']['width'] * card_img.size[0]
        f_h = frame['bounds']['height'] * card_img.size[1]

        if 'alphaShade' in frame:
            shade_img = Image.new("RGBA", (int(f_w), int(f_h)), frame['value'])
            frame_padded.paste(shade_img, (int(f_x), int(f_y)))
        else:
            frame_img = Image.open(frame['fn'])
            frame_img = frame_img.resize((int(f_w), int(f_h)))

            if 'selfMask' in frame and frame['selfMask']:
                frame_padded.paste(frame_img, (int(f_x), int(f_y)))
            else:
                frame_padded.paste(frame_img, (int(f_x), int(f_y)))

            if 'masks' in frame:
                current_frame = Image.new("RGBA", (card_img.size[0], card_img.size[1]), (0, 0, 0, 0))
                for mask in frame['masks']:
                    if ".svg" in mask['fn']:
                        with open(mask['fn'], 'rb') as mask_f:
                            mask_svg = svg2png(mask_f.read())
                        mask_img = Image.open(BytesIO(mask_svg))
                    else:
                        mask_img = Image.open(mask['fn'])
                    mask_img = mask_img.convert("RGBA")

                    current_frame = Image.composite(frame_padded, current_frame, mask=mask_img)

                frame_padded.paste(current_frame, (int(f_x), int(f_y)))
                frame_padded = current_frame

        card_img = Image.alpha_composite(card_img, frame_padded)
    return card_img


def draw_text(card_img, card, resource_root):
    for text_region in card['textRegions']:
        render_text_region(card_img, card, card['textRegions'][text_region], resource_root)
    return card_img


def render_text_region(img, card_obj, text_region, resource_root):
    tokens   = parse(text_region['text'], resource_root)
    fontsize = int(text_region['size']*img.size[1])
    tr_w     = int(text_region['width']*img.size[0])

    if 'color' in text_region:
        tr_color = text_region['color']
    else:
        tr_color = "black"

    if 'align' not in text_region:
        text_region['align'] = 'left'
    if 'verticalAlign' not in text_region:
        text_region['verticalAlign'] = 'top'

    def attempt_render(text_image):
        text_font = ImageFont.truetype(f"resources/fonts/{text_region['font']}", fontsize)
        cur_line_img  = Image.new("RGBA", (tr_w, int(fontsize*(1+DESCENDER_ADJUSTMENT_RATIO))), (0, 0, 0, 0))
        cur_line_draw = ImageDraw.Draw(cur_line_img)
        cur_x, cur_y_tr = 0, 0

        def paint_cur_line(cl_img, c_x, c_y):
            if text_region['align'] == "left":
                text_image.alpha_composite(cl_img, dest=(0, c_y))
            elif text_region['align'] == 'right':
                dx = tr_w - c_x
                text_image.alpha_composite(cl_img, dest=(dx, c_y))
            else:  # Center Aligned
                dx = int(0.5*(tr_w - c_x))
                text_image.alpha_composite(cl_img, dest=(dx, c_y))

        for token in tokens:
            if token['token_type'] == 'newline':
                paint_cur_line(cur_line_img, cur_x, cur_y_tr)
                cur_x = 0
                cur_y_tr += int(fontsize * (1 + 3 * LINE_MARGIN_RATIO))

                cur_line_img  = Image.new("RGBA", (tr_w, int(fontsize*(1+DESCENDER_ADJUSTMENT_RATIO))), (0, 0, 0, 0))
                cur_line_draw = ImageDraw.Draw(cur_line_img)

            if token['token_type'] == 'str':
                token_str   = f"{token['content']}{token['whitespace']}"
                token_width = cur_line_draw.textlength(token_str, text_font)

                if cur_x+token_width > tr_w:
                    paint_cur_line(cur_line_img, cur_x, cur_y_tr)
                    cur_x = 0
                    cur_y_tr += int(fontsize * (1 + 3 * LINE_MARGIN_RATIO))
                    cur_line_img = Image.new("RGBA", (tr_w, int(fontsize*(1+DESCENDER_ADJUSTMENT_RATIO))), (0, 0, 0, 0))
                    cur_line_draw = ImageDraw.Draw(cur_line_img)

                # cur_line_draw.text((cur_x, 0), token_str, font=text_font, fill="black")
                cur_line_draw.text((cur_x, fontsize*(1+DESCENDER_ADJUSTMENT_RATIO)), token_str, font=text_font, fill=tr_color, anchor='ld')
                cur_x += int(token_width)

            if token['token_type'] == 'symbol':
                with open(token['path_to_img'], 'rb') as mask_f:
                    mana_svg = svg2png(mask_f.read())

                symbol_size = int(fontsize*SYMBOL_RATIO)
                mana_y = int((fontsize-symbol_size)*0.5)

                if cur_x+symbol_size > tr_w:
                    paint_cur_line(cur_line_img, cur_x, cur_y_tr)
                    cur_x = 0
                    cur_y_tr += int(fontsize * (1 + 3 * LINE_MARGIN_RATIO))
                    cur_line_img = Image.new("RGBA", (tr_w, int(fontsize*(1+DESCENDER_ADJUSTMENT_RATIO))), (0, 0, 0, 0))
                    cur_line_draw = ImageDraw.Draw(cur_line_img)

                mana_img = Image.open(BytesIO(mana_svg))
                mana_img = mana_img.resize((symbol_size, symbol_size))

                # Drop shadow
                if text_region['dropShadows']:
                    ds_x0, ds_y0 = cur_x, mana_y+DROP_SHADOW_RATIO*symbol_size
                    ds_x1, ds_y1 = cur_x+symbol_size, mana_y + (DROP_SHADOW_RATIO+1)*symbol_size
                    cur_line_draw.ellipse((ds_x0, ds_y0, ds_x1, ds_y1), fill='black')

                cur_line_img.alpha_composite(mana_img, (cur_x, mana_y))

                cur_x += symbol_size
                if token['whitespace'] != "":
                    cur_x += int(cur_line_draw.textlength(token['whitespace'], text_font))
                else:
                    cur_x += int(0.1*symbol_size)

            if token['token_type'] == 'card_meta':
                if token['card_field'] == "display-title":
                    token_str = f"{card_obj['textRegions']['display-title']['text']}{token['whitespace']}"
                    token_width = cur_line_draw.textlength(token_str, text_font)

                    if cur_x + token_width > tr_w:
                        paint_cur_line(cur_line_img, cur_x, cur_y_tr)
                        cur_x = 0
                        cur_y_tr += int(fontsize * (1 + 3 * LINE_MARGIN_RATIO))
                        cur_line_img = Image.new("RGBA", (tr_w, int(fontsize*(1+DESCENDER_ADJUSTMENT_RATIO))), (0, 0, 0, 0))
                        cur_line_draw = ImageDraw.Draw(cur_line_img)

                    # cur_line_draw.text((cur_x, 0), token_str, font=text_font, fill="black")
                    cur_line_draw.text((cur_x, fontsize * (1 + DESCENDER_ADJUSTMENT_RATIO)), token_str, font=text_font,
                                       fill=tr_color, anchor='ld')
                    cur_x += int(token_width)

            if token['token_type'] == 'font_change':
                if token['val'] == 0:
                    text_font = ImageFont.truetype(f"resources/fonts/{text_region['font']}", fontsize)
                else:
                    font_str = text_region['font'].replace(".ttf", "-i.ttf")
                    text_font = ImageFont.truetype(f"resources/fonts/{font_str}", fontsize)

            if cur_y_tr+fontsize > text_region['height']*img.size[1]:
                return False, 0

        paint_cur_line(cur_line_img, cur_x, cur_y_tr)
        return True, cur_y_tr

    tr_size = (int(text_region['width']*img.size[0]), int(text_region['height']*img.size[1]))
    t_img = Image.new("RGBA", tr_size, (0, 0, 0, 0))

    done, last_text_y = attempt_render(t_img)
    while not done:
        fontsize = int(fontsize*FONT_REDUCTION_ON_FAIL_RATIO)
        t_img = Image.new("RGBA", tr_size, (0, 0, 0, 0))
        done, last_text_y = attempt_render(t_img)

    if text_region['verticalAlign'] == "top":
        tr_loc = (int(text_region['x']*img.size[0]), int(text_region['y']*img.size[1]))
    elif text_region['verticalAlign'] == "center":
        dy = text_region['height']*img.size[1]-(last_text_y+fontsize)
        tr_loc = (int(text_region['x']*img.size[0]), int(text_region['y']*img.size[1]+0.5*dy))
    else:  # Bottom Vertical Align
        dy = text_region['height']*img.size[1]-(last_text_y+fontsize)
        tr_loc = (int(text_region['x']*img.size[0]), int(text_region['y']*img.size[1]+dy))

    img.alpha_composite(t_img, tr_loc)
    return img


def draw_set_symbol(img, set_symbol_meta, img_root):
    # This is basically a copy/paste of the art one, but in the
    # future I might have it handle something like automatically
    # mapping a rarity value to an image? idk.
    ss_fn = f"{img_root}/{set_symbol_meta['src']}"
    ss_img = Image.open(ss_fn)
    ss_x = int(set_symbol_meta['x']*img.size[0])
    ss_y = int(set_symbol_meta['y']*img.size[1])
    ss_w = int(ss_img.size[0]*set_symbol_meta['zoom'])
    ss_h = int(ss_img.size[1]*set_symbol_meta['zoom'])
    # ss_img.resize((ss_w, ss_h)), (ss_x, ss_y)
    # ss_img.re
    img.alpha_composite(ss_img.resize((ss_w, ss_h)), (ss_x, ss_y))
    return img


def draw_bottom_region(img, card_obj, resource_root):
    card_draw = ImageDraw.Draw(img)

    # Top Left
    tl_obj = card_obj['bottomInfo']['topLeft']
    tl_fontsize = int(tl_obj['size']*img.size[1])
    set_font = ImageFont.truetype(f"{resource_root}/fonts/gotham-medium.ttf", tl_fontsize)
    tl_x = int(tl_obj['x']*img.size[0])
    tl_y = int(tl_obj['y']*img.size[1])
    tl_str = f"{card_obj['infoNumber']:<16}{card_obj['infoRarity']}"
    card_draw.text((tl_x, tl_y), tl_str, font=set_font)

    # Mid-Left
    # <SET * LANG (set_font)><BRUSH IMG><ARTIST STR (same font as title?)>
    ml_obj = card_obj['bottomInfo']['midLeft']
    ml_x = tl_x
    ml_y = int(ml_obj['y']*img.size[1])

    # set info
    ml_set_str = f"{card_obj['infoSet']}*{card_obj['infoLanguage']} "
    card_draw.text((ml_x, ml_y), ml_set_str, font=set_font)
    ml_x += int(card_draw.textlength(ml_set_str, font=set_font))

    # artist brush
    brush_fn = f"{resource_root}/manaSymbols/artistbrush.svg"
    with open(brush_fn, 'rb') as brush_f:
        brush_svg = svg2png(brush_f.read())
    brush_img = Image.open(BytesIO(brush_svg))
    brush_zoom = (tl_fontsize/brush_img.size[1])*0.8
    brush_img = brush_img.resize((int(brush_img.size[0]*brush_zoom), int(brush_img.size[1]*brush_zoom)))
    img.alpha_composite(brush_img, (ml_x, ml_y))
    ml_x += brush_img.size[0]
    ml_x += card_draw.textlength(" ", font=set_font)

    # artist line
    artist_fontsize = int(card_obj['bottomInfo']['midLeft']['size']*img.size[1])
    artist_font = ImageFont.truetype(f"{resource_root}/fonts/beleren-bsc.ttf", artist_fontsize)
    # TODO - fix this hack. without it the artist line sinks below flush. might be an issue with anchor choice?
    ml_y -= 12
    card_draw.text((ml_x, ml_y), card_obj['art']['artist'], font=artist_font, fill=card_obj['bottomInfo']['midLeft']['color'])

    # bottom left - NOTE FOR SALE
    bl_x = tl_x
    bl_y = int(card_obj['bottomInfo']['bottomLeft']['y']*img.size[1])
    nfs_font = ImageFont.truetype(f"{resource_root}/fonts/gotham-medium.ttf", int(0.8*tl_fontsize))
    card_draw.text((bl_x, bl_y),
                   card_obj['bottomInfo']['bottomLeft']['text'],
                   font=nfs_font,
                   fill=card_obj['bottomInfo']['bottomLeft']['color'])
    return img


def render_card_json(card_dir, card_fn, resource_path, output_dir):
    card_obj = read_card(f"{card_dir}/{card_fn}", resource_path)['data']

    card_img = Image.new("RGBA", (card_obj['card']['width'], card_obj['card']['height']), (0, 0, 0, 0))

    card_img = draw_art(card_img, card_obj['art'], card_dir)
    card_img = draw_frames(card_img, card_obj['frames'])
    card_img = draw_text(card_img, card_obj, resource_path)
    card_img = draw_set_symbol(card_img, card_obj['setSymbol'], card_dir)
    card_img = draw_bottom_region(card_img, card_obj, resource_path)

    output_fn = f"{output_dir}/{card_obj['textRegions']['display-title']['text']}.png"
    card_img.save(output_fn)


def render_frame_regions(meta_path, frame):
    with open(f"{meta_path}/frame_pack_meta.json", 'rb') as f:
        meta_obj = json.load(f)

    frame_img = Image.open(f"{meta_path}/{meta_obj['frames'][frame]['path']}")
    frame_img = frame_img.convert("RGB")
    frame_draw = ImageDraw.Draw(frame_img, "RGBA")

    frame_dg_name = meta_obj['frames'][frame]['defaultGroup']
    frame_dg = meta_obj['defaultGroups'][frame_dg_name]

    for text_region_name in frame_dg['defaultTextFields']:
        text_region = frame_dg['defaultTextFields'][text_region_name]

        tr_x  = int(text_region['x']*frame_img.size[0])
        tr_y  = int(text_region['y']*frame_img.size[1])
        tr_x2 = tr_x+int(text_region['width']*frame_img.size[0])
        tr_y2 = tr_y+int(text_region['height']*frame_img.size[1])

        frame_draw.rectangle((tr_x, tr_y, tr_x2, tr_y2), fill=(100, 100, 100, 125))

    frame_img.save("test_view_frame.png")
