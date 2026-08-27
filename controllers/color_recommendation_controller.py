from flask import Blueprint, jsonify, request

from services.color_recommendation_service import ColorRecommendationService


color_recommendation_bp = Blueprint(
    "color_recommendation",
    __name__,
    url_prefix="/api/color-recommendations"
)


@color_recommendation_bp.route("/matches", methods=["GET"])
def get_color_matches():
    color = request.args.get("color")

    # 沒傳就給 None
    limit = request.args.get("limit", type=int)
    threshold = request.args.get("threshold", type=float)

    # 同一支 API 透過 direction 切換查詢方向
    # main_to_sub：主色 -> 配色（預設）
    # sub_to_main：配色 -> 主色
    direction = request.args.get(
        "direction",
        ColorRecommendationService.DIRECTION_MAIN_TO_SUB,
    )

    if not color:
        return jsonify({
            "success": False,
            "message": "請提供 color 參數",
        }), 400

    try:
        result = ColorRecommendationService.get_color_matches(
            input_color=color,
            limit=limit,
            threshold=threshold,
            direction=direction,
        )

        print(result)
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
        print("color recommendation error:", exc)

        return jsonify({
            "success": False,
            "message": "取得配色建議失敗",
        }), 500
