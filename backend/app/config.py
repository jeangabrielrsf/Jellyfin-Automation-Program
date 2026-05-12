"""Application configuration."""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="postgresql://jfa_user:jfa_password@localhost:5432/jellyfin_automation")
    
    # TMDB
    tmdb_api_key: str = Field(default="")
    
    # qBittorrent
    qbittorrent_host: str = Field(default="http://localhost:8080")
    qbittorrent_username: str = Field(default="admin")
    qbittorrent_password: str = Field(default="adminadmin")
    
    # Jackett
    jackett_url: str = Field(default="http://localhost:9117")
    jackett_api_key: str = Field(default="")
    jackett_timeout: int = Field(default=120)
    
    # Jellyfin
    jellyfin_url: str = Field(default="http://localhost:8096")
    jellyfin_api_key: str = Field(default="")
    
    # App
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="dev-secret-key")
    
    # Library paths
    movies_path: str = Field(default="D:\\Filmes")
    series_path: str = Field(default="D:\\Séries")
    animes_path: str = Field(default="D:\\Animes")
    
    # Default preferences
    default_quality: str = Field(default="1080p")
    default_language: str = Field(default="legendado")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
