Day 7 — Food & Grocery Ordering Voice Agent (README)

🎙️ **Day 7: Food & Grocery Ordering Voice Agent**
Build a voice-first shopping assistant that adds items to a cart, supports simple “ingredients for X” requests, and saves the final order to JSON.

---

What this project does (MVP)

* Loads a small **catalog** (JSON).
* Lets a user add/remove/update items to a **cart** via natural voice.
* Supports simple “ingredients for X” mapping (recipes → multiple items).
* Shows the cart on request.
* When the user says “That’s all / Place my order / I’m done”, agent:

  * Confirms the final cart and total,
  * Saves an order JSON to `shared-data/orders/` (one file per order),
  * Clears the session cart.

---

Files & paths (important)

* `backend/src/agent.py` — main agent code (voice pipeline + tools).
* `shared-data/day7_catalog.json` — **catalog** (you must create this).
* `shared-data/orders/` — generated order files (auto-created).
* Example per-session state: `ctx.userdata["catalog"]`, `ctx.userdata["cart"]`.

---

Example files

### Example `shared-data/day7_catalog.json`

Create this file with at least 10–20 items. Example entry format:

```json
[
  {
    "id": "bread_ww",
    "name": "Whole Wheat Bread",
    "category": "Groceries",
    "price": 45,
    "tags": ["bread", "vegan"]
  },
  {
    "id": "peanut_butter",
    "name": "Peanut Butter (Creamy) 350g",
    "category": "Groceries",
    "price": 220,
    "tags": ["spread", "snack"]
  },
  {
    "id": "milk_1l",
    "name": "Milk 1L",
    "category": "Groceries",
    "price": 56,
    "tags": ["dairy"]
  },
  {
    "id": "pasta_500g",
    "name": "Pasta 500g",
    "category": "Groceries",
    "price": 120,
    "tags": ["pasta", "italian"]
  },
  {
    "id": "pasta_sauce",
    "name": "Pasta Sauce 400g",
    "category": "Groceries",
    "price": 150,
    "tags": ["sauce"]
  }
  // ...add more items
]
```

Example `shared-data/orders/current-order.json` (sample)

(This is the same sample I provided previously; orders are saved with timestamps in filenames by default.)

```json
{
  "customer_name": "Rahul Singh",
  "address": "Bangalore, Karnataka",
  "items": [
    { "id": "bread_ww", "name": "Whole Wheat Bread", "quantity": 2, "price": 45 },
    { "id": "peanut_butter", "name": "Peanut Butter (Creamy)", "quantity": 1, "price": 220 },
    { "id": "milk_1l", "name": "Milk 1L", "quantity": 1, "price": 56 }
  ],
  "total": 366,
  "timestamp": "2025-02-15T17:42:18.232Z"
}
```

---

Code changes / where to put things (short guide)

1. Catalog load & session userdata

* `load_catalog()` should read `shared-data/day7_catalog.json`.
* In `entrypoint()` load `catalog = load_catalog()` and pass into the realtime session via `AgentSession(..., userdata={"catalog": catalog, "cart": []}, ...)`. This ensures every session has access to the catalog and an empty cart.

2. Tools (function_tool)

Add these `@function_tool()` methods inside your `Assistant` class so the LLM can call them reliably:

* `add_to_cart(ctx: RunContext, item_id: str, quantity: int = 1, notes: str | None = None) -> str`
* `add_recipe(ctx: RunContext, recipe_name: str) -> str`
* `remove_from_cart(ctx: RunContext, item_id: str) -> str`
* `list_cart(ctx: RunContext) -> str`
* `place_order(ctx: RunContext, customer_name: str | None = None, address: str | None = None) -> str`

Place all these tool functions in `Assistant` (they already exist in the code you showed — keep them there).

3. A helper to resolve user item text → item id

* A `resolve_item_id(catalog, user_text)` helper helps map free-form item mentions to catalog IDs (exact match then partial / tag search).

4. Recipes mapping

* Keep a small `RECIPES` dict for “ingredients for X” that maps dish names to list of item IDs.

5. Saving orders

* `save_order(order: dict) -> Path` — create a timestamped file under `shared-data/orders/`.

6. Session state usage

* Use `ctx.userdata["cart"]` and `ctx.userdata["catalog"]` for each session. Prefer passing `userdata` to `AgentSession` and not attempting to write to `JobContext` (use `ctx.proc.userdata` only for process-global userdata; session-level per-call data belongs in `session`/`ctx.userdata`).

---

Suggested conversation flow (agent behavior)

* Greet and say what you can do (list categories or sample items).
* If user says “Add X”:

  * Resolve `X` → item id (or ask for clarifying question if ambiguous).
  * Call `add_to_cart`.
  * Confirm: “Added 2 × Whole Wheat Bread to your cart.”
* If user says “I need ingredients for peanut butter sandwich”:

  * Call `add_recipe("peanut butter sandwich")`
  * Confirm what was added.
* If user asks “What’s in my cart?”:

  * Call `list_cart()` and speak the reply (line breaks ok for debug; TTS will speak it).
* If user says “Remove bread” or “Remove item bread_ww”:

  * Resolve and call `remove_from_cart`.
* If user says “Place my order / That’s all”:

  * Ask for optional `customer_name` and `address` if missing.
  * Call `place_order(...)` — returns saved filename and total.
  * Respond: “Order placed — saved as order-20250... Total ₹xxx. Thank you!”

---

How to test locally

1. Ensure `shared-data/day7_catalog.json` exists and is valid JSON.
2. Start the agent worker:

   ```bash
   uv run python src/agent.py dev
   ```
3. Use the provided LiveKit web UI for the project to join the agent room and speak your commands, or call the agent with test messages if you have a local test harness.
4. Check `shared-data/orders/` for new `order-*.json` files after placing orders.

----

MVP checklist (Day 7)

* [ ] `day7_catalog.json` exists with 10+ items.
* [ ] Agent loads catalog into session `userdata`.
* [ ] `add_to_cart`, `add_recipe`, `remove_from_cart`, `list_cart`, `place_order` tools work and are decorated with `@function_tool`.
* [ ] Agent confirms cart changes by voice/text.
* [ ] When user says “place order”, order JSON file is saved to `shared-data/orders/`.
* [ ] Cart cleared after order placement.


🚀 Day 7 of #10DaysofAIVoiceAgents — I Built a Food & Grocery Ordering Voice Agent!
🎯 My agent can now: ✔ add items to a cart, supports simple “ingredients for X” requests, and saves the final order to JSON!!


#MurfAI #VoiceAI #LiveKit #Gemini #AIAgents #FraudDetection #BankingAI #BuildInPublic #TTS #STT #GenAI
