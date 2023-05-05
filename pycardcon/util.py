import json

"""
Reads a cards json from the fn, and searches for the necessary frame packs to build up the full set of
meta-data needed to render a frame. This means finding the right default group for a frame and copying
over the defaults for the bounds, zooms, alignment, text fields, etc...

TODO - Make Planeswalker text regions read defaults and overwrites correctly
TODO - Make saga text regions read defaults and overwrites correctly 
"""
def read_card(card_fn, resources_root):
    with open(card_fn, 'rb') as card_f:
        card = json.load(card_f)

    processed_frames = []  # Collecting frames as they are expanded or created
    loyalty_frames   = []  # These are the 'foreground' frames added by things like loyalty or chapter icons.
    for frame in card['data']['frames']:
        frame_meta = load_fp_meta_file(frame['framePack'], resources_root)
        frame_dg = frame_meta["frames"][frame['frame']]["defaultGroup"]
        frame_defaults = frame_meta["defaultGroups"][frame_dg]
        frame['bounds'] = frame_defaults['defaultBounds']

        # Resolve full path to the frame image file.
        frame['fn'] = f"{resources_root}/{frame['framePack']}/{frame_meta['frames'][frame['frame']]['path']}"

        if 'usingTexts' in frame:
            for text_field in frame['usingTexts']:
                copy_or_overwrite_defaults(card['data']['textRegions'][text_field],
                                           frame_defaults['defaultTextFields'][text_field])

        if 'usingPWTexts' in frame:
            if 'pwRegion' not in card['data']:
                card['data']['pwRegion'] = {
                    'bounds': {}
                }

            for key in frame_defaults['defaultPWRegion']['bounds']:
                val = frame_defaults['defaultPWRegion']['bounds'][key]
                if 'pwRegion' in frame and 'bounds' in frame['pwRegion'] and key in frame['pwRegion']['bounds']:
                    card['data']['pwRegion']['bounds'][key] = frame['pwRegion']['bounds'][key]
                else:
                    card['data']['pwRegion']['bounds'][key] = val

            for key in ['textOffsetX', 'textOffsetY', 'size', 'font']:
                val = frame_defaults['defaultPWRegion'][key]
                if key not in frame['pwRegion']:
                    card['data']['pwRegion'][key] = val
                else:
                    card['data']['pwRegion'][key] = frame['pwRegion'][key]

            # for now, lets make a rule that you either use all or none for the
            # vertical share field. Up to the user to make it sum to 1.
            region_n = 1
            num_regions = len(frame['usingPWTexts'])
            pw_region_x = card['data']['pwRegion']['bounds']['x']
            pw_region_y = card['data']['pwRegion']['bounds']['y']
            pw_region_w = card['data']['pwRegion']['bounds']['width']
            pw_region_h = card['data']['pwRegion']['bounds']['height']

            cur_region_y = pw_region_y
            for pw_region_name in frame['usingPWTexts']:
                card['data']['textRegions'][pw_region_name]['pwRegion'] = True

                if 'verticalShare' not in card['data']['textRegions'][pw_region_name]:
                    card['data']['textRegions'][pw_region_name]['verticalShare'] = (1.0/num_regions)

                pw_region_vshare = card['data']['textRegions'][pw_region_name]['verticalShare']

                # TODO - Handle arbitary planeswalker packs/boundry packs
                boundary_pack = "planeswalker"
                bp_meta_fn = f"{resources_root}/frames/{boundary_pack}/frame_pack_meta.json"
                with open(bp_meta_fn, 'rb') as meta_f:
                    bp_meta = json.load(meta_f)

                # TODO - Make these be read from a defaults file for a planeswalker pack.
                if region_n % 2 == 0:
                    # Darker
                    boundary_frame_name = "Ability Line Even"
                    v = 170
                    shade_rgba = (v, v, v, 172)
                else:
                    # 'Lighter'
                    boundary_frame_name = "Ability Line Odd"
                    v = 242
                    shade_rgba = (v, v, v, 172)

                bf_height = bp_meta['defaultGroups']['abilityLines']['defaultBounds']['height']

                one_px = 1.0/card['data']['card']['height']
                alpha_shade_frame = {
                    "alphaShade": True,
                    "bounds": {
                        "x": pw_region_x,
                        "y": cur_region_y,
                        "width": pw_region_w,
                        "height": pw_region_h * pw_region_vshare - 0.5*bf_height+one_px,
                    },
                    "value": shade_rgba
                }
                processed_frames.insert(0, alpha_shade_frame)

                pw_text_region = card['data']['textRegions'][pw_region_name]
                text_os_x = card['data']['pwRegion']['textOffsetX']
                text_os_y = card['data']['pwRegion']['textOffsetY']

                # TODO - Make this offset a function of the width of the loyalty symbols.
                if card['data']['textRegions'][pw_region_name]['loyaltySymbol'] != "none":
                    # Bad hardcoded value. Booooo.
                    text_os_x += 0.05

                pw_text_region['x'] = pw_region_x+text_os_x
                pw_text_region['y'] = cur_region_y+text_os_y
                pw_text_region['width'] = pw_region_w-text_os_x
                pw_text_region['height'] = pw_region_h * pw_region_vshare - 0.5*bf_height - text_os_y

                # TODO - Read these from the meta config file.
                pw_text_region['font'] = card['data']['pwRegion']['font']
                pw_text_region['size'] = card['data']['pwRegion']['size']

                ls_y = cur_region_y
                loyalty_symbol_name = card['data']['textRegions'][pw_region_name]['loyaltySymbol']
                if loyalty_symbol_name != "none":
                    ls_obj = bp_meta['frames'][loyalty_symbol_name]
                    ls_fn = f"{resources_root}/frames/{boundary_pack}/{ls_obj['path']}"
                    LS_SCALE = 105.0/51.0  # TODO - more hardcoded fixes to replace
                    LS_HEIGHT = 0.073
                    LS_WIDTH  = LS_HEIGHT*LS_SCALE
                    loyalty_frames.append({
                        'fn': ls_fn,
                        'bounds': {
                            'x': pw_region_x-LS_WIDTH*0.61,
                            'y': ls_y+0.025*LS_HEIGHT,
                            'width': LS_WIDTH,
                            'height': LS_HEIGHT
                        }
                    })

                    # Add text region for ability change text_region
                    pw_la_tr_name = f"{pw_region_name}_loyalty_text"
                    card['data']['textRegions'][pw_la_tr_name] = {
                        'x': pw_region_x-LS_WIDTH*0.61,
                        'y': ls_y+0.1*LS_HEIGHT,
                        'width': 0.15,
                        'height': 0.05,
                        'font': "beleren-b.ttf",
                        'size': 0.03,
                        'text': pw_text_region['loyaltyText'],
                        'color': 'white',
                        "verticalAlign": "center",
                        'align': 'center'
                    }

                    if 'textOffsetX' in pw_text_region:
                        new_x = pw_text_region['textOffsetX']+card['data']['textRegions'][pw_la_tr_name]['x']
                        card['data']['textRegions'][pw_la_tr_name]['x'] = new_x

                    if 'textOffsetY' in pw_text_region:
                        new_y = pw_text_region['textOffsetY']+card['data']['textRegions'][pw_la_tr_name]['y']
                        card['data']['textRegions'][pw_la_tr_name]['y'] = new_y

                # Ability Line
                cur_region_y += pw_region_h * pw_region_vshare - 0.5*bf_height
                if region_n < num_regions:
                    b_frame = bp_meta['frames'][boundary_frame_name]
                    b_frame['bounds'] = {
                        'x': pw_region_x,
                        'y': cur_region_y,
                        'width': pw_region_w,
                        'height': bf_height
                    }
                    b_frame['selfMask'] = True
                    b_frame['fn'] = f"{resources_root}/frames/{boundary_pack}/{b_frame['path']}"
                    processed_frames.append(b_frame)
                    cur_region_y += bf_height
                region_n += 1

        if 'saga' in frame:
            chapter_region = frame_defaults['defaultChapterRegion']

            # For saga text field, add text-regions and chapter frames
            num_chapters = len(frame['saga']['chapters'])
            chapter_vertical_frac = 1.0/num_chapters
            cur_chapter_y = chapter_region['y']
            for chapter_tr_name in frame['saga']['chapters']:
                # Need to add the defaults for a text region to the text region,
                # and calculate and place its x, y, width, etc..
                chapter_tr = card['data']['textRegions'][chapter_tr_name]
                chapter_tr['x'] = chapter_region['x']
                chapter_tr['y'] = cur_chapter_y
                chapter_tr['width'] = chapter_region['width']
                cr_height = chapter_vertical_frac*chapter_region['height']
                chapter_tr['height'] = cr_height
                chapter_tr['size'] = chapter_region['size']
                chapter_tr['font'] = chapter_region['font']
                chapter_tr['verticalAlign'] = chapter_region['verticalAlign']

                chap_sym_meta = load_fp_meta_file("frames/saga", resources_root)

                chap_bar_fn = f"{resources_root}/frames/saga/sagaDivider.png"
                chap_bar_defaults = chap_sym_meta['defaultGroups']['sagaBar']

                # Need to add saga divider bar at the top of each chapter text region
                chapter_bar_frame = {
                    "fn": chap_bar_fn,
                    "bounds": {
                        'x': chap_bar_defaults['defaultBounds']['x'],
                        'y': cur_chapter_y,
                        'width': chap_bar_defaults['defaultBounds']['width'],
                        'height': chap_bar_defaults['defaultBounds']['height'],
                    },
                    "masks": [
                        {
                            "mask": "saga Text Area Full",
                            "framePack": "frames/saga",
                        }
                    ]

                }
                mask_fp_meta = load_fp_meta_file("frames/saga", resources_root)
                mask_meta_info = mask_fp_meta['masks']["saga Text Area Full"]
                chapter_bar_frame['masks'][0]['fn'] = f"{resources_root}/frames/saga/{mask_meta_info['path']}"
                mask_dg = mask_fp_meta['defaultGroups'][mask_meta_info['defaultGroup']]
                copy_or_overwrite_defaults(chapter_bar_frame['masks'][0], mask_dg)
                loyalty_frames.append(chapter_bar_frame)

                if len(chapter_tr['chapterSymbols']) > 0:
                    chap_sym_defaults = chap_sym_meta['defaultGroups']['sagaChapter']
                    # TODO - Pull this out of the defaults file.
                    chap_sym_fn = f"{resources_root}/frames/saga/sagaChapter.png"
                    num_symbols = len(chapter_tr['chapterSymbols'])
                    sym_height = chap_sym_defaults['defaultBounds']['height']
                    spacing = (cr_height-num_symbols*sym_height)/(num_symbols+1.0)
                    cur_sym_y = cur_chapter_y
                    cur_sym_y += spacing
                    for chapter_symbol_name in chapter_tr['chapterSymbols']:
                        # New Frame
                        sym_frame = {
                            'fn': chap_sym_fn,
                            'bounds': {
                                'x': chap_sym_defaults['defaultBounds']['x'],
                                'y': cur_sym_y,
                                'width': chap_sym_defaults['defaultBounds']['width'],
                                'height': chap_sym_defaults['defaultBounds']['height']
                            }
                        }
                        loyalty_frames.append(sym_frame)

                        # New Text Region
                        sym_tr_name = f"{chapter_symbol_name}_symbol_tr"
                        sym_text_x_os = 0.005
                        sym_tr = {
                            'x': chap_sym_defaults['defaultBounds']['x']+sym_text_x_os,
                            'y': cur_sym_y,
                            'width': chap_sym_defaults['defaultBounds']['width'],
                            'height': chap_sym_defaults['defaultBounds']['height'],
                            "font": "plantin-semibold.otf",
                            'size': 0.03,
                            'text': chapter_symbol_name,
                            'color': 'black',
                            "verticalAlign": "center",
                            'align': 'center'
                        }
                        card['data']['textRegions'][sym_tr_name] = sym_tr

                        # Increment Height for next loop
                        cur_sym_y += sym_height+spacing

                cur_chapter_y += cr_height

        if 'masks' in frame:
            for mask in frame['masks']:
                # Open mask meta file, read its default group, and copy/overwrite to the user mask obj
                mask_fp_meta = load_fp_meta_file(mask['framePack'], resources_root)
                mask_meta_info = mask_fp_meta['masks'][mask['mask']]
                mask['fn'] = f"{resources_root}/{mask['framePack']}/{mask_meta_info['path']}"
                mask_dg = mask_fp_meta['defaultGroups'][mask_meta_info['defaultGroup']]
                copy_or_overwrite_defaults(mask, mask_dg)

        if "defaultComplementary" in frame_defaults:
            for comp_frame in frame_defaults['defaultComplementary']:
                comp_frame_meta = load_fp_meta_file(f"frames/{comp_frame['framePack']}", resources_root)
                comp_frame_fn = comp_frame_meta['frames'][comp_frame['frame']]['path']
                comp_frame['fn'] = f"{resources_root}/frames/{comp_frame['framePack']}/{comp_frame_fn}"

                # NOTE - This may be a source of issues if any of the complimentary frames are more complicated.
                # Might require copy/overwriting defaults from files to fix.
                comp_frame_dg = comp_frame_meta['defaultGroups'][comp_frame_meta['frames'][comp_frame['frame']]['defaultGroup']]
                comp_frame_bounds = comp_frame_dg['defaultBounds']
                comp_frame['bounds'] = comp_frame_bounds

                processed_frames.append(comp_frame)

        if "usingSetSymbol" in frame and frame['usingSetSymbol']:
            copy_or_overwrite_defaults(card['data']['setSymbol'], frame_defaults['defaultSetSymbol'])

        if "usingBottomInfo" in frame and frame['usingBottomInfo']:
            if 'bottomInfo' not in card['data']:
                card['data']['bottomInfo'] = {}

            for bottom_region in frame_defaults['defaultBottomInfo']:
                if bottom_region not in card['data']['bottomInfo']:
                    card['data']['bottomInfo'][bottom_region] = {}

                copy_or_overwrite_defaults(card['data']['bottomInfo'][bottom_region],
                                           frame_defaults['defaultBottomInfo'][bottom_region])

        processed_frames.append(frame)

    if len(loyalty_frames) > 0:
        processed_frames.extend(loyalty_frames)
    card['data']['frames'] = processed_frames

    # TODO - Add in set data, resolve fn from the set information here so we don't do it at render time.

    return card


def copy_or_overwrite_defaults(user_obj, defaults_obj):
    for key in defaults_obj:
        val = defaults_obj[key]
        if key not in user_obj:
            user_obj[key] = val


def load_fp_meta_file(frame_pack_path, resource_dir):
    fp_meta_fn = f"{resource_dir}/{frame_pack_path}/frame_pack_meta.json"
    with open(fp_meta_fn, 'rb') as meta_f:
        meta_obj = json.load(meta_f)
    return meta_obj
