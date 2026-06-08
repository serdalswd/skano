import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

# Bayer threshold matrices
BAYER_2 = np.array([[0, 2], [3, 1]], dtype=np.float32) / 4.0
BAYER_4 = np.array([
    [0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]
], dtype=np.float32) / 16.0
BAYER_8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
], dtype=np.float32) / 64.0

# Error diffusion kernels: list of (dy, dx, weight)
KERNELS = {
    "Floyd-Steinberg": [
        (0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16),
    ],
    "Atkinson": [
        (0, 1, 1 / 8), (0, 2, 1 / 8),
        (1, -1, 1 / 8), (1, 0, 1 / 8), (1, 1, 1 / 8),
        (2, 0, 1 / 8),
    ],
    "Jarvis-Judice-Ninke": [
        (0, 1, 7 / 48), (0, 2, 5 / 48),
        (1, -2, 3 / 48), (1, -1, 5 / 48), (1, 0, 7 / 48), (1, 1, 5 / 48), (1, 2, 3 / 48),
        (2, -2, 1 / 48), (2, -1, 3 / 48), (2, 0, 5 / 48), (2, 1, 3 / 48), (2, 2, 1 / 48),
    ],
    "Stucki": [
        (0, 1, 8 / 42), (0, 2, 4 / 42),
        (1, -2, 2 / 42), (1, -1, 4 / 42), (1, 0, 8 / 42), (1, 1, 4 / 42), (1, 2, 2 / 42),
        (2, -2, 1 / 42), (2, -1, 2 / 42), (2, 0, 4 / 42), (2, 1, 2 / 42), (2, 2, 1 / 42),
    ],
    "Burkes": [
        (0, 1, 8 / 32), (0, 2, 4 / 32),
        (1, -2, 2 / 32), (1, -1, 4 / 32), (1, 0, 8 / 32), (1, 1, 4 / 32), (1, 2, 2 / 32),
    ],
    "Sierra": [
        (0, 1, 5 / 32), (0, 2, 3 / 32),
        (1, -2, 2 / 32), (1, -1, 4 / 32), (1, 0, 5 / 32), (1, 1, 4 / 32), (1, 2, 2 / 32),
        (2, -1, 2 / 32), (2, 0, 3 / 32), (2, 1, 2 / 32),
    ],
    "Sierra Two-Row": [
        (0, 1, 4 / 16), (0, 2, 3 / 16),
        (1, -2, 1 / 16), (1, -1, 2 / 16), (1, 0, 3 / 16), (1, 1, 2 / 16), (1, 2, 1 / 16),
    ],
    "Sierra Lite": [
        (0, 1, 2 / 4), (1, -1, 1 / 4), (1, 0, 1 / 4),
    ],
}

ALGORITHM_NAMES = [
    "None (Threshold)",
    "Floyd-Steinberg",
    "Atkinson",
    "Jarvis-Judice-Ninke",
    "Stucki",
    "Burkes",
    "Sierra",
    "Sierra Two-Row",
    "Sierra Lite",
    "Bayer 2x2",
    "Bayer 4x4",
    "Bayer 8x8",
    "Random Noise",
]


