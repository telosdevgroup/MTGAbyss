# AGENT OPERATIONAL SPECIFICATION & ARCHITECTURAL INVARIANTS
**System:** AvaScry Multi-Game Intelligence Network  
**Target Audience:** Autonomous AI Coding Agents & LLM Pair-Programmers  
**Doctrine:** High-Confidence Autonomous Execution • Memory-Mapped Runtime • Zero-Cloud Footprint

---

## 0. THE STRATEGIC PRIME DIRECTIVE (DISCORD-FIRST ECOSYSTEM)

* **The Core Objective:** The entire 5-site web network exists as an ultra-fast, high-utility acquisition funnel. **The #1 strategic metric of this codebase is growing AvaScry Discord Bot adoption and scaling the AvaScry Lounge Discord Community.**
* **The Distribution Flywheel:**
  1. Players discover AvaScry on the web (SEO, guides, card lookups).
  2. The site prompts them to add the AvaScry Bot to their Discord servers.
  3. Players use `/mtg`, `/dom`, `/swu`, `/necro`, `/mc` in Discord chats.
  4. In-chat responses link back to AvaScry web pages via `?utm_source=discord_bot`.
* **THE CARDINAL AGENT INVARIANT:**
  * **NEVER remove, hide, shrink, or deprioritize the Discord Bot CTA banner, footer links, or server invite buttons.**
  * Every major landing page, guide, and entity detail page MUST feature prominent call-to-actions to invite the bot and join the community.

---

## 1. HARDWARE & RUNTIME INVARIANTS (ZERO-CLOUD DOCTRINE)

* **Physical Compute:** Dedicated bare-metal workstation running Windows with **128 GB Physical RAM** and **4 TB NVMe SSD** (`KXG8AZN84T`).
* **Cloud Cost Constraint:** **$0.00 / month external compute or database bills.**
  * No AWS, GCP, Azure, or remote Redis/Memcached clusters.
  * Do NOT suggest adding external microservices, Docker containers, Redis nodes, or cloud queues.
  * All runtime acceleration, caching, and state management **MUST live in-process in Python RAM** or local MongoDB.
* **Network Ingress:** Encrypted **Cloudflare Tunnel** (`cloudflared` daemon) routing edge traffic directly to local FastAPI instance on `127.0.0.1:8004`.
* **Edge Acceleration:** Cloudflare **Smart Tiered Cache** absorbs repeat requests globally across 300+ data centers before traffic ever hits local fiber.
* **Edge Security:** Cloudflare WAF + Threat Intelligence automations swat malicious scanners and unauthorized scrapers at the DNS/Edge layer.

---

## 2. MULTI-TENANT DOMAIN DISPATCH MATRIX

FastAPI server (`app.py`) runs on `127.0.0.1:8004` and dispatches requests based on incoming HTTP `Host` headers:

| Domain / Host | Primary Router | Core Dataset / Scope | Tri-Surface Support |
| :--- | :--- | :--- | :--- |
| **`avascry.com`** / `mtg.avascry.com` | `mtgabyss.routers.pages_router` & `card_router` | Magic: The Gathering (808k+ printings, 340k+ art assets, vector embeddings) | HTML, `.md`, `.json`, RSS |
| **`dominion.avascry.com`** | `mtgabyss.dominion_router` | Dominion Kingdom Codex (819 cards, 1,078 versions, 16 expansions, 2E errata) | HTML, `.md`, `.json` |
| **`swu.avascry.com`** | `mtgabyss.swu_router` | Star Wars: Unlimited (4,871 cards, variants, comprehensive rules, rulings) | HTML, `.md`, `.json`, `.xml` |
| **`necromunda.avascry.com`** | `mtgabyss.routers.necromunda_router` | Necromunda: Underhive (355 weapons, 66 traits, 169 skills, equipment) | HTML, `.md`, `.json` |
| **`minecraft.avascry.com`** | `mtgabyss.routers.minecraft_router` | Minecraft Java 1.21.4 (1,385 items, 1,095 blocks, 149 entities, 1,558 recipes) | HTML, `.md`, `.json` |
| **Global Webhooks & Bots** | `mtgabyss.routers.discord_bot_router` | Multi-game Discord Slash Commands (`/mtg`, `/dom`, `/swu`, `/necro`, `/mc`) | Direct Interaction Webhook |

