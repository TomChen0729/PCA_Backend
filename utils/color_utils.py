# 若色彩庫內沒有尋找的顏色，則做最近顏色匹配
import math
import re


HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_hex(hex_color: str) -> str:
    """
    將 HEX 統一轉成 #RRGGBB 大寫格式。
    """
    if not hex_color:
        raise ValueError("顏色不可為空")

    color = hex_color.strip()

    if not color.startswith("#"):
        color = f"#{color}"

    if not HEX_PATTERN.match(color):
        raise ValueError(f"HEX 顏色格式錯誤：{hex_color}")

    return color.upper()


def hex_to_rgb(hex_color: str):
    """
    #C97C91 -> (201, 124, 145)
    """
    hex_color = normalize_hex(hex_color)

    return (
        int(hex_color[1:3], 16),
        int(hex_color[3:5], 16),
        int(hex_color[5:7], 16),
    )


def _srgb_to_linear(value: float) -> float:
    value /= 255.0

    if value <= 0.04045:
        return value / 12.92

    return ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    """
    sRGB -> XYZ -> CIE Lab
    D65 illuminant
    """
    r, g, b = rgb

    r = _srgb_to_linear(r)
    g = _srgb_to_linear(g)
    b = _srgb_to_linear(b)

    # sRGB -> XYZ (D65)
    x = (
        r * 0.4124564
        + g * 0.3575761
        + b * 0.1804375
    ) * 100

    y = (
        r * 0.2126729
        + g * 0.7151522
        + b * 0.0721750
    ) * 100

    z = (
        r * 0.0193339
        + g * 0.1191920
        + b * 0.9503041
    ) * 100

    # D65 reference white
    x /= 95.047
    y /= 100.000
    z /= 108.883

    def f(t):
        if t > 0.008856:
            return t ** (1 / 3)

        return (7.787 * t) + (16 / 116)

    fx = f(x)
    fy = f(y)
    fz = f(z)

    l = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return l, a, b


def hex_to_lab(hex_color: str):
    return rgb_to_lab(hex_to_rgb(hex_color))


def delta_e76(lab1, lab2) -> float:
    """
    CIE76 色差。
    數值越小代表兩個顏色越接近。
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    return math.sqrt(
        (l1 - l2) ** 2
        + (a1 - a2) ** 2
        + (b1 - b2) ** 2
    )