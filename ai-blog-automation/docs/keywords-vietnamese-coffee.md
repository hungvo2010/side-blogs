# Keyword research — Vietnamese coffee cluster (dripper.top)

Data: Google Trends via pytrends, geo=US, 2026-09-20. Raw log: `/tmp/coffee_vn_kw.log`.
Script: `~/.hermes/scripts/coffee_vn_kw.py --geo US` (side-blogs venv). vol = estimated Trends volume, diff = 0–100 (lower = easier).

## Seed metrics

- **vietnamese coffee** — vol=6400 · diff=36 🟡 (best vol/diff ratio of the cluster)
- **vietnamese iced coffee** — vol=5900 · diff=41 🟡
- **egg coffee** — vol=5400 · diff=46 🟡 (already published)
- **phin filter** — vol=4500 · diff=55 🔴
- **coconut coffee** — vol=3500 · diff=65 🔴
- **cà phê muối** — vol=500 · diff=90 🔴 (SERP is VN-language only)

## TOP / RISING (real Trends data)

**vietnamese coffee**
- TOP: vietnamese coffee near me · coffee near me · vietnamese iced coffee · best vietnamese coffee · what is vietnamese coffee · vietnamese coffee caffeine · vietnamese cafe · vietnamese coffee recipe · how to make vietnamese coffee · vietnamese egg coffee · vietnamese instant coffee · vietnamese coffee shop · vietnamese food · vietnamese coffee calories · caffeine in vietnamese coffee · condensed milk · vietnamese coffee beans · starbucks vietnamese coffee · thai coffee
- RISING: yoju hard vietnamese coffee · hard vietnamese coffee · vietnamese coffee brownies · 85 degree bakery · lees vietnamese coffee · lees coffee · best vietnamese coffee brand · vietnamese coffee brand · vietnamese coffee ice cream · vietnamese coffee caffeine content · whole foods vietnamese coffee · vietnamese coffee concentrate · best instant coffee · g7 vietnamese coffee

**vietnamese iced coffee**
- TOP: vietnamese iced coffee near me · what is vietnamese iced coffee · vietnamese iced coffee calories · vietnamese iced coffee recipe
- RISING: what is vietnamese iced coffee

**egg coffee**
- TOP: what is egg coffee · egg coffee near me · egg coffee recipe · egg coffee italian · vietnamese coffee · vietnamese egg coffee · how to make egg coffee · italian egg coffee recipe
- RISING: italian egg coffee recipe · egg coffee italian

**coconut coffee**
- TOP: coconut coffee creamer · coconut coffee recipe · starbucks coconut coffee · coconut coffee syrup · coconut coffee near me · toasted coconut coffee · ogx coconut coffee
- RISING: toasted coconut coffee · starbucks coconut coffee

**cà phê muối** — TOP: cà phê muối starbucks · công thức cà phê muối starbucks · cà phê muối chú long (VN-language SERP)

**phin filter** — no related queries returned (narrow/product term)

## Autocomplete (Google suggest, en-US)
- vietnamese coffee → Vietnamese iced coffee · Vietnamese Coffee Co · Phin filter
- vietnamese iced coffee → Vietnamese coconut coffee
- egg coffee → Vietnamese egg coffee
- coconut coffee → Vietnamese coconut coffee · Coconut coffee creamer
- condensed milk coffee → Coffee with condensed milk · Condensed milk coffee cake
- vietnamese coffee beans → Vietnamese Arabica Coffee Beans · Trung Nguyen Legend Espresso Success
- trung nguyen coffee → Trung Nguyên · Trung Nguyen Coffee Village · Trung Nguyen G7 3-in-1
- phin filter → Trung Nguyen Coffee Phin Filter · Vietnamesischer Kaffeefilter Edelstahl
- vietnamese coffee brands → Thai My Phuong · Vietnamese Coffee Omakase Experience in HCMC
- cà phê muối → Salted coffee · Ong Bau Instant Salted Coffee

## Existing coverage on dripper.top (38 published)
Covered: Vietnamese coffee culture · egg coffee (Hanoi) · phin troubleshooting · condensed-milk why · Vietnamese cold brew · cà phê vợt (cloth filter) · Vietnamese food culture · Hanoi 36 streets.
Not covered: cà phê sữa đá / iced-coffee recipe · caffeine & calories numbers · coconut coffee · salted coffee · brand/bean buying guide · instant (G7) · coffee ice cream · brownies.

## Recommended next articles (by opportunity)
1. **Vietnamese coffee caffeine (+ calories)** — rides vol=6400/diff=36; unanswered queries `vietnamese coffee caffeine`, `caffeine in vietnamese coffee`, `vietnamese coffee calories`, `vietnamese coffee caffeine content` (rising). Pure info intent, easy to source from USDA/brand labels.
2. **Cà phê sữa đá / Vietnamese iced coffee recipe** — vol=5900/diff=41; `vietnamese iced coffee recipe` + `what is vietnamese iced coffee` (rising) + `vietnamese iced coffee calories`. No dedicated post (cold brew one is different).
3. **Best Vietnamese coffee brands & beans 2026 (buying guide)** — commercial intent, monetizable: `best vietnamese coffee brand` + `vietnamese coffee brand` (rising), `g7 vietnamese coffee` (rising), `vietnamese coffee concentrate` (rising), `vietnamese coffee beans`, `whole foods vietnamese coffee`, `vietnamese instant coffee`.
4. **Toasted coconut coffee** (rising long-tail under coconut coffee, diff of parent is 65 → target the long-tail) — or Vietnamese coconut coffee recipe.
5. **"Hard" Vietnamese coffee (RTD/canned)** — rising `hard vietnamese coffee` + `yoju hard vietnamese coffee`; needs verification of what the product is before writing (trend-jacking, time-sensitive).
6. **Italian egg coffee** — distinct SERP (`italian egg coffee recipe` rising, TOP under egg coffee) — separate post from Hanoi egg coffee.

## Caveats
- RISING lists carry generic noise (e.g. `cbd gummies`, `diet plan for teens`, `85 degree bakery`) — Google serves broad related queries on small-volume seeds. Only treat coffee-specific items as signal.
- `cà phê muối` diff=90 comes from a VN-language SERP; US English demand for "salted coffee" is thin — low priority for an English blog.
- `near me` / local queries are not addressable by content.
- pytrends burst-throttle: `phin filter` returned an empty related-queries frame — narrow term, not a failure to fix.
