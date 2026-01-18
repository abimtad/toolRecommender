from bioblend.galaxy import GalaxyInstance
from src.config.env import GALAXY_API_KEY, GALAXY_URL


gi = GalaxyInstance(url=GALAXY_URL, key=GALAXY_API_KEY)


def fetch_galaxy_tools():
    """Fetch all tools from Galaxy"""
    print("Fetching tools from Galaxy...")
    tools = gi.tools.get_tools()
    print(f"Found {len(tools)} tools")
    print(f"Found: ", tools[:5])

    return tools


if __name__ == "__main__":
    fetch_galaxy_tools()
