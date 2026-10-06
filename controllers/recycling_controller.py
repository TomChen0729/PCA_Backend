from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models.wardrobe_item import WardrobeItem
from services.recycling_service import collection_sites, serialize_item, set_recycling_plan, update_recycling_status

recycling_bp = Blueprint("recycling_controller", __name__, url_prefix="/api/recycling")


def _error(exc):
    if isinstance(exc, LookupError):
        return jsonify(success=False, message=str(exc)), 404
    if isinstance(exc, ValueError):
        return jsonify(success=False, message=str(exc)), 400
    current_app.logger.exception("舊衣回收功能發生錯誤")
    return jsonify(success=False, message="回收服務暫時無法使用，請稍後重試"), 503


@recycling_bp.get("/sites")
@jwt_required()
def get_sites():
    try:
        result = collection_sites(request.args.get("latitude"), request.args.get("longitude"), request.args.get("district"), request.args.get("limit", 30))
        return jsonify(result)
    except (TypeError, ValueError) as exc:
        return jsonify(success=False, message=str(exc)), 400
    except Exception as exc:
        return _error(exc)


@recycling_bp.get("/items")
@jwt_required()
def get_recycling_items():
    user_id = get_jwt_identity()
    items = (WardrobeItem.query.filter(WardrobeItem.uid == user_id, WardrobeItem.recycling_status != "active")
             .order_by(WardrobeItem.recycling_planned_at.desc(), WardrobeItem.id.desc()).all())
    return jsonify(success=True, data=[serialize_item(item) for item in items])


@recycling_bp.post("/plan")
@jwt_required()
def plan_recycling():
    data = request.get_json(silent=True) or {}
    if not data.get("item_id") or not data.get("site_id"):
        return jsonify(success=False, message="請選擇衣物和回收據點"), 400
    try:
        item = set_recycling_plan(data["item_id"], get_jwt_identity(), data["site_id"])
        return jsonify(success=True, data=serialize_item(item), message="已加入待回收清單")
    except Exception as exc:
        return _error(exc)


def _update(action):
    data = request.get_json(silent=True) or {}
    if not data.get("item_id"):
        return jsonify(success=False, message="缺少衣物編號"), 400
    try:
        item = update_recycling_status(data["item_id"], get_jwt_identity(), action)
        message = "已取消回收安排，衣物已回到衣櫥" if action == "cancel" else "已標記為完成回收"
        return jsonify(success=True, data=serialize_item(item), message=message)
    except Exception as exc:
        return _error(exc)


@recycling_bp.post("/cancel")
@jwt_required()
def cancel_recycling():
    return _update("cancel")


@recycling_bp.post("/complete")
@jwt_required()
def complete_recycling():
    return _update("complete")
