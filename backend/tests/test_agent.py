# tests/test_tools.py
from pathlib import Path
from src.agent import load_catalog, Assistant
from livekit.agents import RunContext

catalog = load_catalog()
print("catalog loaded:", len(catalog))

# You can't fully instantiate RunContext easily; simpler: simulate add_to_cart logic:
from src.agent import find_catalog_item_by_id
item = find_catalog_item_by_id(catalog, "peanut_butter")
print(item)
