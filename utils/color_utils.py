# 色彩格式解析、轉換與色差計算
import math
import re


HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
RGB_FUNCTION_PATTERN = re.compile(
    r"^rgb\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*\)$",
    re.IGNORECASE,
)
RGB_CSV_PATTERN = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)\s*$"
)


def normalize_hex(hex_color: str) -> str:
    """
    將 HEX 統一轉成 #RRGGBB 大寫格式。

    接受：
    - #3A5575
    - 3A5575
    """
    if not hex_color:
        raise ValueError("顏色不可為空")

    color = str(hex_color).strip()

    if not color.startswith("#"):
        color = f"#{color}"

    if not HEX_PATTERN.match(color):
        raise ValueError(f"HEX 顏色格式錯誤：{hex_color}")

    return color.upper()


def normalize_rgb(rgb):
    """
    RGB 統一為 (R, G, B) 整數 tuple，範圍 0~255。
    """
    if rgb is None or len(rgb) != 3:
        raise ValueError("RGB 必須包含 R,G,B 三個值")

    values = []

    for value in rgb:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"RGB 數值錯誤：{rgb}")

        if not math.isfinite(number):
            raise ValueError(f"RGB 數值錯誤：{rgb}")

        # Wardrobe KMeans 寫入的值原本就是整數；
        # 若外部送入 58.0 這類值，也允許轉為整數。
        integer = int(round(number))

        if integer < 0 or integer > 255:
            raise ValueError(
                f"RGB 必須介於 0~255：{rgb}"
            )

        values.append(integer)

    return tuple(values)


def rgb_to_hex(rgb) -> str:
    """
    (58, 85, 117) -> #3A5575
    """
    r, g, b = normalize_rgb(rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


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


def parse_color(color):
    """
    將 API 的 color 輸入統一轉為 HEX + RGB。

    支援：
    - #3A5575
    - 3A5575
    - 58,85,117
    - rgb(58,85,117)
    - (58, 85, 117) / [58, 85, 117]（供後端內部使用）

    回傳：
    {
        "hex": "#3A5575",
        "rgb": (58, 85, 117),
    }
    """
    if color is None:
        raise ValueError("color 不可為空")

    if isinstance(color, (list, tuple)):
        rgb = normalize_rgb(color)
        return {
            "hex": rgb_to_hex(rgb),
            "rgb": rgb,
        }

    value = str(color).strip()

    if not value:
        raise ValueError("color 不可為空")

    # HEX：有 # 或單純 6 碼都接受
    try:
        normalized_hex = normalize_hex(value)
        return {
            "hex": normalized_hex,
            "rgb": hex_to_rgb(normalized_hex),
        }
    except ValueError:
        pass

    # rgb(58,85,117)
    match = RGB_FUNCTION_PATTERN.match(value)

    if match:
        rgb = normalize_rgb(match.groups())
        return {
            "hex": rgb_to_hex(rgb),
            "rgb": rgb,
        }

    # 58,85,117（Wardrobe DB 目前就是這種格式）
    match = RGB_CSV_PATTERN.match(value)

    if match:
        rgb = normalize_rgb(match.groups())
        return {
            "hex": rgb_to_hex(rgb),
            "rgb": rgb,
        }

    raise ValueError(
        "color 格式錯誤，請使用 #RRGGBB、RRGGBB、"
        "R,G,B 或 rgb(R,G,B)"
    )


def _srgb_to_linear(value: float) -> float:
    value /= 255.0

    if value <= 0.04045:
        return value / 12.92

    return ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    """
    sRGB -> XYZ -> CIE Lab（D65）。

    此格式與 IQON refined ColorShade 所保存的 CIE Lab
    數值尺度一致：L 約 0~100，a/b 約 -128~127。
    """
    r, g, b = normalize_rgb(rgb)

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
