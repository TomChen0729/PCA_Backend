# 訓練時的 ROI 與色彩特徵萃取原始程式

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd


FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]
LEFT_EYE = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
RIGHT_EYE = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]
LIPS = [
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308,
    324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39,
    37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82,
    81, 42, 183, 78,
]
LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

ROI_ORDER = [
    "skin",
    "skin_core",
    "forehead",
    "left_cheek",
    "right_cheek",
    "lip",
    "left_iris",
    "right_iris",
    "iris",
    "hair",
]

ROI_COLORS = {
    "skin": (40, 220, 40),
    "skin_core": (80, 255, 120),
    "forehead": (30, 180, 255),
    "left_cheek": (255, 180, 40),
    "right_cheek": (255, 110, 40),
    "lip": (210, 70, 230),
    "left_iris": (255, 70, 170),
    "right_iris": (180, 70, 255),
    "iris": (230, 80, 190),
    "hair": (50, 60, 255),
}


def resolve_path(text, base_dir):
    p = Path(str(text))
    if p.exists():
        return p
    q = Path(base_dir) / p
    if q.exists():
        return q
    return p


def image_path_from_row(row):
    for col in ["image_path", "processed_image", "path", "filename", "Image_Name"]:
        if col in row and pd.notna(row[col]):
            return str(row[col])
    raise ValueError("manifest 需要 image_path / processed_image / path 欄位")


def read_bgr(path, input_color_mode="bgr"):
    import cv2

    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)

    alpha = None
    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3] > 10
    else:
        bgr = img[:, :, :3]

    if input_color_mode == "swap_rb":
        bgr = bgr[:, :, ::-1].copy()

    return bgr, alpha


def landmark_points(landmarks, w, h, ids):
    pts = []
    for idx in ids:
        if idx >= len(landmarks):
            continue
        lm = landmarks[idx]
        pts.append([int(round(lm.x * w)), int(round(lm.y * h))])
    return np.asarray(pts, dtype=np.int32)


def fill_poly(mask, pts, value=255):
    import cv2

    if len(pts) >= 3:
        cv2.fillPoly(mask, [pts], value)


def bbox_from_points(pts, w, h, pad=0.0):
    x1, y1 = pts.min(axis=0)
    x2, y2 = pts.max(axis=0)

    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)

    x1 = max(0, int(x1 - bw * pad))
    y1 = max(0, int(y1 - bh * pad))
    x2 = min(w - 1, int(x2 + bw * pad))
    y2 = min(h - 1, int(y2 + bh * pad))

    return x1, y1, x2, y2


def box_mask(shape, bbox, frac):
    x1, y1, x2, y2 = bbox
    h, w = shape

    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)

    fx1, fy1, fx2, fy2 = frac
    ix1 = max(0, min(w - 1, int(x1 + bw * fx1)))
    iy1 = max(0, min(h - 1, int(y1 + bh * fy1)))
    ix2 = max(ix1 + 1, min(w, int(x1 + bw * fx2)))
    iy2 = max(iy1 + 1, min(h, int(y1 + bh * fy2)))

    mask = np.zeros(shape, dtype=np.uint8)
    mask[iy1:iy2, ix1:ix2] = 255
    return mask


def foreground_mask(bgr, alpha):
    import cv2

    if alpha is not None:
        return alpha.astype(np.uint8) * 255

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    non_black = np.max(rgb, axis=2) > 12

    diff = rgb.astype(np.int16) - 127
    not_gray = np.sqrt(np.sum(diff * diff, axis=2)) > 18

    fg = (non_black & not_gray).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return fg


