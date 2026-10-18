from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Resolve base backend directory from this file's location
# connection.py is in backend/app/database/ -> parent.parent.parent is backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DOTENV_PATH = BACKEND_DIR / ".env"
DEFAULT_DB_FILE = BACKEND_DIR / "life_os.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

class Settings(BaseSettings):
    APP_NAME: str = "LIFE_OS"
    ENV: str = "development"
    DATABASE_URL: str = DEFAULT_DB_URL
    TELEGRAM_BOT_TOKEN: str = "your_bot_token_here"
    TELEGRAM_OWNER_ID: str = "your_telegram_id_here"
    MINIMAX_API_KEY: str = "your_minimax_api_key_here"
    MODEL_NAME: str = "abab6.5g-chat"
    TIMEZONE: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(env_file=DOTENV_PATH, env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure SQLite file paths are always absolute to BACKEND_DIR
if settings.DATABASE_URL.startswith("sqlite:///") and not settings.DATABASE_URL.startswith("sqlite:///:memory:"):
    raw_path_str = settings.DATABASE_URL[len("sqlite:///"):]
    raw_path = Path(raw_path_str)
    if not raw_path.is_absolute():
        resolved_db = (BACKEND_DIR / raw_path).resolve()
        settings.DATABASE_URL = f"sqlite:///{resolved_db.as_posix()}"

# Setup SQLite connect args for concurrent write locks
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Database session generator dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
