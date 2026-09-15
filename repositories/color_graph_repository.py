from config.neo4j import Neo4jConnection


class ColorGraphRepository:

    SOURCE = "IQON3000"

    @staticmethod
    def get_all_color_families():
        """
        取得 IQON3000 所有 ColorFamily。
        """

        query = """
        MATCH (c:ColorFamily)

        WHERE c.source = $source

        RETURN
            c.key AS key,
            c.name_zh AS name_zh

        ORDER BY c.key
        """

        with Neo4jConnection.get_session() as session:

            result = session.run(
                query,
                source=ColorGraphRepository.SOURCE,
            )

            return [
                {
                    "key": record["key"],
                    "name_zh": record["name_zh"],
                }
                for record in result
            ]

    @staticmethod
    def get_top_to_bottom_matches(
        color_key: str,
        limit: int,
        include_same_color: bool = True,
    ):
        """
        上衣顏色 -> 推薦下著顏色
        """

        query = """
        MATCH
            (top:ColorFamily {key: $color_key})
            -[r:MATCHES_WITH]->
            (bottom:ColorFamily)

        WHERE
            r.source = $source

            AND (
                $include_same_color = true
                OR r.same_color = false
            )

        RETURN
            top.key AS source_color,

            bottom.key AS color,
            bottom.name_zh AS color_name,

            r.score_top_to_bottom
                AS recommendation_score,

            r.rank_top_to_bottom
                AS rank,

            r.pair_count
                AS pair_count,

            r.p_bottom_given_top
                AS conditional_probability,

            r.lift
                AS lift,

            r.same_color
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
                color_key=color_key,
                source=ColorGraphRepository.SOURCE,
                include_same_color=include_same_color,
                limit=limit,
            )

            return [
                dict(record)
                for record in result
            ]

    @staticmethod
    def get_bottom_to_top_matches(
        color_key: str,
        limit: int,
        include_same_color: bool = True,
    ):
        """
        下著顏色 -> 推薦上衣顏色。

        不需要另外建立反向 relationship，
        直接反向查詢 MATCHES_WITH。
        """

        query = """
        MATCH
            (top:ColorFamily)
            -[r:MATCHES_WITH]->
            (bottom:ColorFamily {key: $color_key})

        WHERE
            r.source = $source

            AND (
                $include_same_color = true
                OR r.same_color = false
            )

        RETURN
            bottom.key AS source_color,

            top.key AS color,
            top.name_zh AS color_name,

            r.score_bottom_to_top
                AS recommendation_score,

            r.rank_bottom_to_top
                AS rank,

            r.pair_count
                AS pair_count,

            r.p_top_given_bottom
                AS conditional_probability,

            r.lift
                AS lift,

            r.same_color
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
                color_key=color_key,
                source=ColorGraphRepository.SOURCE,
                include_same_color=include_same_color,
                limit=limit,
            )

            return [
                dict(record)
                for record in result
            ]