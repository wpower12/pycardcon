
"""
Resolves the body of text into an ordered collection of token objects. These will contain either a
word, and information about length/width, or an image (assumed to be of one of the square/symettric
symbols).

Ideally this collection will be passed to the line-break algorithm, but it could also be used
in a similar manner to the cardconjurer script.

TODO - Have this handle references to various symbols in a different way. I'd like to isolate the image files more.
"""
def parse(text, resource_root):
    text_tokens_raw = text.split(" ")
    token_objects = []
    for raw_token in text_tokens_raw:
        cur_str = ""
        for c_idx, c in enumerate(raw_token):
            if c == "\n":
                if cur_str != "":
                    token_objects.append({
                        "token_type": "str",
                        "content": cur_str,
                        "whitespace": ""
                    })
                token_objects.append({"token_type": "newline"})
                cur_str = ""
            elif c == "{":
                if cur_str != "":
                    token_objects.append({
                        "token_type": "str",
                        "content": cur_str,
                        "whitespace": ""
                    })
                    cur_str = ""
            elif c == "}":
                cmd_obj = parse_cmd_word(cur_str, resource_root)
                if c_idx < len(raw_token)-1:
                    cmd_obj["whitespace"] = ""
                else:
                    cmd_obj["whitespace"] = " "
                token_objects.append(cmd_obj)
                cur_str = ""
            else:
                cur_str += c

        if cur_str != "":
            token_objects.append({
                        "token_type": "str",
                        "content": cur_str,
                        "whitespace": " "
                    })
    return token_objects

def parse_cmd_word(word, resource_root):
    match word:
        case "W":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "W",
                "path_to_img": f"{resource_root}/manaSymbols/w.svg"
            }
        case "B":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "B",
                "path_to_img": f"{resource_root}/manaSymbols/b.svg"
             }
        case "U":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "U",
                "path_to_img": f"{resource_root}/manaSymbols/u.svg"
             }
        case "R":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "R",
                "path_to_img": f"{resource_root}/manaSymbols/r.svg"
             }
        case "G":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "G",
                "path_to_img": f"{resource_root}/manaSymbols/g.svg"
             }
        case "C":
            return {
                "token_type": "symbol",
                "sub_type": "mana",
                "color": "C",
                "path_to_img": f"{resource_root}/manaSymbols/c.svg"
             }
        case "t" | "T":
            return {
                "token_type": "symbol",
                "sub_type": "tap",
                "path_to_img": f"{resource_root}/manaSymbols/t.svg"
            }
        case "0":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 0,
                "path_to_img": f"{resource_root}/manaSymbols/0.svg"
            }
        case "1":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 1,
                "path_to_img": f"{resource_root}/manaSymbols/1.svg"
            }
        case "2":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 2,
                "path_to_img": f"{resource_root}/manaSymbols/2.svg"
            }
        case "3":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 3,
                "path_to_img": f"{resource_root}/manaSymbols/3.svg"
            }
        case "4":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 4,
                "path_to_img": f"{resource_root}/manaSymbols/4.svg"
            }
        case "5":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 5,
                "path_to_img": f"{resource_root}/manaSymbols/5.svg"
            }
        case "6":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 6,
                "path_to_img": f"{resource_root}/manaSymbols/6.svg"
            }
        case "X":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 0,
                "path_to_img": f"{resource_root}/manaSymbols/x.svg"
            }
        case "S" | "s" | "snow":
            return {
                "token_type": "symbol",
                "sub_type": "numeral",
                "value": 1,
                "path_to_img": f"{resource_root}/manaSymbols/s.svg"
            }
        case "cardname":
            return {
                "token_type": "card_meta",
                "card_field": "display-title"
            }

        case "i":
            return {
                "token_type": "font_change",
                "type": "italics",
                "val": 1
            }

        case "/i":
            return {
                "token_type": "font_change",
                "type": "italics",
                "val": 0
            }
