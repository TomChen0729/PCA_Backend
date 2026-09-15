from repositories.color_graph_repository import (
    ColorGraphRepository,
)


class ColorRecommendationService:

    DEFAULT_LIMIT = 5
    MAX_LIMIT = 12

    DIRECTION_TOP_TO_BOTTOM = (
        "top_to_bottom"
    )

    DIRECTION_BOTTOM_TO_TOP = (
        "bottom_to_top"
    )

    VALID_DIRECTIONS = {
        DIRECTION_TOP_TO_BOTTOM,
        DIRECTION_BOTTOM_TO_TOP,
    }

    VALID_COLOR_KEYS = {
        "beige",
        "black",
        "blue",
        "white",
        "gray",
        "brown",
        "pink",
        "red",
        "green",
        "yellow",
        "purple",
        "orange",
    }

    COLOR_NAME_ZH = {
        "beige": "米色",
        "black": "黑色",
        "blue": "藍色",
        "white": "白色",
        "gray": "灰色",
        "brown": "棕色",
        "pink": "粉紅色",
        "red": "紅色",
        "green": "綠色",
        "yellow": "黃色",
        "purple": "紫色",
        "orange": "橘色",
    }

    @staticmethod
    def normalize_color_key(
        color: str,
    ) -> str:

        if not color:
            raise ValueError(
                "color 不可為空"
            )

        color_key = (
            color.strip()
            .lower()
        )

        if (
            color_key
            not in
            ColorRecommendationService
            .VALID_COLOR_KEYS
        ):
            raise ValueError(
                "目前 color 必須是："
                + ", ".join(
                    sorted(
                        ColorRecommendationService
                        .VALID_COLOR_KEYS
                    )
                )
            )

        return color_key

    @staticmethod
    def get_color_matches(
        input_color: str,
        limit: int | None = None,
        direction: str = DIRECTION_TOP_TO_BOTTOM,
        include_same_color: bool = True,
    ):

        # ----------------------------
        # direction 驗證
        # ----------------------------

        if (
            direction
            not in
            ColorRecommendationService
            .VALID_DIRECTIONS
        ):
            raise ValueError(
                "direction 必須是 "
                "top_to_bottom "
                "或 bottom_to_top"
            )

        # ----------------------------
        # limit
        # ----------------------------

        if limit is None:
            limit = (
                ColorRecommendationService
                .DEFAULT_LIMIT
            )

        limit = min(
            max(limit, 1),
            ColorRecommendationService
            .MAX_LIMIT,
        )

        # ----------------------------
        # color
        # ----------------------------

        color_key = (
            ColorRecommendationService
            .normalize_color_key(
                input_color
            )
        )

        # ----------------------------
        # 查 Neo4j
        # ----------------------------

        if (
            direction
            ==
            ColorRecommendationService
            .DIRECTION_TOP_TO_BOTTOM
        ):

            recommendations = (
                ColorGraphRepository
                .get_top_to_bottom_matches(
                    color_key=color_key,
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
                    color_key=color_key,
                    limit=limit,
                    include_same_color=(
                        include_same_color
                    ),
                )
            )

        # ----------------------------
        # 回傳
        # ----------------------------

        return {
            "input_color": color_key,

            "input_color_name": (
                ColorRecommendationService
                .COLOR_NAME_ZH
                .get(color_key)
            ),

            "direction": direction,

            "limit": limit,

            "include_same_color":
                include_same_color,

            "recommendations":
                recommendations,
        }