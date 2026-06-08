import numpy as np
from PIL import Image

BUILTIN_PALETTES = {
    "Black & White": [(0, 0, 0), (255, 255, 255)],
    "4 Grays": [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)],
    "8 Grays": [(i * 36, i * 36, i * 36) for i in range(8)],
    "Game Boy": [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)],
    "CGA": [
        (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
        (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
        (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
        (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
    ],
    "PICO-8": [
        (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
        (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
        (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
        (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
    ],
    "Sweetie 16": [
        (26, 28, 44), (93, 39, 93), (177, 62, 83), (239, 125, 87),
        (255, 205, 117), (167, 240, 112), (56, 183, 100), (37, 113, 121),
        (41, 54, 111), (59, 93, 201), (65, 166, 246), (115, 239, 247),
        (244, 244, 244), (148, 176, 194), (86, 108, 134), (51, 60, 87),
    ],
    "Amstrad CPC": [
        (0, 0, 0), (0, 0, 128), (0, 0, 255),
        (128, 0, 0), (128, 0, 128), (128, 0, 255),
        (255, 0, 0), (255, 0, 128), (255, 0, 255),
        (0, 128, 0), (0, 128, 128), (0, 128, 255),
        (128, 128, 0), (128, 128, 128), (128, 128, 255),
        (255, 128, 0), (255, 128, 128), (255, 128, 255),
        (0, 255, 0), (0, 255, 128), (0, 255, 255),
        (128, 255, 0), (128, 255, 128), (128, 255, 255),
        (255, 255, 0), (255, 255, 128), (255, 255, 255),
    ],
    "8 Colors": [
        (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255),
    ],
    "NES": [
        (84, 84, 84), (0, 30, 116), (8, 16, 144), (48, 0, 136),
        (68, 0, 100), (92, 0, 48), (84, 4, 0), (60, 24, 0),
        (32, 42, 0), (8, 58, 0), (0, 64, 0), (0, 60, 0),
        (0, 50, 60), (0, 0, 0), (0, 0, 0), (0, 0, 0),
        (152, 150, 152), (8, 76, 196), (48, 50, 236), (92, 30, 228),
        (136, 20, 176), (160, 20, 100), (152, 34, 32), (120, 60, 0),
        (84, 90, 0), (40, 114, 0), (8, 124, 0), (0, 118, 40),
        (0, 102, 120), (0, 0, 0), (0, 0, 0), (0, 0, 0),
        (236, 238, 236), (76, 154, 236), (120, 124, 236), (176, 98, 236),
        (228, 84, 236), (236, 88, 180), (236, 106, 100), (212, 136, 32),
        (160, 170, 0), (116, 196, 0), (76, 208, 32), (56, 204, 108),
        (56, 180, 204), (60, 60, 60), (0, 0, 0), (0, 0, 0),
        (236, 238, 236), (168, 204, 236), (188, 188, 236), (212, 178, 236),
        (236, 174, 236), (236, 174, 212), (236, 180, 176), (228, 196, 144),
        (204, 210, 120), (180, 222, 120), (168, 226, 144), (152, 226, 180),
        (160, 214, 228), (160, 162, 160), (0, 0, 0), (0, 0, 0),
    ],
}


def palette_to_numpy(palette: list) -> np.ndarray:
    return np.array(palette, dtype=np.float32)


def extract_palette_from_image(image: Image.Image, n_colors: int = 16) -> list:
    small = image.copy()
    small.thumbnail((200, 200))
    quantized = small.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    raw = quantized.getpalette()
    colors = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, n_colors * 3, 3)]
    seen = set()
    unique = []
    for c in colors:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def load_palette_from_file(path: str) -> list:
    colors = []
    if path.endswith('.hex') or path.endswith('.txt'):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip().lstrip('#')
                if len(line) == 6:
                    r = int(line[0:2], 16)
                    g = int(line[2:4], 16)
                    b = int(line[4:6], 16)
                    colors.append((r, g, b))
    elif path.endswith('.gpl'):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or line.startswith('GIMP') or line.startswith('Name') or not line:
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
                    except ValueError:
                        pass
    elif path.endswith('.png') or path.endswith('.jpg') or path.endswith('.jpeg'):
        img = Image.open(path).convert('RGB')
        colors = extract_palette_from_image(img, 16)
    return colors if colors else BUILTIN_PALETTES["Black & White"]
