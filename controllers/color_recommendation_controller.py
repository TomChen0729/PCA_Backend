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