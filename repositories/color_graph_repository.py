from config.neo4j import Neo4jConnection


class ColorGraphRepository:

    # Step 15 匯入新版 102 色 ColorShade 時使用的 source
    SOURCE = "IQON3000_REFINED"

    @staticmethod
    def find_nearest_color_shade(
        lab_l: float,
        lab_a: float,
        lab_b: float,
    ):
        """
        用 CIE76（Lab Euclidean distance）在 102 個 refined ColorShade
        中找到距離輸入顏色最近的一個 Shade。

        直接在 Neo4j 計算，只回傳最近 1 個節點。
        """

        query = """
        MATCH (c:ColorShade)
        WHERE c.source = $source

        WITH
            c,
            sqrt(
                (c.lab_l - $lab_l) * (c.lab_l - $lab_l)
                +
                (c.lab_a - $lab_a) * (c.lab_a - $lab_a)
                +
                (c.lab_b - $lab_b) * (c.lab_b - $lab_b)
            ) AS delta_e

        RETURN
            c.shade_id AS shade_id,
            c.hex AS hex,
            c.rgb_r AS rgb_r,
            c.rgb_g AS rgb_g,
            c.rgb_b AS rgb_b,
            c.lab_l AS lab_l,
            c.lab_a AS lab_a,
            c.lab_b AS lab_b,
            c.chroma AS chroma,
            c.hue_deg AS hue_deg,
            c.dominant_source_family AS dominant_source_family,
            c.source_family_purity AS source_family_purity,
            delta_e AS delta_e

        ORDER BY delta_e ASC
        LIMIT 1
        """

        with Neo4jConnection.get_session() as session:
            record = session.run(
                query,
                source=ColorGraphRepository.SOURCE,
                lab_l=float(lab_l),
                lab_a=float(lab_a),
                lab_b=float(lab_b),
            ).single()

            if record is None:
                return None

            return dict(record)

    @staticmethod
    def get_top_to_bottom_matches(
        shade_id: str,
        limit: int,
        include_same_color: bool = True,
    ):
        """
        上衣 ColorShade -> 推薦下著 ColorShade。
        """

        query = """
        MATCH
            (top:ColorShade {shade_id: $shade_id})
            -[r:MATCHES_WITH]->
            (bottom:ColorShade)

        WHERE
            r.source = $source
            AND (
                $include_same_color = true
                OR coalesce(r.same_shade, false) = false
            )

        RETURN
            top.shade_id AS source_shade_id,
            top.hex AS source_color,

            bottom.shade_id AS shade_id,
            bottom.hex AS color,
            bottom.hex AS hex,
            bottom.rgb_r AS rgb_r,
            bottom.rgb_g AS rgb_g,
            bottom.rgb_b AS rgb_b,
            bottom.lab_l AS lab_l,
            bottom.lab_a AS lab_a,
            bottom.lab_b AS lab_b,
            bottom.chroma AS chroma,
            bottom.hue_deg AS hue_deg,
            bottom.dominant_source_family AS dominant_source_family,

            r.score_top_to_bottom
                AS recommendation_score,

            r.rank_top_to_bottom
                AS rank,

            r.pair_count
                AS pair_count,

            r.p_bottom_given_top
                AS conditional_probability,

            r.p_bottom_given_top_smoothed
                AS conditional_probability_smoothed,

            r.lift
                AS lift,

            r.lift_shrunk
                AS lift_shrunk,

            r.support_confidence
                AS support_confidence,

            r.same_shade
                AS same_shade,

            r.same_shade
                AS same_color,

            r.avg_like_count
                AS avg_like_count

        ORDER BY
            r.rank_top_to_bottom ASC

        LIMIT $limit
        """

        with Neo4jConnection.get_session() as session:
            result = session.run(
                query,
                shade_id=shade_id,
                source=ColorGraphRepository.SOURCE,
                include_same_color=include_same_color,
                limit=int(limit),
            )

            return [
                dict(record)
                for record in result
            ]

    @staticmethod
    def get_bottom_to_top_matches(
        shade_id: str,
        limit: int,
        include_same_color: bool = True,
    ):
        """
        下著 ColorShade -> 推薦上衣 ColorShade。

        Neo4j 只需要保存 top -> bottom 的 MATCHES_WITH，
        這裡直接反向查詢 relationship。
        """

        query = """
        MATCH
            (top:ColorShade)
            -[r:MATCHES_WITH]->
            (bottom:ColorShade {shade_id: $shade_id})

        WHERE
            r.source = $source
            AND (
                $include_same_color = true
                OR coalesce(r.same_shade, false) = false
            )

        RETURN
            bottom.shade_id AS source_shade_id,
            bottom.hex AS source_color,

            top.shade_id AS shade_id,
            top.hex AS color,
            top.hex AS hex,
            top.rgb_r AS rgb_r,
            top.rgb_g AS rgb_g,
            top.rgb_b AS rgb_b,
            top.lab_l AS lab_l,
            top.lab_a AS lab_a,
            top.lab_b AS lab_b,
            top.chroma AS chroma,
            top.hue_deg AS hue_deg,
            top.dominant_source_family AS dominant_source_family,

            r.score_bottom_to_top
                AS recommendation_score,

            r.rank_bottom_to_top
                AS rank,

            r.pair_count
                AS pair_count,

            r.p_top_given_bottom
                AS conditional_probability,

            r.p_top_given_bottom_smoothed
                AS conditional_probability_smoothed,

            r.lift
                AS lift,

            r.lift_shrunk
                AS lift_shrunk,

            r.support_confidence
                AS support_confidence,

            r.same_shade
                AS same_shade,

            r.same_shade
                AS same_color,

            r.avg_like_count
                AS avg_like_count

        ORDER BY
            r.rank_bottom_to_top ASC

        LIMIT $limit
        """

        with Neo4jConnection.get_session() as session:
            result = session.run(
                query,
                shade_id=shade_id,
                source=ColorGraphRepository.SOURCE,
                include_same_color=include_same_color,
                limit=int(limit),
            )

            return [
                dict(record)
                for record in result
            ]