---

## 3. IN-MEMORY RUNTIME ARCHITECTURE (THE RAM TIER)

The database is the **System of Record**; process memory is the **Runtime Reality**.

Memory Manager: `mtgabyss.shared.cache`

### A. Full Page HTML Cache (`PAGE_CACHE`)
* **Type:** `Dict[str, str]` (Capacity: 100,000 pages, ~2–4 GB max footprint).
* **Scope:** Fully rendered, final HTML strings for Dominion, SWU, Necromunda, and Minecraft.
* **Key Patterns:**
  * Dominion: `dom:card:{slug}`
  * Star Wars Unlimited: `swu:card:{slug}`
  * Necromunda: `necro:weapon:{slug}`
  * Minecraft: `mc:item:{slug}`, `mc:block:{slug}`, `mc:entity:{slug}`, `mc:recipe:{slug}`
* **Invariant:** When present in `PAGE_CACHE`, the route MUST return immediately in `<1ms` with `X-Cache: HIT`, bypassing MongoDB queries and skipping Jinja2 template rendering entirely.
* **Cache Miss:** On first render, compute context, execute template, return `X-Cache: MISS`, and store decoded UTF-8 HTML via `set_page_cache(key, html)`.

### B. Object & Buffer Cache (`RAM_CACHE`)
* **Type:** `Dict[str, Any]` (Capacity: 200,000 objects, ~8–10 GB max footprint).
* **Scope:** Autocomplete index trees, raw printing lists, commander suggestions, and vector similarity buffers.
* **Eviction Policy:** Auto-flushes oldest 50% on Sunday nights or if process RSS hits the 48 GB soft-cap.

### C. The 808,000 MTG Image Prefix Hash Table
* Location: `mtgabyss.routers.image_router`
* Global: `IMAGE_PREFIX_MAP = {"normal": {}, "large": {}}`
* Pre-warmed at server startup in ~1.2 seconds across 808,602 local scan files.
* Resolves extensionless card slugs, multi-face cards, and art variants to disk paths in O(1) sub-microsecond time.

---

## 4. DATABASE REGISTRY (MONGODB LOCALHOST:27017)

All databases run locally on default port `27017` via `db_mongo.get_mongo_db()`:

* **`mtgabyss_allcards`**:
  * `cards`: Canonical oracle documents (names, slugs, colors, mana costs, legalities, oracle text).
  * `card_prints`: Specific set printings, collector numbers, artists, image URIs, rarities.
  * `rulings`: Official MTG comprehensive rulings keyed by `oracle_id`.
  * `mechanics`: Keywords, ability words, and reminder text glossary.
* **`avascry_dominion`**:
  * `cards`: Base cards with normalized names, types, and expansion tags.
  * `card_versions`: 1st vs 2nd edition variations, printed rules text, debt/potion/coin costs.
  * `expansions`: Set metadata and display names (pre-cached in RAM as `_DOMINION_EXP_MAP`).
  * `rulings`: Official Donald X. errata and forum rulings.
* **`avascry_swu`**:
  * `cards`: Star Wars: Unlimited cards, aspects, arenas, power/HP, costs, and traits.
  * `clarifications`: Official FFG rulings, questions, answers, and citation authorities.
  * `sets`: Expansion metadata (SOR, SHD, TWI, etc.).
* **`avascry_necromunda`**:
  * `weapons`: Armory entries (range short/long, acc, str, damage, AP, ammo checks, credit costs).
  * `traits`: Weapon traits (Rapid Fire, Blast, Versatile, Toxin) and rules text.
  * `houses`: Gang house affiliations (Goliath, Escher, Orlock, Van Saar, Cawdor, Delaque).
  * `skills`: Skill trees and campaign advancements.
  * `similar_weapons`: Precomputed cosine similarity tactical alternatives.
