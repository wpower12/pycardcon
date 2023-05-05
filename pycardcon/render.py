import os.path

from PIL import Image, ImageDraw, ImageFont
from cairosvg import svg2png
from io import BytesIO

from pycardcon.text import parse
from pycardcon.util import read_card
from pycardcon.errors import InvalidTextRegion

SYMBOL_RATIO = 0.865
DROP_SHADOW_RATIO = 0.1
LINE_MARGIN_RATIO = 0.02
NEWLINE_MARGIN = 0.5
DESCENDER_ADJUSTMENT_RATIO = 0.1
FONT_REDUCTION_ON_FAIL_RATIO = 0.9

## Helper Methods ##
def scale_art_bounds(art_obj, art_img, card_size):
    art_x = int(art_obj['x']*card_size[0])
    art_y = int(art_obj['y']*card_size[1])
    art_w = int(art_img.size[0]*art_obj['zoom'])
    art_h = int(art_img.size[1]*art_obj['zoom'])
    return art_x, art_y, art_w, art_h


def scale_bounds(bounds, size):
    x = bounds['x'] * size[0]
    y = bounds['y'] * size[1]
    w = bounds['width'] * size[0]
    h = bounds['height'] * size[1]
    return int(x), int(y), int(w), int(h)


"""
Handles the case's where it's a svg and needs to be converted. 
"""
def read_maybe_svg_file(mask_fn):
    if ".svg" in mask_fn:
        with open(mask_fn, 'rb') as mask_f:
            mask_svg = svg2png(mask_f.read())
        return Image.open(BytesIO(mask_svg))
    else:
        return Image.open(mask_fn)


## Per-Card-Component Draw Methods. ##
def draw_art(card_img, art_obj, img_root):
    if art_obj['src'] == '':
        return card_img

    # art_fn = f"{img_root}/{art_obj['src']}"
    art_path = os.path.join(img_root, art_obj['src'])
    art_img = Image.open(art_path)

    art_x, art_y, art_w, art_h = scale_art_bounds(art_obj, art_img, card_img.size)
    card_img.paste(art_img.resize((art_w, art_h)), (art_x, art_y))
    return card_img


def draw_frames(card_img, frames):
    for frame in frames:
        frame_padded = Image.new("RGBA", card_img.size, (0, 0, 0, 0))
        f_x, f_y, f_w, f_h = scale_bounds(frame['bounds'], card_img.size)

        if 'alphaShade' in frame:
            shade_img = Image.new("RGBA", (f_w, f_h), frame['value'])
            frame_padded.paste(shade_img, (f_x, f_y))
        else:
            frame_img = Image.open(os.path.join(frame['fn']))
            frame_img = frame_img.resize((f_w, f_h))
            frame_padded.paste(frame_img, (f_x, f_y))

            blending = False
            if 'blend' in frame:
                blending = True
                blend_img = Image.open(os.path.join(frame['blend']['fn']))
                blend_img = blend_img.resize(frame_padded.size)
                masked_blend = blend_img  # Done to get rid of another 'blending?' check later.

            if 'masks' in frame:
                masked_blend = Image.new("RGBA", frame_padded.size)
                masked_frame = Image.new("RGBA", frame_padded.size)
                for mask in frame['masks']:
                    mask_img = read_maybe_svg_file(os.path.join(mask['fn']))
                    mask_img = mask_img.convert("RGBA")
                    mask_img = mask_img.resize(frame_padded.size)
                    masked_frame.paste(frame_padded, mask=mask_img)

                    if blending:
                        masked_blend.paste(blend_img, mask=mask_img)

                frame_padded = masked_frame

            if blending:
                # If blending w.o masking, this would result in a 'blank' alpha w.o the commented line above.
                frame_padded.putalpha(masked_blend.getchannel("A"))

        card_img.alpha_composite(frame_padded)
    return card_img


def draw_text(card_img, card, resource_root):
    for text_region in card['textRegions']:
        render_text_region(card_img, card, text_region, card['textRegions'][text_region], resource_root)
    return card_img


