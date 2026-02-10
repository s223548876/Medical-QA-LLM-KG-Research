from __future__ import annotations

import os
from pydantic import BaseModel


class Settings(BaseModel):
    # For judge script compatibility / future shared config
    OPENAI_API_KEY: str = ""

    NEO4J_URI: str = "bolt://host.docker.internal:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    APP_API_KEY: str = ""

    FRONTEND_ORIGINS: list[str] = []

    @classmethod
    def from_env(cls) -> "Settings":
        origins_raw = os.getenv("FRONTEND_ORIGINS", "")
        origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
        return cls(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
            NEO4J_URI=os.getenv("NEO4J_URI", "bolt://host.docker.internal:7687"),
            NEO4J_USER=os.getenv("NEO4J_USER", "neo4j"),
            NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD", ""),
            OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            APP_API_KEY=os.getenv("APP_API_KEY", ""),
            FRONTEND_ORIGINS=origins,
        )


settings = Settings.from_env()
