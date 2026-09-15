import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


# ============================================================
# PCA_Backend 根目錄
# config/neo4j.py
#       ↑
# parents[1] = PCA_Backend
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

ENV_PATH = BASE_DIR / ".env"


# ============================================================
# 載入 .env
# ============================================================

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)


class Neo4jConnection:

    _driver = None

    @classmethod
    def get_driver(cls):

        if cls._driver is None:

            uri = os.getenv("NEO4J_URI")

            username = (
                os.getenv("NEO4J_USERNAME")
                or os.getenv("NEO4J_USER")
            )

            password = os.getenv(
                "NEO4J_PASSWORD"
            )

            # --------------------------------------------
            # 環境變數檢查
            # --------------------------------------------

            if not uri:
                raise RuntimeError(
                    f"缺少 NEO4J_URI\n"
                    f".env path: {ENV_PATH}"
                )

            if not username:
                raise RuntimeError(
                    "缺少 "
                    "NEO4J_USERNAME / NEO4J_USER"
                )

            if not password:
                raise RuntimeError(
                    "缺少 NEO4J_PASSWORD"
                )

            # --------------------------------------------
            # 建立 Aura Driver
            # --------------------------------------------

            cls._driver = (
                GraphDatabase.driver(
                    uri,
                    auth=(
                        username,
                        password,
                    ),
                )
            )

        return cls._driver

    @classmethod
    def get_session(cls):

        driver = cls.get_driver()

        database = os.getenv(
            "NEO4J_DATABASE"
        )

        if database:

            return driver.session(
                database=database
            )

        return driver.session()

    @classmethod
    def test_connection(cls):

        driver = cls.get_driver()

        driver.verify_connectivity()

        with cls.get_session() as session:

            record = session.run(
                "RETURN 1 AS test"
            ).single()

            if not record:
                return False

            return (
                record["test"] == 1
            )

    @classmethod
    def close(cls):

        if cls._driver is not None:

            cls._driver.close()

            cls._driver = None