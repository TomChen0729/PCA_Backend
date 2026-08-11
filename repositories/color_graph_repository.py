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
    def get_matches_by_main_colors(main_colors: list[str]):
        """
        根據多個相近主色，一次查詢所有搭配色。
        """
        driver = Neo4jConnection.get_driver()

        query = """
        MATCH (main:Color)-[r:MAIN_TO_SUB]->(sub:Color)
        WHERE toUpper(main.hex) IN $main_colors

        RETURN
            main.hex AS main_color,
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
                main_colors=normalized_colors,
            )

            return [
                {
                    "main_color": record["main_color"],
                    "color": record["color"],
                    "count": record["count"] or 0,
                    "likes": record["likes"] or 0,
                }
                for record in result
            ]