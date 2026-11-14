"""
Credenciais da base de dados de teste, partilhadas por test_load.py e test_queries.py.

Lidas do .env: TEST_DB_* se existirem, senão as mesmas DB_* do projeto.
A base de dados é sempre dw_ocupacao_tests, para nunca tocar nos dados reais.
"""

import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

HOST     = os.getenv("TEST_DB_HOST", os.getenv("DB_HOST", "localhost"))
PORT     = int(os.getenv("TEST_DB_PORT", os.getenv("DB_PORT", "3306")))
USER     = os.getenv("TEST_DB_USER", os.getenv("DB_USER", "root"))
PASSWORD = os.getenv("TEST_DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
DB_NAME  = "dw_ocupacao_tests"

# URL para o SQLAlchemy (escapa caracteres especiais na password)
TEST_DB_URL = URL.create(
    "mysql+pymysql",
    username=USER,
    password=PASSWORD,
    host=HOST,
    port=PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)