def build_roi_masks(bgr, alpha, landmarks):
    import cv2

    h, w = bgr.shape[:2]

    face_pts = landmark_points(landmarks, w, h, FACE_OVAL)
    face = np.zeros((h, w), dtype=np.uint8)
    fill_poly(face, face_pts, 255)

    remove = np.zeros((h, w), dtype=np.uint8)
    fill_poly(remove, landmark_points(landmarks, w, h, LEFT_EYE), 255)
    fill_poly(remove, landmark_points(landmarks, w, h, RIGHT_EYE), 255)
    fill_poly(remove, landmark_points(landmarks, w, h, LIPS), 255)
    remove = cv2.dilate(remove, np.ones((9, 9), np.uint8), iterations=1)

    skin = cv2.bitwise_and(face, cv2.bitwise_not(remove))

    bbox = bbox_from_points(face_pts, w, h, pad=0.03)

    forehead = cv2.bitwise_and(
        box_mask((h, w), bbox, (0.32, 0.13, 0.68, 0.34)),
        skin,
    )
    left_cheek = cv2.bitwise_and(
        box_mask((h, w), bbox, (0.18, 0.43, 0.45, 0.70)),
        skin,
    )
    right_cheek = cv2.bitwise_and(
        box_mask((h, w), bbox, (0.55, 0.43, 0.82, 0.70)),
        skin,
    )
    skin_core = cv2.bitwise_or(forehead, cv2.bitwise_or(left_cheek, right_cheek))

    lip = np.zeros((h, w), dtype=np.uint8)
    fill_poly(lip, landmark_points(landmarks, w, h, LIPS), 255)
    lip = cv2.dilate(lip, np.ones((5, 5), np.uint8), iterations=1)

    left_iris = np.zeros((h, w), dtype=np.uint8)
    right_iris = np.zeros((h, w), dtype=np.uint8)
    fill_poly(left_iris, landmark_points(landmarks, w, h, LEFT_IRIS), 255)
    fill_poly(right_iris, landmark_points(landmarks, w, h, RIGHT_IRIS), 255)
    left_iris = cv2.dilate(left_iris, np.ones((5, 5), np.uint8), iterations=1)
    right_iris = cv2.dilate(right_iris, np.ones((5, 5), np.uint8), iterations=1)
    iris = cv2.bitwise_or(left_iris, right_iris)

    x1, y1, x2, y2 = bbox
    fw = max(1, x2 - x1)
    fh = max(1, y2 - y1)

    hair_region = np.zeros((h, w), dtype=np.uint8)
    hx1 = max(0, int(x1 - fw * 0.18))
    hx2 = min(w, int(x2 + fw * 0.18))
    hy1 = max(0, int(y1 - fh * 0.35))
    hy2 = max(1, int(y1 + fh * 0.20))
    hair_region[hy1:hy2, hx1:hx2] = 255

    not_face = cv2.bitwise_not(cv2.dilate(face, np.ones((13, 13), np.uint8), iterations=1))
    hair = cv2.bitwise_and(hair_region, not_face)

    fg = foreground_mask(bgr, alpha)
    if np.sum(fg > 0) > 200:
        hair = cv2.bitwise_and(hair, fg)

    masks = {
        "skin": skin,
        "skin_core": skin_core,
        "forehead": forehead,
        "left_cheek": left_cheek,
        "right_cheek": right_cheek,
        "lip": lip,
        "left_iris": left_iris,
        "right_iris": right_iris,
        "iris": iris,
        "hair": hair,
    }

    return masks, bbox