def _quantize_to_palette(arr: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Vectorized nearest-color quantization (chunked to control memory)."""
    h, w = arr.shape[:2]
    flat = arr.reshape(-1, 3)
    result = np.empty_like(flat)
    chunk = 4096
    for i in range(0, len(flat), chunk):
        c = flat[i:i + chunk]
        dists = np.sum((c[:, np.newaxis, :] - palette[np.newaxis, :, :]) ** 2, axis=2)
        idx = np.argmin(dists, axis=1)
        result[i:i + chunk] = palette[idx]
    return result.reshape(h, w, 3)


def _error_diffusion(arr: np.ndarray, palette: np.ndarray, kernel: list) -> np.ndarray:
    """Generic error-diffusion dithering with sequential pixel processing."""
    h, w, _ = arr.shape
    buf = arr.astype(np.float32)
    pal_f = palette.astype(np.float32)
    for y in range(h):
        for x in range(w):
            px = buf[y, x]
            dists = np.sum((pal_f - px) ** 2, axis=1)
            nearest = pal_f[np.argmin(dists)]
            error = px - nearest
            buf[y, x] = nearest
            for dy, dx, wt in kernel:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    buf[ny, nx] += error * wt
    return np.clip(buf, 0, 255).astype(np.uint8)


def _bayer_dither(arr: np.ndarray, palette: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    h, w, _ = arr.shape
    n = matrix.shape[0]
    rh = (h + n - 1) // n
    rw = (w + n - 1) // n
    tiled = np.tile(matrix, (rh, rw))[:h, :w]
    spread = 255.0 / max(len(palette), 2)
    offset = (tiled - 0.5) * spread
    adjusted = arr.astype(np.float32) + offset[:, :, np.newaxis]
    adjusted = np.clip(adjusted, 0, 255)
    return _quantize_to_palette(adjusted, palette.astype(np.float32)).astype(np.uint8)


def _random_dither(arr: np.ndarray, palette: np.ndarray) -> np.ndarray:
    spread = 255.0 / max(len(palette), 2)
    noise = (np.random.random(arr.shape).astype(np.float32) - 0.5) * spread
    adjusted = np.clip(arr.astype(np.float32) + noise, 0, 255)
    return _quantize_to_palette(adjusted, palette.astype(np.float32)).astype(np.uint8)


def _apply_adjustments(image: Image.Image, contrast: float, brightness: float,
                       midtones: float, blur: float) -> Image.Image:
    if blur > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=blur))
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    if brightness != 1.0:
        image = ImageEnhance.Brightness(image).enhance(brightness)
    if midtones != 0.0:
        arr = np.array(image).astype(np.float32) / 255.0
        gamma = 1.0 / (1.0 + midtones) if midtones > 0 else 1.0 - midtones
        arr = np.power(arr, gamma)
        image = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
    return image


def process_image(
    image: Image.Image,
    algorithm: str,
    scale: int,
    palette: list,
    contrast: float = 1.0,
    brightness: float = 1.0,
    midtones: float = 0.0,
    blur: float = 0.0,
    invert: bool = False,
) -> Image.Image:
    img = image.convert("RGB")

    img = _apply_adjustments(img, contrast, brightness, midtones, blur)

    if invert:
        arr = np.array(img)
        img = Image.fromarray(255 - arr)

    orig_w, orig_h = img.size
    if scale > 1:
        sw, sh = max(1, orig_w // scale), max(1, orig_h // scale)
        img = img.resize((sw, sh), Image.NEAREST)

    pal_np = np.array(palette, dtype=np.float32)
    arr = np.array(img)

    if algorithm == "None (Threshold)":
        result_arr = _quantize_to_palette(arr.astype(np.float32), pal_np).astype(np.uint8)
    elif algorithm in KERNELS:
        result_arr = _error_diffusion(arr, pal_np, KERNELS[algorithm])
    elif algorithm == "Bayer 2x2":
        result_arr = _bayer_dither(arr, pal_np, BAYER_2)
    elif algorithm == "Bayer 4x4":
        result_arr = _bayer_dither(arr, pal_np, BAYER_4)
    elif algorithm == "Bayer 8x8":
        result_arr = _bayer_dither(arr, pal_np, BAYER_8)
    elif algorithm == "Random Noise":
        result_arr = _random_dither(arr, pal_np)
    else:
        result_arr = _quantize_to_palette(arr.astype(np.float32), pal_np).astype(np.uint8)

    result = Image.fromarray(result_arr)

    if scale > 1:
        result = result.resize((orig_w, orig_h), Image.NEAREST)

    return result


def process_gif(
    image: Image.Image,
    algorithm: str,
    scale: int,
    palette: list,
    contrast: float = 1.0,
    brightness: float = 1.0,
    midtones: float = 0.0,
    blur: float = 0.0,
    invert: bool = False,
    progress_cb=None,
) -> list:
    frames = []
    durations = []
    n_frames = getattr(image, 'n_frames', 1)
    for i in range(n_frames):
        image.seek(i)
        duration = image.info.get('duration', 100)
        frame = image.copy().convert('RGB')
        processed = process_image(frame, algorithm, scale, palette,
                                  contrast, brightness, midtones, blur, invert)
        frames.append(processed)
        durations.append(duration)
        if progress_cb:
            progress_cb(int((i + 1) / n_frames * 100))
    return frames, durations
