# 根據已經算出的 ROI 統計數值，判斷每個臉部區域的取色結果是否可信。

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


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

MODEL_ROIS = [
    "skin_core",
    "forehead",
    "left_cheek",
    "right_cheek",
    "lip",
    "iris",
    "hair",
]

ID_CANDIDATES = [
    "image_id",
    "image_path",
    "processed_image",
    "path",
    "filename",
    "Image_Name",
]

SPLIT_CANDIDATES = [
    "split",
    "Dataset_Split",
    "dataset_split",
]


def read_csv(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path)


def write_json(data: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def quantile_or_default(
    series: pd.Series,
    q: float,
    default: float,
    minimum_valid: int = 10,
) -> float:
    valid = pd.to_numeric(series, errors="coerce")
    valid = valid[np.isfinite(valid)]
    if len(valid) < minimum_valid:
        return float(default)
    return float(valid.quantile(q))


def find_split_column(df: pd.DataFrame) -> str | None:
    for column in SPLIT_CANDIDATES:
        if column in df.columns:
            return column
    return None


def select_fit_rows(
    df: pd.DataFrame,
    train_value: str,
) -> tuple[pd.DataFrame, str | None]:
    split_col = find_split_column(df)

    valid = pd.Series(True, index=df.index)
    if "feature_status" in df.columns:
        valid &= (
            df["feature_status"]
            .astype("string")
            .str.strip()
            .str.lower()
            .eq("ok")
        )

    if split_col is None:
        return df.loc[valid].copy(), None

    normalized_split = (
        df[split_col]
        .astype("string")
        .str.strip()
        .str.lower()
    )
    fit_mask = valid & normalized_split.eq(train_value.lower())

    if int(fit_mask.sum()) < 10:
        raise ValueError(
            f"在欄位 {split_col!r} 中找不到足夠的 "
            f"{train_value!r} 資料列，只有 {int(fit_mask.sum())} 列。"
        )

    return df.loc[fit_mask].copy(), split_col


def delta_e76_from_representatives(
    df: pd.DataFrame,
    left: str,
    right: str,
) -> pd.Series:
    left_values = np.column_stack([
        numeric_series(df, f"{left}_rep_L"),
        numeric_series(df, f"{left}_rep_a"),
        numeric_series(df, f"{left}_rep_b"),
    ])
    right_values = np.column_stack([
        numeric_series(df, f"{right}_rep_L"),
        numeric_series(df, f"{right}_rep_a"),
        numeric_series(df, f"{right}_rep_b"),
    ])

    valid = np.isfinite(left_values).all(axis=1) & np.isfinite(right_values).all(axis=1)
    result = np.full(len(df), np.nan, dtype=np.float64)
    result[valid] = np.linalg.norm(left_values[valid] - right_values[valid], axis=1)
    return pd.Series(result, index=df.index)


def fit_thresholds(
    fit_df: pd.DataFrame,
    low_quantile: float,
    high_quantile: float,
) -> dict:
    thresholds: dict[str, dict[str, float]] = {"roi": {}}

    default_raw_pixels = {
        "skin": 1000,
        "skin_core": 300,
        "forehead": 80,
        "left_cheek": 80,
        "right_cheek": 80,
        "lip": 60,
        "left_iris": 20,
        "right_iris": 20,
        "iris": 40,
        "hair": 80,
    }

    default_core_pixels = {
        "skin": 300,
        "skin_core": 120,
        "forehead": 40,
        "left_cheek": 40,
        "right_cheek": 40,
        "lip": 30,
        "left_iris": 10,
        "right_iris": 10,
        "iris": 20,
        "hair": 40,
    }

    for roi in ROI_ORDER:
        raw = numeric_series(fit_df, f"{roi}_pixels_mask_raw")
        core = numeric_series(fit_df, f"{roi}_pixels_core")
        core_ratio = numeric_series(fit_df, f"{roi}_core_ratio_vs_raw")
        cluster_ratio = numeric_series(fit_df, f"{roi}_main_cluster_ratio")

        thresholds["roi"][roi] = {
            "min_raw_pixels": max(
                1.0,
                quantile_or_default(
                    raw[raw > 0],
                    low_quantile,
                    default_raw_pixels[roi],
                ),
            ),
            "min_core_pixels": max(
                1.0,
                quantile_or_default(
                    core[core > 0],
                    low_quantile,
                    default_core_pixels[roi],
                ),
            ),
            "min_core_ratio": float(np.clip(
                quantile_or_default(
                    core_ratio[(core_ratio >= 0) & (core_ratio <= 1)],
                    low_quantile,
                    0.10,
                ),
                0.02,
                0.90,
            )),
            "min_cluster_ratio": float(np.clip(
                quantile_or_default(
                    cluster_ratio[(cluster_ratio >= 0) & (cluster_ratio <= 1)],
                    low_quantile,
                    0.25,
                ),
                0.05,
                0.95,
            )),
        }

    cheek_delta = delta_e76_from_representatives(
        fit_df,
        "left_cheek",
        "right_cheek",
    )
    iris_delta = delta_e76_from_representatives(
        fit_df,
        "left_iris",
        "right_iris",
    )

    thresholds["pair"] = {
        "max_cheek_deltaE76": max(
            3.0,
            quantile_or_default(
                cheek_delta,
                high_quantile,
                15.0,
            ),
        ),
        "max_iris_deltaE76": max(
            3.0,
            quantile_or_default(
                iris_delta,
                high_quantile,
                18.0,
            ),
        ),
    }

    return thresholds


def build_roi_flags(
    df: pd.DataFrame,
    roi: str,
    thresholds: dict[str, float],
    quality_ok_threshold: float,
) -> pd.DataFrame:
    raw = numeric_series(df, f"{roi}_pixels_mask_raw")
    core = numeric_series(df, f"{roi}_pixels_core")
    core_ratio = numeric_series(df, f"{roi}_core_ratio_vs_raw")
    cluster_ratio = numeric_series(df, f"{roi}_main_cluster_ratio")
    kmeans_fallback = numeric_series(df, f"{roi}_kmeans_fallback").fillna(1)
    mad_fallback = numeric_series(df, f"{roi}_mad_fallback").fillna(1)

    rep_values = np.column_stack([
        numeric_series(df, f"{roi}_rep_L"),
        numeric_series(df, f"{roi}_rep_a"),
        numeric_series(df, f"{roi}_rep_b"),
    ])
    valid_rep = np.isfinite(rep_values).all(axis=1)

    flag_missing = (
        raw.isna()
        | core.isna()
        | (raw <= 0)
        | (core <= 0)
        | (~pd.Series(valid_rep, index=df.index))
    )
    flag_low_raw = raw < thresholds["min_raw_pixels"]
    flag_low_core = core < thresholds["min_core_pixels"]
    flag_low_core_ratio = (
        core_ratio.isna()
        | (core_ratio < thresholds["min_core_ratio"])
    )
    flag_low_cluster_ratio = (
        cluster_ratio.isna()
        | (cluster_ratio < thresholds["min_cluster_ratio"])
    )
    flag_kmeans = kmeans_fallback >= 0.5
    flag_mad = mad_fallback >= 0.5
    flag_any_fallback = flag_kmeans | flag_mad

    components = np.column_stack([
        ~flag_missing,
        ~flag_low_raw,
        ~flag_low_core,
        ~flag_low_core_ratio,
        ~flag_low_cluster_ratio,
        ~flag_kmeans,
        ~flag_mad,
    ]).astype(np.float32)

    quality_score = components.mean(axis=1)
    quality_ok = quality_score >= quality_ok_threshold

    return pd.DataFrame({
        f"{roi}_flag_missing": flag_missing.astype(np.int8),
        f"{roi}_flag_low_raw_pixels": flag_low_raw.fillna(True).astype(np.int8),
        f"{roi}_flag_low_core_pixels": flag_low_core.fillna(True).astype(np.int8),
        f"{roi}_flag_low_core_ratio": flag_low_core_ratio.astype(np.int8),
        f"{roi}_flag_low_cluster_ratio": flag_low_cluster_ratio.astype(np.int8),
        f"{roi}_flag_kmeans_fallback": flag_kmeans.astype(np.int8),
        f"{roi}_flag_mad_fallback": flag_mad.astype(np.int8),
        f"{roi}_flag_any_fallback": flag_any_fallback.astype(np.int8),
        f"{roi}_quality_score": quality_score.astype(np.float32),
        f"{roi}_quality_ok": quality_ok.astype(np.int8),
    }, index=df.index)


def build_quality_table(
    df: pd.DataFrame,
    thresholds: dict,
    quality_ok_threshold: float,
) -> pd.DataFrame:
    parts = [
        build_roi_flags(
            df,
            roi,
            thresholds["roi"][roi],
            quality_ok_threshold,
        )
        for roi in ROI_ORDER
    ]
    flags = pd.concat(parts, axis=1)

    cheek_delta = delta_e76_from_representatives(
        df,
        "left_cheek",
        "right_cheek",
    )
    iris_delta = delta_e76_from_representatives(
        df,
        "left_iris",
        "right_iris",
    )

    flags["cheek_pair_deltaE76_quality"] = cheek_delta.astype(np.float32)
    flags["cheek_pair_asymmetry_flag"] = (
        cheek_delta.isna()
        | (cheek_delta > thresholds["pair"]["max_cheek_deltaE76"])
    ).astype(np.int8)

    flags["iris_pair_deltaE76_quality"] = iris_delta.astype(np.float32)
    flags["iris_pair_asymmetry_flag"] = (
        iris_delta.isna()
        | (iris_delta > thresholds["pair"]["max_iris_deltaE76"])
    ).astype(np.int8)

    flags["forehead_possible_occlusion_flag"] = (
        (flags["forehead_quality_ok"] == 0)
        & (
            (flags["forehead_flag_low_raw_pixels"] == 1)
            | (flags["forehead_flag_low_core_ratio"] == 1)
            | (flags["forehead_flag_low_cluster_ratio"] == 1)
        )
    ).astype(np.int8)

    flags["iris_possible_occlusion_flag"] = (
        (flags["iris_quality_ok"] == 0)
        | (flags["iris_pair_asymmetry_flag"] == 1)
    ).astype(np.int8)

    flags["hair_possible_crop_or_occlusion_flag"] = (
        (flags["hair_quality_ok"] == 0)
        & (
            (flags["hair_flag_low_raw_pixels"] == 1)
            | (flags["hair_flag_missing"] == 1)
        )
    ).astype(np.int8)

    model_quality_score_columns = [
        f"{roi}_quality_score"
        for roi in MODEL_ROIS
    ]
    flags["overall_quality_score"] = (
        flags[model_quality_score_columns]
        .mean(axis=1)
        .astype(np.float32)
    )

    model_quality_ok_columns = [
        f"{roi}_quality_ok"
        for roi in MODEL_ROIS
    ]
    flags["required_roi_bad_count"] = (
        (flags[model_quality_ok_columns] == 0)
        .sum(axis=1)
        .astype(np.int16)
    )
    flags["overall_quality_ok"] = (
        (flags["overall_quality_score"] >= quality_ok_threshold)
        & (flags["required_roi_bad_count"] <= 2)
    ).astype(np.int8)

    if "feature_status" in df.columns:
        extraction_error = ~(
            df["feature_status"]
            .astype("string")
            .str.strip()
            .str.lower()
            .eq("ok")
        )
    else:
        extraction_error = pd.Series(False, index=df.index)

    flags["feature_extraction_error_flag"] = extraction_error.astype(np.int8)

    return flags


def choose_id_columns(df: pd.DataFrame) -> list[str]:
    columns: list[str] = []

    for candidate in ID_CANDIDATES:
        if candidate in df.columns and candidate not in columns:
            columns.append(candidate)

    split_col = find_split_column(df)
    if split_col and split_col not in columns:
        columns.append(split_col)

    for candidate in [
        "season",
        "subtype",
        "label_12",
        "Target_Season",
        "Target_SubSeason",
        "Target_12Class",
        "feature_status",
        "feature_error",
        "debug_image",
    ]:
        if candidate in df.columns and candidate not in columns:
            columns.append(candidate)

    return columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "從 multiroi_robust_features.csv 的 ROI 統計值建立品質旗標，"
            "並輸出 flags-only 與合併後 CSV。"
        )
    )
    parser.add_argument("--features", required=True)
    parser.add_argument("--out_flags_csv", required=True)
    parser.add_argument("--out_merged_csv", required=True)
    parser.add_argument("--thresholds_json", required=True)
    parser.add_argument("--train_value", default="train")
    parser.add_argument("--low_quantile", type=float, default=0.05)
    parser.add_argument("--high_quantile", type=float, default=0.95)
    parser.add_argument("--quality_ok_threshold", type=float, default=0.67)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not 0.0 < args.low_quantile < 0.5:
        raise ValueError("--low_quantile 必須介於 0 與 0.5")
    if not 0.5 < args.high_quantile < 1.0:
        raise ValueError("--high_quantile 必須介於 0.5 與 1")
    if not 0.0 <= args.quality_ok_threshold <= 1.0:
        raise ValueError("--quality_ok_threshold 必須介於 0 與 1")

    df = read_csv(args.features)
    fit_df, split_col = select_fit_rows(df, args.train_value)

    thresholds = fit_thresholds(
        fit_df,
        args.low_quantile,
        args.high_quantile,
    )
    thresholds["fit_info"] = {
        "source_csv": str(Path(args.features).resolve()),
        "split_column": split_col,
        "train_value": args.train_value if split_col else None,
        "fit_rows": int(len(fit_df)),
        "low_quantile": args.low_quantile,
        "high_quantile": args.high_quantile,
        "quality_ok_threshold": args.quality_ok_threshold,
    }

    quality = build_quality_table(
        df,
        thresholds,
        args.quality_ok_threshold,
    )

    id_columns = choose_id_columns(df)
    flags_only = pd.concat(
        [
            df[id_columns].reset_index(drop=True),
            quality.reset_index(drop=True),
        ],
        axis=1,
    )

    merged = pd.concat(
        [
            df.reset_index(drop=True),
            quality.reset_index(drop=True),
        ],
        axis=1,
    )

    out_flags_csv = Path(args.out_flags_csv)
    out_merged_csv = Path(args.out_merged_csv)
    out_flags_csv.parent.mkdir(parents=True, exist_ok=True)
    out_merged_csv.parent.mkdir(parents=True, exist_ok=True)

    flags_only.to_csv(
        out_flags_csv,
        index=False,
        encoding="utf-8-sig",
    )
    merged.to_csv(
        out_merged_csv,
        index=False,
        encoding="utf-8-sig",
    )
    write_json(thresholds, args.thresholds_json)

    print("=== ROI quality flags ===")
    print(f"Source rows: {len(df)}")
    print(f"Threshold fit rows: {len(fit_df)}")
    print(f"Split column: {split_col}")
    print(f"Quality feature columns: {quality.shape[1]}")
    print(
        "Overall quality OK:",
        int(quality["overall_quality_ok"].sum()),
        "/",
        len(quality),
    )
    print("Saved flags:", out_flags_csv)
    print("Saved merged:", out_merged_csv)
    print("Saved thresholds:", args.thresholds_json)


if __name__ == "__main__":
    main()