def clean_mask(mask, roi, erode_iter):
    import cv2

    m = (mask > 0).astype(np.uint8) * 255

    if roi in {"left_iris", "right_iris", "iris"}:
        return m

    m = cv2.morphologyEx(
        m,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    m = cv2.morphologyEx(
        m,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
    )

    if erode_iter > 0 and roi not in {"lip", "hair"}:
        m = cv2.erode(
            m,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
            iterations=erode_iter,
        )

    return m


def bgr_to_spaces(bgr):
    import cv2

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb01 = rgb.astype(np.float32) / 255.0
    lab = cv2.cvtColor(rgb01, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsv = cv2.cvtColor(rgb01, cv2.COLOR_RGB2HSV).astype(np.float32)
    return rgb.astype(np.float32), lab, hsv


def l_filter(lab_pix, roi, args):
    L = lab_pix[:, 0]

    if roi == "hair":
        low_pct, high_pct = args.hair_l_low_pct, args.hair_l_high_pct
        abs_low, abs_high = 0.5, 99.0
    elif roi == "lip":
        low_pct, high_pct = args.lip_l_low_pct, args.lip_l_high_pct
        abs_low, abs_high = 4.0, 98.0
    elif roi in {"left_iris", "right_iris", "iris"}:
        low_pct, high_pct = args.iris_l_low_pct, args.iris_l_high_pct
        abs_low, abs_high = 1.0, 98.0
    else:
        low_pct, high_pct = args.skin_l_low_pct, args.skin_l_high_pct
        abs_low, abs_high = 8.0, 98.0

    low = max(abs_low, float(np.percentile(L, low_pct)))
    high = min(abs_high, float(np.percentile(L, high_pct)))

    if low >= high:
        return np.ones(len(L), dtype=bool), low, high

    return (L >= low) & (L <= high), low, high


def choose_cluster(centers, counts, roi):
    ratios = counts / max(float(counts.sum()), 1.0)

    L = centers[:, 0]
    a = centers[:, 1]
    b = centers[:, 2]
    C = np.sqrt(a * a + b * b)

    if roi == "hair":
        scores = ratios - 0.004 * L + 0.0015 * C
        scores = np.where(L > 2, scores, scores - 1.0)
        return int(np.argmax(scores))

    if roi == "lip":
        scores = 0.45 * ratios + 0.018 * a + 0.008 * C - 0.006 * np.maximum(L - 72, 0)
        return int(np.argmax(scores))

    if roi in {"left_iris", "right_iris", "iris"}:
        scores = 0.50 * ratios - 0.006 * L + 0.003 * C
        return int(np.argmax(scores))

    return int(np.argmax(ratios))


def choose_legacy_cluster(centers, counts, roi):
    """
    使用你一開始那份資料的方法：
    - lip：選最高彩度群集
    - iris：選最低 L 群集
    - 其他 ROI：選最大群集
    """
    L = centers[:, 0]
    a = centers[:, 1]
    b = centers[:, 2]
    C = np.sqrt(a * a + b * b)

    if roi == "lip":
        return int(np.argmax(C))

    if roi in {"left_iris", "right_iris", "iris"}:
        return int(np.argmin(L))

    return int(np.argmax(counts))


def legacy_representative_color(lab_pix, roi, args):
    """
    舊方法代表色：
    KMeans -> 依 ROI 類型選群集 -> 取該群集 Lab median。
    """
    from sklearn.cluster import KMeans, MiniBatchKMeans

    if lab_pix is None or len(lab_pix) == 0:
        return None, np.nan, np.nan

    n = len(lab_pix)
    unique_count = len(np.unique(np.round(lab_pix, 2), axis=0))

    if roi in {"hair", "lip", "left_iris", "right_iris", "iris"}:
        k = 2
    else:
        k = args.k_clusters

    k = min(k, unique_count, n)

    if k < 2:
        return np.median(lab_pix, axis=0).astype(np.float32), 1.0, np.nan

    if args.max_kmeans_pixels > 0 and n > args.max_kmeans_pixels:
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(n, size=args.max_kmeans_pixels, replace=False)
        fit_pix = lab_pix[idx]
    else:
        fit_pix = lab_pix

    if args.kmeans_method == "full":
        km = KMeans(n_clusters=k, random_state=args.seed, n_init=10)
    else:
        km = MiniBatchKMeans(
            n_clusters=k,
            random_state=args.seed,
            n_init=10,
            batch_size=2048,
            max_iter=150,
        )

    km.fit(fit_pix)
    labels = km.predict(lab_pix)
    counts = np.bincount(labels, minlength=k)

    selected = choose_legacy_cluster(km.cluster_centers_, counts, roi)
    cluster_pixels = lab_pix[labels == selected]

    rep = np.median(cluster_pixels, axis=0).astype(np.float32)
    cluster_ratio = float(counts[selected] / n)
    cluster_L = float(km.cluster_centers_[selected][0])

    return rep, cluster_ratio, cluster_L


def kmeans_main_cluster(lab_pix, roi, args):
    from sklearn.cluster import KMeans, MiniBatchKMeans

    n = len(lab_pix)
    if n < max(args.min_pixels, args.k_clusters * 10):
        return np.ones(n, dtype=bool), np.nan, np.nan

    unique_count = len(np.unique(np.round(lab_pix, 2), axis=0))
    k = min(args.hair_k_clusters if roi == "hair" else args.k_clusters, unique_count)

    if k < 2:
        return np.ones(n, dtype=bool), 1.0, np.nan

    if args.max_kmeans_pixels > 0 and n > args.max_kmeans_pixels:
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(n, size=args.max_kmeans_pixels, replace=False)
        fit_pix = lab_pix[idx]
    else:
        fit_pix = lab_pix

    if args.kmeans_method == "full":
        km = KMeans(n_clusters=k, random_state=args.seed, n_init=10)
    else:
        km = MiniBatchKMeans(
            n_clusters=k,
            random_state=args.seed,
            n_init=10,
            batch_size=2048,
            max_iter=150,
        )

    km.fit(fit_pix)
    labels = km.predict(lab_pix)
    counts = np.bincount(labels, minlength=k)

    main = choose_cluster(km.cluster_centers_, counts, roi)
    keep = labels == main

    return keep, float(counts[main] / n), float(km.cluster_centers_[main][0])


def mad_filter(lab_pix, z):
    if len(lab_pix) < 30:
        return np.ones(len(lab_pix), dtype=bool), np.nan

    center = np.median(lab_pix, axis=0)
    dist = np.linalg.norm(lab_pix - center, axis=1)

    med = np.median(dist)
    mad = np.median(np.abs(dist - med))
    sigma = 1.4826 * mad

    if sigma < 1e-6:
        return np.ones(len(lab_pix), dtype=bool), float(med)

    threshold = med + z * sigma
    return dist <= threshold, float(threshold)


def channel_stats(arr, names, prefix):
    out = {}

    for i, name in enumerate(names):
        if arr is None or len(arr) == 0:
            for stat in ["mean", "std", "median", "p10", "p90", "iqr"]:
                out[f"{prefix}_{name}_{stat}"] = np.nan
            continue

        v = arr[:, i].astype(np.float32)
        p25 = np.percentile(v, 25)
        p75 = np.percentile(v, 75)

        out[f"{prefix}_{name}_mean"] = float(np.mean(v))
        out[f"{prefix}_{name}_std"] = float(np.std(v))
        out[f"{prefix}_{name}_median"] = float(np.median(v))
        out[f"{prefix}_{name}_p10"] = float(np.percentile(v, 10))
        out[f"{prefix}_{name}_p90"] = float(np.percentile(v, 90))
        out[f"{prefix}_{name}_iqr"] = float(p75 - p25)

    return out


def hue_stats(h, prefix):
    if h is None or len(h) == 0:
        return {
            f"{prefix}_H_circular_mean": np.nan,
            f"{prefix}_H_resultant_strength": np.nan,
            f"{prefix}_H_sin_mean": np.nan,
            f"{prefix}_H_cos_mean": np.nan,
        }

    rad = np.deg2rad(h.astype(np.float32))
    s = float(np.mean(np.sin(rad)))
    c = float(np.mean(np.cos(rad)))

    mean_deg = float((np.rad2deg(np.arctan2(s, c)) + 360.0) % 360.0)
    strength = float(math.sqrt(s * s + c * c))

    return {
        f"{prefix}_H_circular_mean": mean_deg,
        f"{prefix}_H_resultant_strength": strength,
        f"{prefix}_H_sin_mean": s,
        f"{prefix}_H_cos_mean": c,
    }


def empty_features(roi):
    out = {}

    for key in [
        "pixels_mask_raw",
        "pixels_mask_clean",
        "pixels_after_L_filter",
        "pixels_after_kmeans",
        "pixels_core",
    ]:
        out[f"{roi}_{key}"] = 0

    for key in [
        "L_low_threshold",
        "L_high_threshold",
        "main_cluster_ratio",
        "main_cluster_L",
        "MAD_distance_threshold",
        "core_ratio_vs_raw",
        "core_ratio_vs_clean",
    ]:
        out[f"{roi}_{key}"] = np.nan

    out[f"{roi}_kmeans_fallback"] = 1
    out[f"{roi}_mad_fallback"] = 1

    for name in ["L", "a", "b", "C", "H", "S", "V", "R", "G", "B"]:
        out[f"{roi}_rep_{name}"] = np.nan

    for prefix, names in [
        (f"{roi}_rgb", ["R", "G", "B"]),
        (f"{roi}_lab", ["L", "a", "b"]),
        (f"{roi}_hsv", ["H", "S", "V"]),
    ]:
        out.update(channel_stats(np.empty((0, 3)), names, prefix))

    out.update(hue_stats(np.array([]), f"{roi}_hsv"))

    return out


def compute_region_features(bgr, raw_mask, roi, args):
    import cv2

    raw = raw_mask > 0
    out = {f"{roi}_pixels_mask_raw": int(raw.sum())}

    if raw.sum() < args.min_pixels:
        return {**empty_features(roi), **out}, np.zeros(raw.shape, dtype=bool)

    clean = clean_mask(raw_mask, roi, args.erode_iter) > 0
    out[f"{roi}_pixels_mask_clean"] = int(clean.sum())

    if clean.sum() < args.min_pixels:
        return {**empty_features(roi), **out}, clean

    work = bgr
    if args.median_ksize and args.median_ksize >= 3:
        k = args.median_ksize if args.median_ksize % 2 == 1 else args.median_ksize + 1
        work = cv2.medianBlur(bgr, k)

    rgb_img, lab_img, hsv_img = bgr_to_spaces(work)

    lab0 = lab_img[clean]
    keep_l, l_low, l_high = l_filter(lab0, roi, args)

    idx_clean = np.flatnonzero(clean.reshape(-1))
    flat_l = np.zeros(clean.size, dtype=bool)
    flat_l[idx_clean[keep_l]] = True
    mask_l = flat_l.reshape(clean.shape)

    out[f"{roi}_L_low_threshold"] = l_low
    out[f"{roi}_L_high_threshold"] = l_high
    out[f"{roi}_pixels_after_L_filter"] = int(mask_l.sum())

    if mask_l.sum() < args.min_pixels:
        return {**empty_features(roi), **out}, mask_l

    lab1 = lab_img[mask_l]
    keep_k, cluster_ratio, cluster_L = kmeans_main_cluster(lab1, roi, args)

    idx_l = np.flatnonzero(mask_l.reshape(-1))
    flat_k = np.zeros(mask_l.size, dtype=bool)
    flat_k[idx_l[keep_k]] = True
    mask_k = flat_k.reshape(mask_l.shape)

    out[f"{roi}_main_cluster_ratio"] = cluster_ratio
    out[f"{roi}_main_cluster_L"] = cluster_L
    out[f"{roi}_pixels_after_kmeans"] = int(mask_k.sum())
    out[f"{roi}_kmeans_fallback"] = 0

    if mask_k.sum() < args.min_pixels:
        mask_k = mask_l
        out[f"{roi}_kmeans_fallback"] = 1

    lab2 = lab_img[mask_k]
    keep_mad, mad_threshold = mad_filter(lab2, args.mad_z)

    idx_k = np.flatnonzero(mask_k.reshape(-1))
    flat_mad = np.zeros(mask_k.size, dtype=bool)
    flat_mad[idx_k[keep_mad]] = True
    core = flat_mad.reshape(mask_k.shape)

    out[f"{roi}_MAD_distance_threshold"] = mad_threshold
    out[f"{roi}_pixels_core"] = int(core.sum())
    out[f"{roi}_mad_fallback"] = 0

    if core.sum() < args.min_pixels:
        core = mask_k
        out[f"{roi}_mad_fallback"] = 1
        out[f"{roi}_pixels_core"] = int(core.sum())

    out[f"{roi}_core_ratio_vs_raw"] = float(core.sum() / max(raw.sum(), 1))
    out[f"{roi}_core_ratio_vs_clean"] = float(core.sum() / max(clean.sum(), 1))

    rgb_pix = rgb_img[core]
    lab_pix = lab_img[core]
    hsv_pix = hsv_img[core]

    out.update(channel_stats(rgb_pix, ["R", "G", "B"], f"{roi}_rgb"))
    out.update(channel_stats(lab_pix, ["L", "a", "b"], f"{roi}_lab"))
    out.update(channel_stats(hsv_pix, ["H", "S", "V"], f"{roi}_hsv"))
    out.update(hue_stats(hsv_pix[:, 0] if len(hsv_pix) else np.array([]), f"{roi}_hsv"))

    if args.rep_method == "legacy":
        rep_lab, rep_cluster_ratio, rep_cluster_L = legacy_representative_color(
            lab1,
            roi,
            args,
        )
        out[f"{roi}_legacy_rep_cluster_ratio"] = rep_cluster_ratio
        out[f"{roi}_legacy_rep_cluster_L"] = rep_cluster_L

        if rep_lab is None:
            rep_lab = np.mean(lab_pix, axis=0)

    else:
        rep_lab = np.mean(lab_pix, axis=0)
        out[f"{roi}_legacy_rep_cluster_ratio"] = np.nan
        out[f"{roi}_legacy_rep_cluster_L"] = np.nan

    rep_rgb = np.mean(rgb_pix, axis=0)
    rep_hsv = np.mean(hsv_pix, axis=0)

    out[f"{roi}_rep_L"] = float(rep_lab[0])
    out[f"{roi}_rep_a"] = float(rep_lab[1])
    out[f"{roi}_rep_b"] = float(rep_lab[2])
    out[f"{roi}_rep_C"] = float(np.sqrt(rep_lab[1] ** 2 + rep_lab[2] ** 2))
    out[f"{roi}_rep_R"] = float(rep_rgb[0])
    out[f"{roi}_rep_G"] = float(rep_rgb[1])
    out[f"{roi}_rep_B"] = float(rep_rgb[2])
    out[f"{roi}_rep_H"] = float(rep_hsv[0])
    out[f"{roi}_rep_S"] = float(rep_hsv[1])
    out[f"{roi}_rep_V"] = float(rep_hsv[2])

    return out, core


def add_pair_features(row, left, right):
    needed = [
        f"{left}_rep_L", f"{left}_rep_a", f"{left}_rep_b",
        f"{right}_rep_L", f"{right}_rep_a", f"{right}_rep_b",
    ]

    if not all(k in row and pd.notna(row[k]) for k in needed):
        return

    dL = row[f"{left}_rep_L"] - row[f"{right}_rep_L"]
    da = row[f"{left}_rep_a"] - row[f"{right}_rep_a"]
    db = row[f"{left}_rep_b"] - row[f"{right}_rep_b"]

    prefix = f"{left}_{right}"

    row[f"{prefix}_delta_L"] = float(dL)
    row[f"{prefix}_delta_a"] = float(da)
    row[f"{prefix}_delta_b"] = float(db)
    row[f"{prefix}_deltaE76"] = float(math.sqrt(dL * dL + da * da + db * db))

    denom = abs(row[f"{left}_rep_L"]) + abs(row[f"{right}_rep_L"])
    row[f"{prefix}_michelson_L"] = float(abs(dL) / denom) if denom else np.nan

    for ch in ["C", "S", "V", "R", "G", "B"]:
        lk = f"{left}_rep_{ch}"
        rk = f"{right}_rep_{ch}"
        if lk in row and rk in row and pd.notna(row[lk]) and pd.notna(row[rk]):
            row[f"{prefix}_delta_{ch}"] = float(row[lk] - row[rk])


def lab_to_bgr(L, a, b):
    import cv2

    if not np.isfinite([L, a, b]).all():
        return (128, 128, 128)

    lab = np.array([[[np.clip(L, 0, 100), np.clip(a, -128, 127), np.clip(b, -128, 127)]]], dtype=np.float32)
    bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)[0, 0]
    bgr = np.clip(bgr * 255.0, 0, 255).astype(np.uint8)

    return tuple(int(x) for x in bgr)


def draw_debug(bgr, masks, core_masks, features, out_path):
    import cv2

    canvas = bgr.copy()
    overlay = bgr.copy()

    for roi in ROI_ORDER:
        mask = masks.get(roi)
        if mask is None:
            continue

        color = ROI_COLORS.get(roi, (255, 255, 255))
        overlay[mask > 0] = (0.62 * overlay[mask > 0] + 0.38 * np.array(color)).astype(np.uint8)

        contours, _ = cv2.findContours((mask > 0).astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, color, 1)

        core = core_masks.get(roi)
        if core is not None:
            contours, _ = cv2.findContours((core > 0).astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(canvas, contours, -1, (255, 255, 255), 1)

    canvas = cv2.addWeighted(overlay, 0.55, canvas, 0.45, 0)

    h, w = canvas.shape[:2]
    panel_w = 310
    panel_h = max(h, 34 * len(ROI_ORDER) + 30)
    panel = np.full((panel_h, panel_w, 3), 245, dtype=np.uint8)

    y = 18
    for roi in ROI_ORDER:
        L = features.get(f"{roi}_rep_L", np.nan)
        a = features.get(f"{roi}_rep_a", np.nan)
        b = features.get(f"{roi}_rep_b", np.nan)

        swatch = lab_to_bgr(L, a, b)

        cv2.rectangle(panel, (10, y - 12), (44, y + 12), swatch, -1)
        cv2.rectangle(panel, (10, y - 12), (44, y + 12), (0, 0, 0), 1)

        text = f"{roi:11s} L={L:5.1f} a={a:5.1f} b={b:5.1f}"
        cv2.putText(panel, text, (52, y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (20, 20, 20), 1, cv2.LINE_AA)
        y += 34

    if panel.shape[0] > canvas.shape[0]:
        pad = np.full((panel.shape[0] - canvas.shape[0], w, 3), 255, dtype=np.uint8)
        canvas = np.vstack([canvas, pad])
    elif panel.shape[0] < canvas.shape[0]:
        pad = np.full((canvas.shape[0] - panel.shape[0], panel_w, 3), 245, dtype=np.uint8)
        panel = np.vstack([panel, pad])

    out = np.hstack([canvas, panel])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), out)


def extract_one(path, face_detector, args):
    bgr, alpha = read_bgr(path, args.input_color_mode)

    landmarks = face_detector.detect(bgr)
    if landmarks is None:
        raise RuntimeError("MediaPipe face not detected")

    masks, bbox = build_roi_masks(bgr, alpha, landmarks)

    features = {
        "image_width": int(bgr.shape[1]),
        "image_height": int(bgr.shape[0]),
        "face_bbox_x1": int(bbox[0]),
        "face_bbox_y1": int(bbox[1]),
        "face_bbox_x2": int(bbox[2]),
        "face_bbox_y2": int(bbox[3]),
    }

    core_masks = {}

    for roi in ROI_ORDER:
        roi_features, core = compute_region_features(bgr, masks[roi], roi, args)
        features.update(roi_features)
        core_masks[roi] = core

    pairs = [
        ("skin_core", "hair"),
        ("skin", "hair"),
        ("forehead", "hair"),
        ("left_cheek", "right_cheek"),
        ("forehead", "left_cheek"),
        ("forehead", "right_cheek"),
        ("skin_core", "lip"),
        ("skin", "lip"),
        ("skin_core", "iris"),
        ("skin", "iris"),
        ("hair", "iris"),
        ("lip", "iris"),
    ]

    for left, right in pairs:
        add_pair_features(features, left, right)

    features["cheek_rep_L_mean"] = float(np.nanmean([
        features.get("left_cheek_rep_L", np.nan),
        features.get("right_cheek_rep_L", np.nan),
    ]))
    features["cheek_rep_C_mean"] = float(np.nanmean([
        features.get("left_cheek_rep_C", np.nan),
        features.get("right_cheek_rep_C", np.nan),
    ]))
    features["forehead_cheek_deltaE_mean"] = float(np.nanmean([
        features.get("forehead_left_cheek_deltaE76", np.nan),
        features.get("forehead_right_cheek_deltaE76", np.nan),
    ]))

    return features, masks, core_masks, bgr


def append_preview(preview_rows, meta, features, debug_image):
    for roi in ROI_ORDER:
        preview_rows.append({
            **meta,
            "roi": roi,
            "debug_image": debug_image,
            "pixels_raw": features.get(f"{roi}_pixels_mask_raw", np.nan),
            "pixels_clean": features.get(f"{roi}_pixels_mask_clean", np.nan),
            "pixels_core": features.get(f"{roi}_pixels_core", np.nan),
            "core_ratio_vs_raw": features.get(f"{roi}_core_ratio_vs_raw", np.nan),
            "rep_L": features.get(f"{roi}_rep_L", np.nan),
            "rep_a": features.get(f"{roi}_rep_a", np.nan),
            "rep_b": features.get(f"{roi}_rep_b", np.nan),
            "rep_C": features.get(f"{roi}_rep_C", np.nan),
            "rep_H": features.get(f"{roi}_rep_H", np.nan),
            "rep_S": features.get(f"{roi}_rep_S", np.nan),
            "rep_V": features.get(f"{roi}_rep_V", np.nan),
            "main_cluster_ratio": features.get(f"{roi}_main_cluster_ratio", np.nan),
            "kmeans_fallback": features.get(f"{roi}_kmeans_fallback", np.nan),
            "mad_fallback": features.get(f"{roi}_mad_fallback", np.nan),
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out_csv", required=True)
    parser.add_argument("--base_dir", default=".")
    parser.add_argument("--debug_dir", default=None)
    parser.add_argument("--debug_every", type=int, default=1)
    parser.add_argument("--debug_max", type=int, default=0)
    parser.add_argument("--preview_csv", default=None)

    parser.add_argument("--min_pixels", type=int, default=60)
    parser.add_argument("--median_ksize", type=int, default=5)
    parser.add_argument("--erode_iter", type=int, default=1)

    parser.add_argument("--k_clusters", type=int, default=3)
    parser.add_argument("--hair_k_clusters", type=int, default=3)
    parser.add_argument("--kmeans_method", choices=["full", "minibatch"], default="full")
    parser.add_argument("--max_kmeans_pixels", type=int, default=12000)
    parser.add_argument(
        "--rep_method",
        choices=["legacy", "robust_mean"],
        default="legacy",
        help="legacy = 使用一開始那份資料的 KMeans 群集 median 代表色；robust_mean = 使用新版 MAD 後 mean",
    )

    parser.add_argument("--mad_z", type=float, default=2.5)

    parser.add_argument("--skin_l_low_pct", type=float, default=5.0)
    parser.add_argument("--skin_l_high_pct", type=float, default=95.0)
    parser.add_argument("--hair_l_low_pct", type=float, default=1.0)
    parser.add_argument("--hair_l_high_pct", type=float, default=99.0)
    parser.add_argument("--lip_l_low_pct", type=float, default=3.0)
    parser.add_argument("--lip_l_high_pct", type=float, default=97.0)
    parser.add_argument("--iris_l_low_pct", type=float, default=2.0)
    parser.add_argument("--iris_l_high_pct", type=float, default=98.0)

    parser.add_argument(
        "--input_color_mode",
        choices=["bgr", "swap_rb"],
        default="bgr",
    )

    parser.add_argument("--seed", type=int, default=42)

    default_model_path = (
        Path(__file__).resolve().parent
        / "models"
        / "face_landmarker.task"
    )
    parser.add_argument(
        "--face_landmarker_model",
        default=str(default_model_path),
        help="MediaPipe Face Landmarker .task 模型路徑",
    )

    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, encoding="utf-8-sig")
    base_dir = Path(args.base_dir)
    debug_dir = Path(args.debug_dir) if args.debug_dir else None

    rows = []
    preview_rows = []
    debug_count = 0

    face_detector = FaceLandmarkDetector(
        model_path=args.face_landmarker_model,
    )

    try:
        for i, item in manifest.iterrows():
            path = resolve_path(image_path_from_row(item), base_dir)
            debug_image = ""

            try:
                features, masks, core_masks, bgr = extract_one(
                    path,
                    face_detector,
                    args,
                )
                status = "ok"
                error = ""

                should_debug = (
                    debug_dir is not None
                    and args.debug_every > 0
                    and i % args.debug_every == 0
                )

                if should_debug and (args.debug_max <= 0 or debug_count < args.debug_max):
                    label = str(item.get("label_12", item.get("Target_12Class", "unknown")))
                    safe_name = "".join(
                        ch if ch.isalnum() or ch in "._-" else "_"
                        for ch in f"{i:06d}_{label}_{path.stem}.jpg"
                    )
                    out_path = debug_dir / safe_name
                    draw_debug(bgr, masks, core_masks, features, out_path)
                    debug_image = str(out_path.as_posix())
                    debug_count += 1

            except Exception as exc:
                features = {}
                status = "error"
                error = f"{type(exc).__name__}: {exc}"

            row = item.to_dict()
            row.update(features)
            row["feature_status"] = status
            row["feature_error"] = error
            row["debug_image"] = debug_image
            rows.append(row)

            meta = {
                "image_id": row.get("image_id", Path(path).stem),
                "image_path": row.get("image_path", str(path)),
                "split": row.get("split", row.get("Dataset_Split", "")),
                "season": row.get("season", row.get("Target_Season", "")),
                "subtype": row.get("subtype", row.get("Target_SubSeason", "")),
                "label_12": row.get("label_12", row.get("Target_12Class", "")),
            }
            append_preview(preview_rows, meta, features, debug_image)

            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(manifest)}")
    finally:
        face_detector.close()

    out = pd.DataFrame(rows)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print("Saved features:", out_csv)
    print(out["feature_status"].value_counts(dropna=False).to_string())

    if args.preview_csv:
        preview_csv = Path(args.preview_csv)
        preview_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(preview_rows).to_csv(preview_csv, index=False, encoding="utf-8-sig")
        print("Saved preview CSV:", preview_csv)

    if debug_dir is not None:
        print("Saved debug images:", debug_dir)


class FaceLandmarkDetector:
    """MediaPipe Tasks Face Landmarker 單張圖片偵測器。"""

    def __init__(
        self,
        model_path: str | Path,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
    ) -> None:
        model_path = Path(model_path).resolve()

        if not model_path.is_file():
            raise FileNotFoundError(
                f"找不到 Face Landmarker 模型：{model_path}"
            )

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path),
            ),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_presence_confidence,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        self._landmarker = (
            mp.tasks.vision.FaceLandmarker.create_from_options(options)
        )
        self._closed = False

    def detect(self, image_bgr: np.ndarray) -> list[Any] | None:
        if self._closed:
            raise RuntimeError("Face Landmarker 已關閉")

        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("輸入圖片為空")

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image_rgb = np.ascontiguousarray(image_rgb, dtype=np.uint8)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=image_rgb,
        )
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return None

        landmarks = result.face_landmarks[0]

        # 虹膜 ROI 使用 468～476，因此至少需要 477 點；
        # 這裡要求 478 點以符合原本 refine_landmarks=True 的輸出。
        if len(landmarks) < 478:
            raise RuntimeError(
                f"Face Landmarker 僅輸出 {len(landmarks)} 個點，"
                "不足以執行目前的虹膜 ROI。"
            )

        return landmarks

    def close(self) -> None:
        landmarker = getattr(self, "_landmarker", None)

        if landmarker is None:
            return

        self._landmarker = None

        try:
            landmarker.close()
        except RuntimeError as exc:
            if "cannot schedule new futures after shutdown" not in str(exc):
                raise


if __name__ == "__main__":
    main()