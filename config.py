import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self) -> None:
        self.bot_token: str = self._require("BOT_TOKEN")
        self.openrouter_api_key: str = self._require("OPENROUTER_API_KEY")
        self.proxy: str | None = os.getenv("PROXY") or None
        self.free_generations: int = int(os.getenv("FREE_GENERATIONS", "2"))
        self.db_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://t_bot:t_bot_secure_2026@localhost:5432/t_bot_db",
        )
        self.gen_cost: int = int(os.getenv("GEN_COST", "2500"))  # в копейках

    @staticmethod
    def _require(name: str) -> str:
        value = os.getenv(name)
        if not value or value.startswith("YOUR_"):
            raise ValueError(
                f"{name} не задан. Скопируйте .env.example в .env и укажите реальное значение."
            )
        return value


config = Config()
