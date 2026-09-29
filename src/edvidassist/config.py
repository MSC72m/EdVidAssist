import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

class Config(BaseModel):
    llm_model: str = "openai/gpt-4o"
    embedding_model: str = "openai/text-embedding-3-small"
    
    tts_provider: str = "openai"
    tts_voice: str = "alloy"
    tts_api_key: str | None = None
    
    pexels_api_key: str | None = None
    opensubtitles_api_key: str | None = None
    opensubtitles_username: str | None = None
    opensubtitles_password: str | None = None
    
    max_segment_duration: int = 300
    max_total_duration: int = 900
    transition_duration: float = 1.0
    
    output_dir: Path = Path("output")
    work_dir: Path = Path(".edvidassist_work")
    
    @classmethod
    def load(cls, config_path: str | None = None) -> "Config":
        load_dotenv()
        data = {}
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        
        for k in cls.model_fields.keys():
            env_val = os.getenv(f"EDVIDASSIST_{k.upper()}")
            if env_val is not None:
                data[k] = env_val
                
        return cls(**data)
