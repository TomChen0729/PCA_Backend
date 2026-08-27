from config.neo4j import Neo4jConnection


class ColorGraphRepository:

    @staticmethod
    def get_all_main_colors():
        """
        取得所有具有 MAIN_TO_SUB 關係的主色。
        """
        driver = Neo4jConnection.get_driver()

        query = """
        MATCH (main:Color)-[:MAIN_TO_SUB]->(:Color)
        WHERE main.hex IS NOT NULL
        RETURN DISTINCT main.hex AS hex
        """

        with driver.session() as session:
            result = session.run(query)

            return [
                record["hex"]
                for record in result
                if record["hex"]
            ]

    @staticmethod
    def get_all_sub_colors():
        """
        取得所有具有 MAIN_TO_SUB 關係的配色。
        用於「配色 -> 主色」的反向推薦。
        """
        driver = Neo4jConnection.get_driver()

        query = """
        MATCH (:Color)-[:MAIN_TO_SUB]->(sub:Color)
        WHERE sub.hex IS NOT NULL
        RETURN DISTINCT sub.hex AS hex
        """

        with driver.session() as session:
            result = session.run(query)

            return [
                record["hex"]
                for record in result
                if record["hex"]
            ]

    @staticmethod
    def get_matches_by_main_colors(main_colors: list[str]):
        """
        主色 -> 配色。
        根據多個相近主色，一次查詢所有搭配色。
        """
        driver = Neo4jConnection.get_driver()

        query = """
        MATCH (main:Color)-[r:MAIN_TO_SUB]->(sub:Color)
        WHERE toUpper(main.hex) IN $source_colors

        RETURN
            main.hex AS source_color,
            sub.hex AS color,
            r.count AS count,
            r.likes AS likes
        """

        normalized_colors = [
            color.upper()
            for color in main_colors
        ]

        with driver.session() as session:
            result = session.run(
                query,
                source_colors=normalized_colors,
            )

            return [
                {
                    "source_color": record["source_color"],
                    "color": record["color"],
                    "count": record["count"] or 0,
                    "likes": record["likes"] or 0,
                }
                for record in result
            ]

    @staticmethod
    def get_matches_by_sub_colors(sub_colors: list[str]):
        """
        配色 -> 主色。
        不需要新增 SUB_TO_MAIN 關係，直接反向查詢原本的 MAIN_TO_SUB。
        """
        driver = Neo4jConnection.get_driver()

        query = """
        MATCH (main:Color)-[r:MAIN_TO_SUB]->(sub:Color)
        WHERE toUpper(sub.hex) IN $source_colors

        RETURN
            sub.hex AS source_color,
            main.hex AS color,
            r.count AS count,
            r.likes AS likes
        """

        normalized_colors = [
            color.upper()
            for color in sub_colors
        ]

        with driver.session() as session:
            result = session.run(
                query,
                source_colors=normalized_colors,
            )

            return [
                {
                    "source_color": record["source_color"],
                    "color": record["color"],
                    "count": record["count"] or 0,
                    "likes": record["likes"] or 0,
                }
                for record in result
            ]
