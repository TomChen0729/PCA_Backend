from flask import (
    Blueprint,
    jsonify,
    request,
)

from services.color_recommendation_service import (
    ColorRecommendationService,
)


color_recommendation_bp = Blueprint(
    "color_recommendation",
    __name__,
    url_prefix="/api/color-recommendations",
)


def parse_bool(
    value,
    default=True,
):

    if value is None:
        return default

    value = str(value).strip().lower()

    if value in {
        "true",
        "1",
        "yes",
    }:
        return True

    if value in {
        "false",
        "0",
        "no",
    }:
        return False

    raise ValueError(
        "include_same_color / include_same_shade "
        "必須是 true 或 false"
    )


@color_recommendation_bp.route(
    "/matches",
    methods=["GET"],
)
def get_color_matches():

    # 支援：
    # color=#3A5575
    # color=3A5575
    # color=58,85,117
    # color=rgb(58,85,117)
    color = request.args.get(
        "color"
    )

    limit = request.args.get(
        "limit",
        type=int,
    )

    direction = request.args.get(
        "direction",
        ColorRecommendationService
        .DIRECTION_TOP_TO_BOTTOM,
    )

    if not color:

        return jsonify({
            "success": False,
            "message": (
                "請提供 color 參數，例如 "
                "#3A5575 或 58,85,117"
            ),
        }), 400

    try:

        # 新名稱 include_same_shade 優先；
        # 沒有時相容舊 include_same_color。
        same_value = request.args.get(
            "include_same_shade"
        )

        if same_value is None:
            same_value = request.args.get(
                "include_same_color"
            )

        include_same_color = (
            parse_bool(
                same_value,
                default=True,
            )
        )

        result = (
            ColorRecommendationService
            .get_color_matches(
                input_color=color,
                limit=limit,
                direction=direction,
                include_same_color=(
                    include_same_color
                ),
            )
        )

        return jsonify({
            "success": True,
            **result,
        }), 200

    except ValueError as exc:

        return jsonify({
            "success": False,
            "message": str(exc),
        }), 400

    except Exception as exc:

        print(
            "color recommendation error:",
            exc,
        )

        return jsonify({
            "success": False,
            "message": (
                "取得配色建議失敗"
            ),
        }), 500