def render_text_region(img, card_obj, text_region_name, text_region, resource_root):

    for field in ['text', 'size', 'width', 'height', 'x', 'y']:
        if field not in text_region:
            raise InvalidTextRegion(text_region_name, field)

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
        text_font_path = os.path.join(resource_root, "fonts", text_region['font'])
        text_font = ImageFont.truetype(text_font_path, fontsize)
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
                cur_y_tr += int(fontsize*(1+NEWLINE_MARGIN))

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
                with open(os.path.join(token['path_to_img']), 'rb') as mask_f:
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
                    font_path = os.path.join(resource_root, "fonts", text_region['font'])
                else:
                    font_str = text_region['font'].replace(".ttf", "-i.ttf")
                    font_path = os.path.join(resource_root, "fonts", font_str)
                text_font = ImageFont.truetype(font_path, fontsize)

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


def draw_set_symbol(img, card, resource_root):
    symbol_fn = f"{card['infoSet']}_{card['infoRarity']}.png"
    symbol_path = os.path.join(resource_root, "setSymbols", card['infoSet'], symbol_fn)

    ss_img = Image.open(symbol_path)
    set_symbol_meta = card['setSymbol']
    ss_x, ss_y, ss_w, ss_h = scale_art_bounds(set_symbol_meta, ss_img, img.size)
    img.alpha_composite(ss_img.resize((ss_w, ss_h)), (ss_x, ss_y))
    return img


def draw_bottom_region(img, card_obj, resource_root):
    card_draw = ImageDraw.Draw(img)

    # Top Left
    tl_obj = card_obj['bottomInfo']['topLeft']
    tl_fontsize = int(tl_obj['size']*img.size[1])
    font_path = os.path.join(resource_root, "fonts", "gotham-medium.ttf")
    set_font = ImageFont.truetype(font_path, tl_fontsize)
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
    brush_path = os.path.join(resource_root, "manaSymbols", "artistbrush.svg")
    with open(brush_path, 'rb') as brush_f:
        brush_svg = svg2png(brush_f.read())
    brush_img = Image.open(BytesIO(brush_svg))
    brush_zoom = (tl_fontsize/brush_img.size[1])*0.8
    brush_img = brush_img.resize((int(brush_img.size[0]*brush_zoom), int(brush_img.size[1]*brush_zoom)))
    img.alpha_composite(brush_img, (ml_x, ml_y))
    ml_x += brush_img.size[0]
    ml_x += card_draw.textlength(" ", font=set_font)

    # artist line
    artist_fontsize = int(card_obj['bottomInfo']['midLeft']['size']*img.size[1])
    art_font_path = os.path.join(resource_root, "fonts", "beleren-bsc.ttf")
    artist_font = ImageFont.truetype(art_font_path, artist_fontsize)
    # TODO - fix this hack. without it the artist line sinks below flush. might be an issue with anchor choice?
    ml_y -= 12
    card_draw.text((ml_x, ml_y), card_obj['art']['artist'], font=artist_font, fill=card_obj['bottomInfo']['midLeft']['color'])

    # bottom left - NOTE FOR SALE
    bl_x = tl_x
    bl_y = int(card_obj['bottomInfo']['bottomLeft']['y']*img.size[1])
    nfs_font_path = os.path.join(resource_root, "fonts", "gotham-medium.ttf")
    nfs_font = ImageFont.truetype(nfs_font_path, int(0.8*tl_fontsize))
    card_draw.text((bl_x, bl_y),
                   card_obj['bottomInfo']['bottomLeft']['text'],
                   font=nfs_font,
                   fill=card_obj['bottomInfo']['bottomLeft']['color'])
    return img


def render_card_json(card_dir, card_fn, resource_path, output_dir):
    card_obj = read_card(os.path.join(card_dir, card_fn), resource_path)['data']
    card_img = Image.new("RGBA", (card_obj['card']['width'], card_obj['card']['height']), (0, 0, 0, 0))

    card_img = draw_art(card_img, card_obj['art'], card_dir)
    card_img = draw_frames(card_img, card_obj['frames'])
    card_img = draw_text(card_img, card_obj, resource_path)
    card_img = draw_set_symbol(card_img, card_obj, resource_path)
    card_img = draw_bottom_region(card_img, card_obj, resource_path)

    output_path = os.path.join(output_dir, f"{card_obj['textRegions']['display-title']['text']}.png")
    card_img.save(output_path)
