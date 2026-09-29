from repositories.color_graph_repository import (
    ColorGraphRepository,
)
from utils.color_utils import (
    parse_color,
    rgb_to_lab,
)


class ColorRecommendationService:

    DEFAULT_LIMIT = 5
    MAX_LIMIT = 12

    DIRECTION_TOP_TO_BOTTOM = "top_to_bottom"
    DIRECTION_BOTTOM_TO_TOP = "bottom_to_top"

    # 保留舊前端曾使用過的 direction 名稱，避免 API 直接壞掉。
    DIRECTION_MAIN_TO_SUB = "main_to_sub"
    DIRECTION_SUB_TO_MAIN = "sub_to_main"

    DIRECTION_ALIASES = {
        DIRECTION_TOP_TO_BOTTOM:
            DIRECTION_TOP_TO_BOTTOM,

        DIRECTION_BOTTOM_TO_TOP:
            DIRECTION_BOTTOM_TO_TOP,

        DIRECTION_MAIN_TO_SUB:
            DIRECTION_TOP_TO_BOTTOM,

        DIRECTION_SUB_TO_MAIN:
            DIRECTION_BOTTOM_TO_TOP,
    }

    @staticmethod
    def normalize_direction(direction: str) -> str:

        value = (
            direction
            or ColorRecommendationService
            .DIRECTION_TOP_TO_BOTTOM
        )

        value = str(value).strip().lower()

        normalized = (
            ColorRecommendationService
            .DIRECTION_ALIASES
            .get(value)
        )

        if normalized is None:
            raise ValueError(
                "direction 必須是 "
                "top_to_bottom、bottom_to_top、"
                "main_to_sub 或 sub_to_main"
            )

        return normalized

    @staticmethod
    def _normalize_limit(limit: int | None) -> int:

        if limit is None:
            limit = (
                ColorRecommendationService
                .DEFAULT_LIMIT
            )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError("limit 必須是整數")

        return min(
            max(limit, 1),
            ColorRecommendationService.MAX_LIMIT,
        )

    @staticmethod
    def _format_matched_shade(shade):

        if shade is None:
            return None

        return {
            "shade_id": shade.get("shade_id"),
            "hex": shade.get("hex"),
            "rgb": [
                shade.get("rgb_r"),
                shade.get("rgb_g"),
                shade.get("rgb_b"),
            ],
            "lab": [
                round(float(shade.get("lab_l")), 4),
                round(float(shade.get("lab_a")), 4),
                round(float(shade.get("lab_b")), 4),
            ],
            "chroma": shade.get("chroma"),
            "hue_deg": shade.get("hue_deg"),
            "dominant_source_family": (
                shade.get("dominant_source_family")
            ),
            "source_family_purity": (
                shade.get("source_family_purity")
            ),
            "delta_e": round(
                float(shade.get("delta_e") or 0.0),
                4,
            ),
        }

    @staticmethod
    def _format_recommendations(recommendations):
        """
        補上 rgb list，並保留 color=HEX 供舊前端相容。
        """

        output = []

        for item in recommendations:
            row = dict(item)

            row["rgb"] = [
                row.pop("rgb_r", None),
                row.pop("rgb_g", None),
                row.pop("rgb_b", None),
            ]

            # color 與 hex 都保留：
            # 舊前端若讀 item.color 不會壞，
            # 新前端可以直接讀 item.hex。
            if not row.get("color"):
                row["color"] = row.get("hex")

            output.append(row)

        return output

    @staticmethod
    def get_color_matches(
        input_color: str,
        limit: int | None = None,
        direction: str = DIRECTION_TOP_TO_BOTTOM,
        include_same_color: bool = True,
    ):
        """
        輸入顏色支援：

        - #3A5575
        - 3A5575
        - 58,85,117
        - rgb(58,85,117)

        流程：
        input -> RGB -> Lab -> 最近 refined ColorShade
        -> MATCHES_WITH -> 推薦實際 HEX。
        """

        normalized_direction = (
            ColorRecommendationService
            .normalize_direction(direction)
        )

        limit = (
            ColorRecommendationService
            ._normalize_limit(limit)
        )

        # ====================================================
        # 1. HEX / RGB 統一
        # ====================================================

        parsed = parse_color(
            input_color
        )

        input_hex = parsed["hex"]
        input_rgb = parsed["rgb"]
        input_lab = rgb_to_lab(
            input_rgb
        )

        # ====================================================
        # 2. 找 102 個 refined ColorShade 中最近的一個
        # ====================================================

        matched_shade = (
            ColorGraphRepository
            .find_nearest_color_shade(
                lab_l=input_lab[0],
                lab_a=input_lab[1],
                lab_b=input_lab[2],
            )
        )

        if matched_shade is None:
            return {
                "input_color": input_hex,
                "input_rgb": list(input_rgb),
                "input_lab": [
                    round(float(v), 4)
                    for v in input_lab
                ],
                "direction": normalized_direction,
                "limit": limit,
                "include_same_color": include_same_color,
                "matched_shade": None,
                "recommendations": [],
            }

        shade_id = (
            matched_shade["shade_id"]
        )

        # ====================================================
        # 3. 依衣服方向查推薦
        # ====================================================

        if (
            normalized_direction
            ==
            ColorRecommendationService
            .DIRECTION_TOP_TO_BOTTOM
        ):

            recommendations = (
                ColorGraphRepository
                .get_top_to_bottom_matches(
                    shade_id=shade_id,
                    limit=limit,
                    include_same_color=(
                        include_same_color
                    ),
                )
            )

        else:

            recommendations = (
                ColorGraphRepository
                .get_bottom_to_top_matches(
                    shade_id=shade_id,
                    limit=limit,
                    include_same_color=(
                        include_same_color
                    ),
                )
            )

        recommendations = (
            ColorRecommendationService
            ._format_recommendations(
                recommendations
            )
        )

        # ====================================================
        # 4. Response
        # ====================================================

        return {
            # 舊 API 原本就使用 input_color，維持這個 key。
            "input_color": input_hex,

            # Wardrobe DB 的 RGB 可以直接對照這裡。
            "input_rgb": list(input_rgb),

            "input_lab": [
                round(float(v), 4)
                for v in input_lab
            ],

            "direction": normalized_direction,

            "limit": limit,

            "include_same_color": (
                include_same_color
            ),

            "matched_shade": (
                ColorRecommendationService
                ._format_matched_shade(
                    matched_shade
                )
            ),

            "recommendations": (
                recommendations
            ),
        }
