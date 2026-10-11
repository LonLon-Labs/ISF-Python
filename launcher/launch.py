import sys


def launch_game(paths):
    """Start the port, pointing it at the generated files in the app data folder."""
    root = str(paths.repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from ispy.main import main as game_main
    return game_main([
        "--exports", str(paths.exports),
        "--data", str(paths.data),
        "--game", str(paths.game),
    ])
