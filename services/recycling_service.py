"""Taipei City old-clothes collection point lookup and wardrobe recycling workflow."""
import json
import math
import threading
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app
from extensions import db
from models.wardrobe_item import WardrobeItem


RESOURCE_ID = "67d4ce6f-3137-4e6f-b490-fd127ccdff5b"
API_URL = f"https://data.taipei/api/v1/dataset/{RESOURCE_ID}"
_cache = {"expires": 0, "sites": []}
_cache_lock = threading.Lock()


def _first(record, *keys):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize(record):
    try:
        lat = float(_first(record, "緯度", "latitude", "lat"))
        lng = float(_first(record, "經度", "longitude", "lng", "lon"))
    except (TypeError, ValueError):
        return None
    address = str(_first(record, "臺北市核准地點", "核准地點", "地址", "address") or "").strip()
    district = str(_first(record, "行政區", "district") or "").strip()
    if not address or not district or not (21 <= lat <= 26 and 119 <= lng <= 123):
        return None
    return {
        "id": str(_first(record, "核准編號", "核准編號 ", "_id", "id") or f"{lat:.5f},{lng:.5f}"),
        "district": district,
        "neighborhood": str(_first(record, "里別", "neighborhood") or ""),
        "address": address,
        "organization": str(_first(record, "團體名稱", "設置團體", "organization") or ""),
        "phone": str(_first(record, "電話", "phone") or ""),
        "latitude": lat,
        "longitude": lng,
    }


def _fetch_sites():
    now = time.monotonic()
    with _cache_lock:
        if _cache["sites"] and now < _cache["expires"]:
            return _cache["sites"], False
    records = []
    offset = 0
    while offset < 3000:
        params = urlencode({"scope": "resourceAquire", "resource_id": RESOURCE_ID, "limit": 1000, "offset": offset})
        request = Request(f"{API_URL}?{params}", headers={"Accept": "application/json", "User-Agent": "PCA-Recycling/1.0"})
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8-sig"))
        result = payload.get("result", payload)
        page = result.get("results", result.get("records", [])) if isinstance(result, dict) else []
        if not isinstance(page, list):
            raise ValueError("回收據點 API 回傳格式不正確")
        records.extend(page)
        if len(page) < 1000:
            break
        offset += len(page)
    sites = [site for record in records if (site := _normalize(record))]
    if not sites:
        raise ValueError("目前無法取得有效的舊衣回收據點資料")
    with _cache_lock:
        _cache.update(sites=sites, expires=time.monotonic() + 6 * 60 * 60)
    return sites, False


def collection_sites(latitude=None, longitude=None, district=None, limit=30):
    stale = False
    try:
        sites, _ = _fetch_sites()
    except Exception:
        with _cache_lock:
            sites = list(_cache["sites"])
        if not sites:
            raise
        stale = True
        current_app.logger.warning("臺北市回收據點 API 無法連線，使用暫存資料")
    sites = [dict(site) for site in sites]
    all_districts = sorted({site["district"] for site in sites})
    district = (district or "").strip()
    if district:
        sites = [site for site in sites if site["district"] == district]
    has_location = latitude is not None and longitude is not None
    if has_location:
        latitude, longitude = float(latitude), float(longitude)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("定位座標無效")
        for site in sites:
            lat1, lat2 = math.radians(latitude), math.radians(site["latitude"])
            dlat = lat2 - lat1
            dlon = math.radians(site["longitude"] - longitude)
            a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            site["distance_km"] = round(6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)
        sites.sort(key=lambda site: site["distance_km"])
    else:
        sites.sort(key=lambda site: (site["district"], site["address"]))
    return {"success": True, "data": sites[:max(1, min(int(limit), 100))], "districts": all_districts, "stale": stale, "source": "臺北市社會福利團體(機構)設置舊衣回收設施據點"}


def set_recycling_plan(item_id, user_id, site_id):
    item = WardrobeItem.query.filter_by(id=item_id, uid=user_id).first()
    if not item:
        raise LookupError("找不到這件衣物或無權限操作")
    if item.recycling_status != "active":
        raise ValueError("這件衣物已安排或完成回收")
    sites, _ = _fetch_sites()
    site = next((s for s in sites if s["id"] == str(site_id)), None)
    if not site:
        raise ValueError("找不到此回收據點，請重新查詢")
    item.recycling_status = "planned"
    item.recycle_site_id = site["id"]
    item.recycle_district = site["district"]
    item.recycle_address = site["address"]
    item.recycle_organization = site["organization"]
    item.recycle_phone = site["phone"]
    item.recycle_latitude = site["latitude"]
    item.recycle_longitude = site["longitude"]
    item.recycling_planned_at = datetime.utcnow()
    item.recycled_at = None
    db.session.commit()
    return item


def update_recycling_status(item_id, user_id, action):
    item = WardrobeItem.query.filter_by(id=item_id, uid=user_id).first()
    if not item:
        raise LookupError("找不到這件衣物或無權限操作")
    if action == "cancel":
        if item.recycling_status != "planned":
            raise ValueError("只有待回收的衣物可以取消安排")
        item.recycling_status = "active"
        item.recycle_site_id = item.recycle_district = item.recycle_address = None
        item.recycle_organization = item.recycle_phone = None
        item.recycle_latitude = item.recycle_longitude = None
        item.recycling_planned_at = item.recycled_at = None
    elif action == "complete":
        if item.recycling_status != "planned":
            raise ValueError("只有待回收的衣物可以標記為已回收")
        item.recycling_status = "recycled"
        item.recycled_at = datetime.utcnow()
    else:
        raise ValueError("不支援的回收操作")
    db.session.commit()
    return item


def serialize_item(item):
    return {
        "item_id": item.id, "tag": item.tag, "date": item.timestamp.strftime("%Y-%m-%d"),
        "image_url": f"/{item.previewPath or item.imgPath}", "tryon_image_url": f"/{item.imgPath}",
        "colors": [item.color_1, item.color_2, item.color_3], "recycling_status": item.recycling_status,
        "recycle_site": ({"id": item.recycle_site_id, "district": item.recycle_district, "address": item.recycle_address,
            "organization": item.recycle_organization, "phone": item.recycle_phone, "latitude": item.recycle_latitude,
            "longitude": item.recycle_longitude} if item.recycle_site_id else None),
        "recycling_planned_at": item.recycling_planned_at.isoformat() if item.recycling_planned_at else None,
        "recycled_at": item.recycled_at.isoformat() if item.recycled_at else None,
    }