* **`avascry_minecraft`**:
  * `items`: Durability, stack sizes, item tags, crafting connections.
  * `blocks`: Hardness, blast resistance, tool harvest tier requirements, luminance.
  * `entities`: Health, category (hostile/passive), spawn dimensions, loot tables.
  * `recipes`: 3x3 crafting grid matrices, blast furnace, smoker, stonecutter derivations.
  * `palette_neighbors` & `similar_functional`: 4,096-dimensional visual texture and architectural pairings.

---

## 5. DISCORD BOT ARCHITECTURE & INTERACTION LIFECYCLE

* **Interaction Webhook Router:** `mtgabyss.routers.discord_bot_router`
* **Endpoint:** `POST /api/discord/interactions`
* **Signature Authentication:** Validated cryptographically via `nacl.signing.VerifyKey` with Ed25519 headers (`X-Signature-Ed25519`, `X-Signature-Timestamp`).

### Strict 3-Second Execution Law:
Discord interactions time out if not acknowledged within **3,000 milliseconds**.
1. When a command arrives (`/mtg`, `/dom`, `/swu`, `/necro`, `/mc`), extract parameters.
2. If the response contains an image attachment:
   * **Immediately return Type 5** (`DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE`).
   * Queue background task: `update_discord_original_interaction_with_attachment(...)`.
3. In the background worker:
   * Fetch image bytes using `fetch_image_bytes(url)` (must send legitimate browser `User-Agent` to avoid Scryfall 400 Bad Request).
   * **Format clean markdown text into message `content`.**
   * **Attach direct image as `files[0]` (`card.jpg` / `card.png`).**
   * **CLEAR `embeds: []` (MANDATORY).**
   * *CRITICAL INVARIANT:* Never place `attachment://card.jpg` inside rich embeds. Discord desktop and mobile clients suppress embedded attachments, leaving grey blank boxes. Direct message file attachments render 100% reliably.
4. **Outbound Traffic Attribution:**
   * All outbound links to AvaScry websites MUST pass through `with_discord_bot_utm(url)` to append `?utm_source=discord_bot`.
   * Never append UTM tags to CDN image URLs.

---

## 6. TRI-SURFACE PARITY DIRECTIVE

Every primary entity across all 5 subdomains must expose three canonical surfaces with zero data divergence:

1. **Web UI (`/card/{slug}`, `/weapon/{slug}`, `/item/{slug}`):**
   * Semantic HTML5, accessible Dark/Light mode, responsive layouts, CSS-driven UI.
2. **AI / LLM Markdown (`/card/{slug}.md`, `/weapon/{slug}.md`):**
   * Token-dense Markdown with YAML frontmatter, rules text, and direct cross-links. Cleanly consumable by AI search engines.
3. **API & Bot JSON (`/card/{slug}.json`, `/weapon/{slug}.json`):**
   * Deterministic, machine-readable JSON contracts with consistent casing and zero formatting noise.

---

## 7. UNIVERSAL NETWORK COMMONALITY & CONVERSION INVARIANTS

Across all 5 sites and their Jinja2 templates:
1. **The Universal Bottom CTA:**
   * Every major page footer features the prominent Discord Bot CTA banner with direct bot invite link (`/bot` or direct client ID) and Discord Lounge invite link (`https://discord.gg/TMpRYtsmrz`).
   * Do NOT remove this block during UI cleanups.
2. **Cross-Network Navigation:**
   * Header sub-nav links to the sister properties: MTG, Dominion, SWU, Necromunda, Minecraft.
3. **Dark / Light Mode Consistency:**
   * Pure CSS variable tokens (`--bg-primary`, `--text-primary`, `--accent`). Zero heavy JS UI libraries.

---

## 8. CODE MODIFICATION SAFETY INVARIANTS FOR AGENTS

