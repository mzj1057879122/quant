from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库配置
    dbHost: str = Field(default="127.0.0.1", alias="DB_HOST")
    dbPort: int = Field(default=3306, alias="DB_PORT")
    dbUser: str = Field(default="root", alias="DB_USER")
    dbPassword: str = Field(default="", alias="DB_PASSWORD")
    dbName: str = Field(default="quant", alias="DB_NAME")

    # Server酱推送配置
    serverChanKey: str = Field(default="", alias="SERVER_CHAN_KEY")

    # 日志配置
    logLevel: str = Field(default="INFO", alias="LOG_LEVEL")
    logFile: str = Field(default="logs/app.log", alias="LOG_FILE")

    @property
    def databaseUrl(self) -> str:
        encodedPassword = quote_plus(self.dbPassword)
        return (
            f"mysql+pymysql://{self.dbUser}:{encodedPassword}"
            f"@{self.dbHost}:{self.dbPort}/{self.dbName}"
            f"?charset=utf8mb4"
        )


settings = Settings()
