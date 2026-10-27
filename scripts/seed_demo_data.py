import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.services.playlist_service import PlaylistService

def seed():
    app = create_app()
    with app.app_context():
        print("Seeding demo playlist data...")
        pl = PlaylistService.seed_demo_playlist(force=True)
        print(f"Successfully seeded '{pl.title}' with {pl.item_count} items.")

if __name__ == "__main__":
    seed()
