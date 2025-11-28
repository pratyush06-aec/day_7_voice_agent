import logging
import json
from pathlib import Path
from livekit.agents import function_tool, RunContext

import os

from datetime import datetime
from typing import List, Dict

from pydantic import BaseModel
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    # function_tool,
    # RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# ---------- Day 7: catalog, cart, orders ----------
CATALOG_PATH = Path("shared-data/day7_catalog.json")
ORDERS_DIR = Path("shared-data/orders")
ORDERS_DIR.mkdir(parents=True, exist_ok=True)

def load_catalog() -> List[Dict]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Catalog not found at {CATALOG_PATH}")
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def find_catalog_item_by_id(catalog: List[Dict], item_id: str) -> Dict | None:
    for it in catalog:
        if it["id"] == item_id:
            return it
    return None

def find_catalog_items_by_name(catalog: List[Dict], name_query: str) -> List[Dict]:
    q = name_query.lower()
    return [it for it in catalog if q in it["name"].lower() or q in " ".join(it.get("tags", [])).lower()]

def save_order(order: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = ORDERS_DIR / f"order-{ts}.json"
    with filename.open("w", encoding="utf-8") as f:
        json.dump(order, f, indent=2, ensure_ascii=False)
    return filename

# Simple recipes mapping for "ingredients for X"
RECIPES = {
    "peanut butter sandwich": ["bread_ww", "peanut_butter"],
    "pasta for two": ["pasta_500g", "pasta_sauce"],
    "basic sandwich": ["bread_ww", "eggs_12", "peanut_butter"]
}

# Pydantic models (optional but helpful)
class CartItem(BaseModel):
    item_id: str
    quantity: int = 1
    notes: str | None = None

class Order(BaseModel):
    customer_name: str | None = None
    address: str | None = None
    items: List[Dict]
    total: float
    timestamp: str


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting including emojis, asterisks, or other weird symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

    @function_tool()
    async def add_to_cart(self, ctx: RunContext, item_id: str, quantity: int = 1, notes: str | None = None) -> str:
        catalog = ctx.userdata.get("catalog", [])
        item = find_catalog_item_by_id(catalog, item_id)
        if not item:
            return f"Item {item_id} not found in catalog."
        cart = ctx.userdata.setdefault("cart", [])
        # merge if exists
        for ci in cart:
            if ci["item_id"] == item_id:
                ci["quantity"] += max(1, quantity)
                if notes:
                    ci["notes"] = (ci.get("notes") or "") + " " + notes
                return f"Updated {item['name']} quantity to {ci['quantity']}."
        cart.append({"item_id": item_id, "quantity": max(1, quantity), "notes": notes or ""})
        return f"Added {quantity} x {item['name']} to your cart."

    @function_tool()
    async def add_recipe(self, ctx: RunContext, recipe_name: str) -> str:
        catalog = ctx.userdata.get("catalog", [])
        recipe = RECIPES.get(recipe_name.lower())
        if not recipe:
            return f"Sorry, I don't know the recipe {recipe_name}."
        added = []
        for item_id in recipe:
            item = find_catalog_item_by_id(catalog, item_id)
            if item:
                await self.add_to_cart(ctx, item_id, quantity=1)
                added.append(item["name"])
        return "Added: " + ", ".join(added)

    @function_tool()
    async def remove_from_cart(self, ctx: RunContext, item_id: str) -> str:
        cart = ctx.userdata.setdefault("cart", [])
        for i, ci in enumerate(cart):
            if ci["item_id"] == item_id:
                cart.pop(i)
                return f"Removed item {item_id} from cart."
        return "Item not found in cart."

    @function_tool()
    async def list_cart(self, ctx: RunContext) -> str:
        catalog = ctx.userdata.get("catalog", [])
        cart = ctx.userdata.get("cart", [])
        if not cart:
            return "Your cart is empty."
        lines = []
        total = 0.0
        for ci in cart:
            it = find_catalog_item_by_id(catalog, ci["item_id"])
            name = it["name"] if it else ci["item_id"]
            price = it.get("price", 0) if it else 0
            qty = ci.get("quantity", 1)
            lines.append(f"{qty} x {name} — ₹{price * qty}")
            total += price * qty
        lines.append(f"Total: ₹{total}")
        return "\n".join(lines)

    @function_tool()
    async def place_order(self, ctx: RunContext, customer_name: str | None = None, address: str | None = None) -> str:
        catalog = ctx.userdata.get("catalog", [])
        cart = ctx.userdata.get("cart", [])
        if not cart:
            return "Your cart is empty — cannot place an order."
        items = []
        total = 0.0
        for ci in cart:
            it = find_catalog_item_by_id(catalog, ci["item_id"])
            price = it.get("price", 0) if it else 0
            items.append({"id": ci["item_id"], "name": it.get("name",""), "quantity": ci.get("quantity",1), "price": price})
            total += price * ci.get("quantity",1)
        order = {
            "customer_name": customer_name,
            "address": address,
            "items": items,
            "total": total,
            "timestamp": datetime.now().isoformat()
        }
        path = save_order(order)
        # clear cart after placing
        ctx.userdata["cart"] = []
        return f"Order placed and saved to {path.name}. Total: ₹{total}"
    
    def resolve_item_id(catalog: List[Dict], user_text: str) -> str | None:
        # exact name match
        for it in catalog:
            if user_text.lower() == it["name"].lower():
                return it["id"]
        # partial match
        results = find_catalog_items_by_name(catalog, user_text)
        return results[0]["id"] if results else None



    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here

    catalog = load_catalog()

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
    stt=deepgram.STT(model="nova-3"),
    llm=google.LLM(model="gemini-2.5-flash"),
    tts=murf.TTS(
    api_key=os.getenv("MURF_API_KEY"),
    model="FALCON",
    voice="en-US-matthew",
    style="Conversation",
    tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
    text_pacing=True
),
    turn_detection=MultilingualModel(),
    vad=ctx.proc.userdata["vad"],
    preemptive_generation=True,

    userdata={
        "catalog": catalog,
        "cart": []
    }
)

    ctx.proc.userdata.setdefault("catalog", catalog)
    ctx.proc.userdata.setdefault("cart", [])


    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
