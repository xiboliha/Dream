"""Setup script for initializing the application."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def setup_directories():
    """Create necessary directories."""
    base_dir = Path(__file__).parent.parent.parent

    directories = [
        base_dir / "data" / "database",
        base_dir / "data" / "cache",
        base_dir / "data" / "cache" / "wechat",
        base_dir / "data" / "logs",
        base_dir / "data" / "backups",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")


def setup_env_file():
    """Create .env file from example if not exists."""
    base_dir = Path(__file__).parent.parent.parent
    env_file = base_dir / ".env"
    env_example = base_dir / ".env.example"

    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print(f"Created .env file from .env.example")
        print("Please edit .env and add your API keys!")
    elif env_file.exists():
        print(".env file already exists")
    else:
        print("Warning: .env.example not found")


def setup_database():
    """Initialize the database."""
    from config.settings import settings
    from src.services.storage import init_database

    print(f"Initializing database: {settings.database_url}")
    init_database(settings.database_url, echo=False)
    print("Database initialized successfully!")


def main():
    """Run setup."""
    print("=" * 50)
    print("AI Girlfriend Agent Setup")
    print("=" * 50)

    print("\n1. Creating directories...")
    setup_directories()

    print("\n2. Setting up environment file...")
    setup_env_file()

    print("\n3. Initializing database...")
    try:
        setup_database()
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("You may need to install dependencies first: pip install -r requirements/base.txt")

    print("\n" + "=" * 50)
    print("Setup complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Edit .env file and add your API keys")
    print("2. Run: python src/main.py")
    print("3. Scan the QR code to login to WeChat")


if __name__ == "__main__":
    main()
