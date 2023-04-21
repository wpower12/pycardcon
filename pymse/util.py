import json

"""
Reads a cards json from the fn, and searches for the necessary frame packs to build up the full set of
meta-data needed to render a frame. This means finding the right default group for a frame and copying
over the defaults for the bounds, zooms, alignment, text fields, etc...
"""
def read_card(card_fn, resources_root):
    with open(card_fn, 'rb') as card_f:
        card = json.load(card_f)

    # Reading Frames and Text Regions
    processed_frames = []
    loyalty_frames = []
    for frame in card['data']['frames']:
        # Open the relevant frame_pack meta file.
        frame_meta_fn = f"{resources_root}/{frame['framePack']}/frame_pack_meta.json"

        with open(frame_meta_fn, 'rb') as meta_f:
            frame_meta = json.load(meta_f)

        frame_dg = frame_meta["frames"][frame['frame']]["defaultGroup"]
        frame_defaults = frame_meta["defaultGroups"][frame_dg]

        frame['fn'] = f"{resources_root}/{frame['framePack']}/{frame_meta['frames'][frame['frame']]['path']}"
        frame['bounds'] = frame_defaults['defaultBounds']

        if 'usingTexts' in frame:
            for text_field in frame['usingTexts']:
                # we assume that the text_field exists in the other part of the json.
                for key in frame_defaults['defaultTextFields'][text_field]:
                    val = frame_defaults['defaultTextFields'][text_field][key]
                    if key not in card['data']['textRegions'][text_field]:
                        card['data']['textRegions'][text_field][key] = val
                card['data']['textRegions'][text_field]['pwRegion'] = False

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
                    boundary_frame_name = "Ability Line Even"
                    shade_rgba = (170, 170, 170, 170)
                else:
                    boundary_frame_name = "Ability Line Odd"
                    shade_rgba = (242, 242, 242, 170)

                bf_height = bp_meta['defaultGroups']['abilityLines']['defaultBounds']['height']

                # We need to add a 'fake' frame somehow, that masks the image?
                alpha_shade_frame = {
                    "alphaShade": True,
                    "bounds": {
                        "x": pw_region_x,
                        "y": cur_region_y,
                        "width": pw_region_w,
                        "height": pw_region_h * pw_region_vshare - 0.5*bf_height,
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
                    LS_SCALE = 105.0/51.0 # TODO - more hardcoded fixes to replace
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
                cur_region_y += pw_region_h * pw_region_vshare - 0.505*bf_height
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

        if 'masks' in frame:
            for mask in frame['masks']:
                mask_meta_fn = f"{resources_root}/{mask['framePack']}/frame_pack_meta.json"
                with open(mask_meta_fn, 'rb') as meta_f:
                    mask_fp_meta = json.load(meta_f)

                mask_meta_info = mask_fp_meta['masks'][mask['mask']]
                mask['fn'] = f"{resources_root}/{mask['framePack']}/{mask_meta_info['path']}"

                mask_dg = mask_fp_meta['defaultGroups'][mask_meta_info['defaultGroup']]
                for key in mask_dg:
                    val = mask_dg[key]
                    if key not in mask:
                        mask[key] = val

        if "defaultComplementary" in frame_defaults:
            for comp_frame in frame_defaults['defaultComplementary']:
                comp_frame_meta_fn = f"{resources_root}/frames/{comp_frame['framePack']}/frame_pack_meta.json"
                with open(comp_frame_meta_fn, 'rb') as meta_f:
                    comp_frame_meta = json.load(meta_f)

                comp_frame_fn = comp_frame_meta['frames'][comp_frame['frame']]['path']
                comp_frame['fn'] = f"{resources_root}/frames/{comp_frame['framePack']}/{comp_frame_fn}"

                # Note to future self; might need to copy more/handle actual masks in the future.
                comp_frame_dg = comp_frame_meta['defaultGroups'][comp_frame_meta['frames'][comp_frame['frame']]['defaultGroup']]
                comp_frame_bounds = comp_frame_dg['defaultBounds']
                comp_frame['bounds'] = comp_frame_bounds

                processed_frames.append(comp_frame)

        if "usingSetSymbol" in frame and frame['usingSetSymbol']:
            for key in frame_defaults['defaultSetSymbol']:
                val = frame_defaults['defaultSetSymbol'][key]
                if key not in card['data']['setSymbol']:
                    card['data']['setSymbol'][key] = val

        if "usingBottomInfo" in frame and frame['usingBottomInfo']:
            if 'bottomInfo' not in card['data']:
                card['data']['bottomInfo'] = {}

            for bottom_region in frame_defaults['defaultBottomInfo']:
                if bottom_region not in card['data']['bottomInfo']:
                    card['data']['bottomInfo'][bottom_region] = {}

                for key in frame_defaults['defaultBottomInfo'][bottom_region]:
                    val = frame_defaults['defaultBottomInfo'][bottom_region][key]

                    if key not in card['data']['bottomInfo'][bottom_region]:
                        card['data']['bottomInfo'][bottom_region][key] = val

        processed_frames.append(frame)

    if len(loyalty_frames) > 0:
        processed_frames.extend(loyalty_frames)

    card['data']['frames'] = processed_frames

    return card

"""
Returns a card object more amenable to being used in the GUI. 

Mostly, this means returning a structure of json fields that contains information about groupings/nestings, 
defaults, and widths. 

This can then be read, more or less iteratively, to create interface elements.  

Maybe eventually this behavior becomes a flag for a single method? idk. 
"""
def read_card_for_gui(card_fn, resources_root):
    with open(card_fn, 'rb') as card_f:
        card = json.load(card_f)

    card_elem_list = []
    # We need to touch everything manually, I don't think we can avoid it. It's not that much.
    # Card-Meta (Size, Info), ArtInfo, BottomInfo, SetInfo, Frames, TextRegions

    def read_json_elem(elem, elem_path, ui_title=""):
        if ui_title == "":
            ui_title = elem_path.split(".")[-1]
        elem_obj = {
            'title': ui_title
        }
        if isinstance(elem, type({})):
            elem_obj['children'] = []
            for child_key in elem:
                child_elem = elem[child_key]
                elem_obj['children'].append(read_json_elem(child_elem, f"{elem_path}.{child_key}"))
        elif isinstance(elem, type([])):
            # we assume that any list is JUST OF STRINGS.
            # this means we manually iterate over the frames list.
            elem_obj['type'] = "str-list"
            elem_obj['value']   = elem
            elem_obj['default'] = elem
            elem_obj['json-field'] = elem_path
        else:
            elem_obj['value']   = elem
            elem_obj['default'] = elem
            elem_obj['json-field'] = elem_path
        return elem_obj

    # Card Meta
    card_elem_list.append({
        'title':   'Card Name',
        'value':   card['key'],
        'default': card['key'],
        'json-field': 'key',
        'type': 'str'
    })

    card_elem_list.append(read_json_elem(card['data']['card'], "data.card", ui_title="Card Bounds"))
    card_elem_list.append(read_json_elem(card['data']['art'], "data.art", ui_title="Art"))

    # Reading Frames and Text Regions
    processed_frames = []
    for frame in card['data']['frames']:
        # Open the relevant frame_pack meta file.
        frame_meta_fn = f"{resources_root}/{frame['framePack']}/frame_pack_meta.json"

        with open(frame_meta_fn, 'rb') as meta_f:
            frame_meta = json.load(meta_f)

        frame_dg = frame_meta["frames"][frame['frame']]["defaultGroup"]
        frame_defaults = frame_meta["defaultGroups"][frame_dg]

        frame['fn'] = f"{resources_root}/{frame['framePack']}/{frame_meta['frames'][frame['frame']]['path']}"
        frame['bounds'] = frame_defaults['defaultBounds']

        if 'usingTexts'in frame:
            for text_field in frame['usingTexts']:
                # we assume that the text_field exists in the other part of the json.
                for key in frame_defaults['defaultTextFields'][text_field]:
                    val = frame_defaults['defaultTextFields'][text_field][key]
                    if key not in card['data']['textRegions'][text_field]:
                        card['data']['textRegions'][text_field][key] = val

        if "defaultComplementary" in frame_defaults:
            for comp_frame in frame_defaults['defaultComplementary']:
                comp_frame_meta_fn = f"{resources_root}/frames/{comp_frame['framePack']}/frame_pack_meta.json"
                with open(comp_frame_meta_fn, 'rb') as meta_f:
                    comp_frame_meta = json.load(meta_f)

                comp_frame_fn = comp_frame_meta['frames'][comp_frame['frame']]['path']
                comp_frame['fn'] = f"{resources_root}/frames/{comp_frame['framePack']}/{comp_frame_fn}"
                # Note to future self; might need to copy more/handle actual masks in the future.
                comp_frame_dg = comp_frame_meta['defaultGroups'][comp_frame_meta['frames'][comp_frame['frame']]['defaultGroup']]
                comp_frame_bounds = comp_frame_dg['defaultBounds']
                comp_frame['bounds'] = comp_frame_bounds

                processed_frames.append(comp_frame)

        if "usingSetSymbol" in frame and frame['usingSetSymbol']:
            for key in frame_defaults['defaultSetSymbol']:
                val = frame_defaults['defaultSetSymbol'][key]
                if key not in card['data']['setSymbol']:
                    card['data']['setSymbol'][key] = val

        if "usingBottomInfo" in frame and frame['usingBottomInfo']:
            if 'bottomInfo' not in card['data']:
                card['data']['bottomInfo'] = {}

            for bottom_region in frame_defaults['defaultBottomInfo']:
                if bottom_region not in card['data']['bottomInfo']:
                    card['data']['bottomInfo'][bottom_region] = {}

                for key in frame_defaults['defaultBottomInfo'][bottom_region]:
                    val = frame_defaults['defaultBottomInfo'][bottom_region][key]

                    if key not in card['data']['bottomInfo'][bottom_region]:
                        card['data']['bottomInfo'][bottom_region][key] = val

        processed_frames.append(frame)

    card['data']['frames'] = processed_frames
    card_elem_list.append({
        'title': 'Frames',
        'children': [read_json_elem(pf, 'data.frames.F', ui_title=f"{pf['frame']}") for pf in processed_frames]
    })

    card_elem_list.append(read_json_elem(card['data']['setSymbol'], 'data.setSymbol'))
    card_elem_list.append(read_json_elem(card['data']['textRegions'], 'data.textRegions', ui_title="Text Regions"))
    card_elem_list.append(read_json_elem(card['data']['bottomInfo'], 'data.bottomInfo', ui_title="Bottom Info"))

    for d_key in ['version', 'infoYear', 'infoRarity', 'infoSet', 'infoLanguage']:
        card_elem_list.append(read_json_elem(card['data'][d_key], f"data.{d_key}"))

    return card_elem_list
