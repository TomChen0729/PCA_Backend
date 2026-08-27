from repositories.color_graph_repository import ColorGraphRepository
from utils.color_utils import (
    normalize_hex,
    hex_to_lab,
    delta_e76,
)


class ColorRecommendationService:

    DEFAULT_LIMIT = 10
    DEFAULT_DELTA_E_THRESHOLD = 10.0
    MAX_LIMIT = 6

    DIRECTION_MAIN_TO_SUB = "main_to_sub"
    DIRECTION_SUB_TO_MAIN = "sub_to_main"
    VALID_DIRECTIONS = {
        DIRECTION_MAIN_TO_SUB,
        DIRECTION_SUB_TO_MAIN,
    }

    @staticmethod
    def find_similar_graph_colors(
        input_color: str,
        threshold: float,
        direction: str,
    ):
        input_color = normalize_hex(input_color)
        input_lab = hex_to_lab(input_color)

        # 主色 -> 配色：輸入色要跟圖譜中的主色比較
        # 配色 -> 主色：輸入色要跟圖譜中的配色比較
        if direction == ColorRecommendationService.DIRECTION_MAIN_TO_SUB:
            graph_colors = ColorGraphRepository.get_all_main_colors()
        else:
            graph_colors = ColorGraphRepository.get_all_sub_colors()

        similar_colors = []

        for graph_color in graph_colors:
            try:
                graph_color = normalize_hex(graph_color)
                graph_lab = hex_to_lab(graph_color)

                distance = delta_e76(
                    input_lab,
                    graph_lab,
                )

                if distance <= threshold:
                    similar_colors.append({
                        "color": graph_color,
                        "delta_e": round(distance, 4),
                    })

            except ValueError:
                continue

        similar_colors.sort(
            key=lambda item: item["delta_e"]
        )

        return similar_colors

    @staticmethod
    def get_color_matches(
        input_color: str,
        limit: int | None = None,
        threshold: float | None = None,
        direction: str = DIRECTION_MAIN_TO_SUB,
    ):
        if direction not in ColorRecommendationService.VALID_DIRECTIONS:
            raise ValueError(
                "direction 必須是 main_to_sub 或 sub_to_main"
            )

        # 沒有傳參數才使用 Service 預設值
        if limit is None:
            limit = ColorRecommendationService.DEFAULT_LIMIT

        if threshold is None:
            threshold = (
                ColorRecommendationService
                .DEFAULT_DELTA_E_THRESHOLD
            )

        # limit 限制 1 ~ MAX_LIMIT
        limit = min(
            max(limit, 1),
            ColorRecommendationService.MAX_LIMIT
        )

        if threshold <= 0:
            raise ValueError("threshold 必須大於 0")

        input_color = normalize_hex(input_color)

        # 1. 依 direction 找相近的圖譜來源色
        similar_colors = (
            ColorRecommendationService
            .find_similar_graph_colors(
                input_color=input_color,
                threshold=threshold,
                direction=direction,
            )
        )

        if not similar_colors:
            return {
                "input_color": input_color,
                "direction": direction,
                "limit": limit,
                "threshold": threshold,
                "similar_source_color_count": 0,
                "similar_source_colors": [],
                "recommendations": [],
            }

        source_colors = [
            item["color"]
            for item in similar_colors
        ]

        distance_map = {
            item["color"].upper(): item["delta_e"]
            for item in similar_colors
        }

        # 2. 依 direction 查圖譜
        if direction == ColorRecommendationService.DIRECTION_MAIN_TO_SUB:
            graph_matches = (
                ColorGraphRepository
                .get_matches_by_main_colors(source_colors)
            )
        else:
            graph_matches = (
                ColorGraphRepository
                .get_matches_by_sub_colors(source_colors)
            )

        # 3. 合併重複推薦色
        merged = {}

        for item in graph_matches:
            recommended_color = normalize_hex(item["color"])
            source_color = normalize_hex(item["source_color"])

            if recommended_color not in merged:
                merged[recommended_color] = {
                    "color": recommended_color,
                    "count": 0,
                    "likes": 0,
                    "source_count": 0,
                    "source_colors": [],
                    "min_delta_e": float("inf"),
                }

            target = merged[recommended_color]

            target["count"] += item["count"]
            target["likes"] += item["likes"]
            target["source_count"] += 1

            delta_e = distance_map.get(
                source_color.upper(),
                999,
            )

            target["min_delta_e"] = min(
                target["min_delta_e"],
                delta_e,
            )

            target["source_colors"].append(
                source_color
            )

        recommendations = list(merged.values())

        # 4. 排序
        recommendations.sort(
            key=lambda item: (
                -item["source_count"],
                -item["count"],
                -item["likes"],
                item["min_delta_e"],
            )
        )

        # 5. 限制數量
        recommendations = recommendations[:limit]

        for item in recommendations:
            item["min_delta_e"] = round(
                item["min_delta_e"],
                4,
            )

        return {
            "input_color": input_color,
            "direction": direction,
            "limit": limit,
            "threshold": threshold,
            "similar_source_color_count": len(
                similar_colors
            ),
            "similar_source_colors": similar_colors,
            "recommendations": recommendations,
        }