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

    @staticmethod
    def find_similar_graph_colors(
        input_color: str,
        threshold: float,
    ):
        input_color = normalize_hex(input_color)
        input_lab = hex_to_lab(input_color)

        graph_colors = ColorGraphRepository.get_all_main_colors()

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
    ):
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

        # 1. 找所有相近 Neo4j 主色
        similar_colors = (
            ColorRecommendationService
            .find_similar_graph_colors(
                input_color=input_color,
                threshold=threshold,
            )
        )

        if not similar_colors:
            return {
                "input_color": input_color,
                "threshold": threshold,
                "similar_main_color_count": 0,
                "similar_main_colors": [],
                "recommendations": [],
            }

        main_colors = [
            item["color"]
            for item in similar_colors
        ]

        distance_map = {
            item["color"].upper(): item["delta_e"]
            for item in similar_colors
        }

        # 2. 查圖譜配色
        graph_matches = (
            ColorGraphRepository
            .get_matches_by_main_colors(main_colors)
        )

        # 3. 合併重複配色
        merged = {}

        for item in graph_matches:
            sub_color = normalize_hex(item["color"])
            main_color = normalize_hex(item["main_color"])

            if sub_color not in merged:
                merged[sub_color] = {
                    "color": sub_color,
                    "count": 0,
                    "likes": 0,
                    "source_count": 0,
                    "source_main_colors": [],
                    "min_delta_e": float("inf"),
                }

            target = merged[sub_color]

            target["count"] += item["count"]
            target["likes"] += item["likes"]
            target["source_count"] += 1

            delta_e = distance_map.get(
                main_color.upper(),
                999,
            )

            target["min_delta_e"] = min(
                target["min_delta_e"],
                delta_e,
            )

            target["source_main_colors"].append(
                main_color
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
            "limit": limit,
            "threshold": threshold,
            "similar_main_color_count": len(
                similar_colors
            ),
            "similar_main_colors": similar_colors,
            "recommendations": recommendations,
        }