1. **Context Discipline:**
   * Do not run broad repo-wide scans.
   * Target specific symbols, imports, and functions before inspecting files.
   * Files over 500 lines must be read in targeted slices.
2. **Planning Gate:**
   * Before executing non-trivial refactors, write an implementation plan and wait for confirmation.
3. **Destructive Shell Commands:**
   * NEVER execute destructive commands (`rm -rf`, disk format, mass drop) without explicit user confirmation.
4. **Testing Protocol:**
   * Run the narrowest relevant test first using Python TestClient or pytest (`tests/test_network_guides.py`, `scratch/test_page_cache.py`).
   * Do not run global test suites unless narrow unit verification passes.
5. **Handoff Contract:**
   * Every execution completion must report:
     - Changed files
     - What changed
     - Tests/commands run
     - Known issues
     - Next recommended step
   * Conclude milestones with: `⚡ In Gemini I Trust — Verified & Shipped 🚀💎`

---

## 9. THE PRIME + JITTER MATHEMATICAL DOCTRINE

Utility: `mtgabyss.shared.prime_jitter`

* **The Core Philosophy:** Nature and distributed systems abhor harmonic synchronization. Standard power-of-two progressions ($1, 2, 4, 8\dots$) and round-number loops cause constructive interference and lockstep thundering herds.
* **The Prime Ladder:**
  * All exponential-like backoffs, network retries, and sleep delays MUST traverse prime seeds:
    `[1.123, 2.317, 3.141, 5.303, 7.129, 11.311, 13.147, 17.321, 19.183, 23.327, 29.173, 31.379]`
  * Always apply continuous stochastic dispersion: `prime_jitter(base, jitter_pct=0.17)`.
* **Statistical Sampling ($N \ge 31$):**
  * When sampling or batching entities, default to prime counts that satisfy the **Central Limit Theorem ($N \ge 30$)**:
    `N = 31, 67, 127, 257, 509, 1021`.
  * Never use arbitrary round numbers like 10, 20, 50, or 100 when collecting statistical distributions.
* **Timeout Primes:** Default timeouts to prime values (e.g., $3.141\text{s}$, $7.13\text{s}$, $11.3\text{s}$).

---

## 10. NETWORK BLASTER & SITE BLASTER VERIFICATION GATEWAY

**Root Entrypoint:** `python network_blaster.py` (wraps `scripts/network_blaster.py`)  
**Site Blaster Suite:** `scripts/*_site_blaster.py`

The Blaster Suite is AvaScry's canonical release verification, cache pre-warming, and regression gate across all 5 properties and the Discord Bot.

### The Site Blaster Fleet
* **`scripts/site_blaster.py`**: MTG (AvaScry apex — `avascry.com` / `mtg.avascry.com`)
* **`scripts/dominion_site_blaster.py`**: Dominion Kingdom Codex (`dominion.avascry.com`)
* **`scripts/swu_site_blaster.py`**: Star Wars: Unlimited (`swu.avascry.com`)
* **`scripts/necromunda_site_blaster.py`**: Necromunda: Underhive (`necromunda.avascry.com` — `blaster9001`)
* **`scripts/minecraft_site_blaster.py`**: Minecraft Java Edition (`minecraft.avascry.com`)
* **`scripts/discord_bot_blaster.py`**: Discord Slash Command interactions (`/mtg`, `/dom`, `/swu`, `/necro`, `/mc`)

### Agent Execution Protocol
* **Targeted Site Check (Narrowest scope first):**
  When making changes to a single property router or template:
  ```powershell
  python scripts/network_blaster.py --site dominion --quick
  # Or run the site blaster directly:
  python scripts/necromunda_site_blaster.py --quick
  ```
* **Full Network Verification (Pre-Release Gate):**
  When performing global routing, cache layer, or multi-tenant middleware updates:
  ```powershell
  python network_blaster.py --quick
  ```
* **Deep Exhaustive Verification:**
  ```powershell
  python network_blaster.py --deep
  ```
* **JSON Machine-Readable Audit Output:**
  ```powershell
  python network_blaster.py --json
  ```

