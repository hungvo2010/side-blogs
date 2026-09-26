#!/usr/bin/env python3
"""Generate the site's static pages in the blog's own design.

Pages: about, contributors, contact, newsletter, pay-it-forward, sustainability,
privacy + a real 404.html (so an unknown path returns the 404 page with a 404
status instead of Cloudflare Pages' fallback to index.html — the "soft 404").

Branding, tokens and the footer come from `publish.py` (SITE_CSS / STATIC_PAGES /
footer_cols_html) so these pages can never drift from the blog's look or link to
a page nobody generates.

Run AFTER a build (publish.py writes public/, this adds the static pages to it):
    set -a; . ./.env; set +a
    SITE_NAME="The Daily Brew" SITE_URL="https://dripper.top" \
        PYTHONPATH=src .venv/bin/python scripts/gen_pages.py

Env:
    SITE_NAME / SITE_URL / SITE_AUTHOR / SITE_DESCRIPTION  (via .env)
    CONTACT_EMAIL      — public contact address (default hello@dripper.top)
    NEWSLETTER_ACTION  — provider form action URL; when empty the newsletter page
                         explains the list is not open yet and offers RSS instead
                         (never render a form that silently drops addresses)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from string import Template

SCRIPTS = Path(__file__).resolve().parent
BASE = SCRIPTS.parent                      # ai-blog-automation/
PUBLIC = BASE.parent / "public"            # side-blogs/public
CONTENT = BASE / "content"
sys.path.insert(0, str(SCRIPTS))

try:  # make `python scripts/gen_pages.py` behave like the pipeline does
    from dotenv import load_dotenv

    load_dotenv(BASE / ".env")
except Exception:  # noqa: BLE001
    pass

from publish import (  # noqa: E402  (fails loudly if the shared CSS moved — good)
    DEFAULTS,
    FEATURED_EXTERNAL,
    LAYOUT_CSS,
    SITE_CSS,
    STATIC_PAGES,
    footer_cols_html,
    slugify,
)

SITE = DEFAULTS["site_name"]
SITE_URL = DEFAULTS["site_url"].rstrip("/")
AUTHOR = DEFAULTS["author"]
DESCRIPTION = DEFAULTS["description"]
LANG = DEFAULTS["lang"]
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "hello@dripper.top")
NEWSLETTER_ACTION = os.getenv("NEWSLETTER_ACTION", "")

SHELL = Template(
    """<!DOCTYPE html>
<html lang="$lang">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>$title — $site</title>
<meta name="description" content="$desc">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="canonical" href="$canonical">
<meta property="og:title" content="$title — $site">
<meta property="og:description" content="$desc">
<meta property="og:type" content="website">
<meta property="og:url" content="$canonical">
<meta property="og:site_name" content="$site">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="$site RSS" href="/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>$layout_css</style>
<style>$site_css</style>
<style>
  .page{{max-width:780px;margin:34px auto 60px;padding:0 var(--gut)}}
  .page h1{{font-family:var(--serif);font-weight:700;font-size:clamp(1.8rem,1.2rem + 2.4vw,2.5rem);line-height:1.1;letter-spacing:-.01em;margin:0 0 12px}}
  .page .lede{{font-size:clamp(1rem,.4vw + .95rem,1.12rem);color:var(--muted);margin:0 0 26px}}
  .page h2{{font-family:var(--serif);font-weight:600;font-size:1.35rem;margin:34px 0 10px}}
  .page h3{{font-family:var(--serif);font-weight:600;font-size:1.1rem;margin:22px 0 6px}}
  .page p,.page li{{line-height:1.75}}
  .page ul,.page ol{{padding-left:22px}}
  .page a{{text-decoration:underline;text-underline-offset:2px}}
  .card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin:18px 0}}
  .card h3{{margin-top:0}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:18px 0}}
  .cta{{display:inline-flex;align-items:center;min-height:46px;padding:0 22px;border-radius:999px;background:var(--accent);color:#fff;font-weight:600;text-decoration:none;font-size:.92rem}}
  .cta:hover{{background:#7d5223}}
  .muted{{color:var(--muted)}}
  .who{{display:flex;gap:14px;align-items:center}}
  .who img{{width:56px;height:56px;border-radius:50%;object-fit:cover;border:2px solid var(--accent-soft)}}
  .form{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 6px}}
  .form input{{flex:1;min-width:220px;min-height:46px;padding:0 14px;border:1px solid var(--line);border-radius:10px;background:#fff;font-family:inherit;font-size:.95rem}}
  .form button{{min-height:46px;padding:0 20px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;font-family:inherit;cursor:pointer}}
  .form button:hover{{background:#7d5223}}
  .kicker{{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}}
  .back{{margin-top:30px;font-size:.9rem}}
</style>
</head>
<body>
<nav><div class="inner">
    <a class="brand" href="/">$site</a>
    <div class="nav-links"><a href="/">Home</a><a href="/sitemap.xml">Archive</a><a href="/rss.xml">RSS</a></div>
</div></nav>
<main class="page">
$body
</main>
<footer><p>&copy; 2026 $site.</p>
<div class="cols">$footer_cols</div>
</footer>
</body>
</html>
"""
)


def shell(slug: str, title: str, desc: str, body: str) -> str:
    return SHELL.substitute(
        lang=LANG,
        title=title,
        desc=desc.replace('"', "&quot;"),
        canonical=f"{SITE_URL}/{slug}/",
        site=SITE,
        layout_css=LAYOUT_CSS,
        site_css=SITE_CSS,
        body=body,
        footer_cols=footer_cols_html(),
    )


# ---------------------------------------------------------------------------
# Contributors page data — read the real content/, never invent people
# ---------------------------------------------------------------------------
def contributors() -> list[dict]:
    people: dict[str, dict] = {}
    seen_slugs: set[str] = set()
    for md in sorted(CONTENT.glob("*.md")):
        head = md.read_text(encoding="utf-8", errors="ignore")[:1200]
        m = re.match(r"^---\s*\n(.*?)\n---", head, re.S)
        fields = {}
        if m:
            for line in m.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fields[k.strip()] = v.strip().strip('"').strip("'")
        if fields.get("author", "").strip().strip("'\"") == "" or fields.get("title", "").startswith("["):
            continue
        # mirror the build's slug de-duplication, otherwise a stray duplicate
        # content file (e.g. x.md) inflates the guide count on this page
        slug = fields.get("slug") or slugify(fields.get("title", ""))
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        name = fields.get("author", AUTHOR).strip().strip("'\"") or AUTHOR
        date = fields.get("date", "")[:10]
        row = people.setdefault(name, {"name": name, "posts": 0, "first": date, "last": date})
        row["posts"] += 1
        if date:
            row["first"] = min(row["first"] or date, date)
            row["last"] = max(row["last"] or date, date)
    return sorted(people.values(), key=lambda r: (-r["posts"], r["name"]))


# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------
def page_about() -> str:
    return f"""<p class="kicker">About</p>
<h1>About {SITE}</h1>
<p class="lede">{DESCRIPTION}</p>

<h2>What this site is</h2>
<p>{SITE} is a working notebook for brewing coffee at home. Every guide starts from a
question a real kitchen raises — <em>why is my cold brew bitter, how much caffeine is actually in a
phin cup, is the $40 grinder worth it</em> — and ends with numbers you can copy: ratios, grind
settings, temperatures, timings.</p>
<p>Alongside the brewing guides we cover Vietnamese coffee properly, which we think deserves better
than a paragraph in someone else's listicle: cà phê sữa đá, the phin, cà phê vợt, egg coffee, and
the robusta-first growing culture behind them.</p>

<h2>How the guides are made</h2>
<ul>
  <li><strong>Research first.</strong> Roaster and producer documentation, green-coffee trade data,
  and published research where it exists — e.g. the
  <a href="{FEATURED_EXTERNAL[0]}" target="_blank" rel="noopener">{FEATURED_EXTERNAL[1]}</a> and
  <a href="https://worldcoffeeresearch.org/" target="_blank" rel="noopener">World Coffee Research</a>.</li>
  <li><strong>Then tested at home.</strong> Ratios, grind sizes and timings are brewed on ordinary
  equipment — a moka pot, a pour-over dripper, a phin, a French press — not a lab bench.</li>
  <li><strong>Drafted with software, edited by a human.</strong> We are upfront about this: drafts are
  produced with AI assistance and then reviewed, corrected and reworked before publishing. Claims
  that cannot be verified are cut rather than softened.</li>
  <li><strong>Corrections are welcome.</strong> If a number is wrong, tell us — the
  <a href="/contact/">contact page</a> is open and fixes get applied to the article itself.</li>
</ul>

<h2>What you will not find here</h2>
<p>No sponsored placements hidden inside rankings, no "we tested 30 machines" claims we cannot back
up, and no newsletter popup that follows you down the page. If a link is commercial we would rather
explain the trade-off than pretend it is neutral.</p>

<div class="card">
  <h3>Start here</h3>
  <ul>
    <li><a href="/the-ultimate-cold-brew-coffee-guide-how-to-make-smooth-cafe-quality-brew-at-home/">Cold brew, ratios included</a></li>
    <li><a href="/moka-pot-20260912-9c47/">The moka pot, done properly</a></li>
    <li><a href="/the-soul-of-vietnam-in-a-cup-a-deep-dive-into-vietnamese-coffee-culture/">Vietnamese coffee culture</a></li>
  </ul>
</div>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_contact() -> str:
    return f"""<p class="kicker">Contact</p>
<h1>Contact</h1>
<p class="lede">Corrections, questions, and story tips are all welcome. Email is the surest way to
reach us: <a href="mailto:{CONTACT_EMAIL}"><strong>{CONTACT_EMAIL}</strong></a>.</p>

<h2>Please do write if</h2>
<ul>
  <li><strong>A fact or number is wrong.</strong> Include the article URL and the source you trust —
  corrections get fixed in the piece, not in a comment nobody sees.</li>
  <li><strong>You brew something we got wrong.</strong> Different grinder, different water, different
  altitude: that is genuinely useful information for other readers.</li>
  <li><strong>You have a story tip.</strong> A roaster, a region, a brewing method we have not covered.</li>
  <li><strong>You want to write a guest guide.</strong> See the guidelines on the
  <a href="/contributors/">contributors page</a>.</li>
</ul>

<h2>Please do not bother with</h2>
<ul>
  <li>Paid link insertions or "collaboration" offers that boil down to buying a backlink.</li>
  <li>Guest posts that are thinly disguised product pages — they will not be answered.</li>
</ul>

<div class="card">
  <h3>Prefer not to email?</h3>
  <p class="muted">Follow new posts by <a href="/rss.xml">RSS</a> in any reader
  (Feedly, NetNewsWire, Inoreader) — no address required.</p>
</div>

<p class="muted">We read everything, but replies can take a few days: this site is run alongside a
full-time job.</p>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_newsletter() -> str:
    if NEWSLETTER_ACTION:
        form = f"""<form class="form" action="{NEWSLETTER_ACTION}" method="post" target="_blank" rel="noopener">
  <input type="email" name="email" placeholder="you@email.com" aria-label="Your email address" required>
  <button type="submit">Subscribe</button>
</form>
<p class="muted">One email per week at most. Unsubscribe link in every issue.</p>"""
    else:
        form = f"""<div class="card">
  <h3>The email list is not open yet</h3>
  <p>We would rather tell you that than show you a box that silently drops your address. Until the
  list is live, the feed is the fastest way to keep up:</p>
  <p><a class="cta" href="/rss.xml">Subscribe by RSS →</a></p>
  <p class="muted">Feed URL: <code>{SITE_URL}/rss.xml</code>. Paste it into Feedly, NetNewsWire,
  Inoreader or any other reader.</p>
  <p class="muted">Want email instead? Say so at
  <a href="mailto:{CONTACT_EMAIL}?subject=Newsletter">{CONTACT_EMAIL}</a> and you will be added when
  it opens.</p>
</div>"""
    return f"""<p class="kicker">Newsletter</p>
<h1>New guides, one email at a time</h1>
<p class="lede">Brewing guides, bean notes and the occasional gear verdict — short, no sponsored
filler, and never more than one email a week.</p>
{form}

<h2>What goes in it</h2>
<ul>
  <li>One or two new guides, with the ratios that actually worked.</li>
  <li>What changed our minds this month (grind size, water, a cheap tool that held up).</li>
  <li>Occasionally: something from Vietnamese coffee worth trying.</li>
</ul>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_contributors() -> str:
    rows = contributors()
    cards = []
    for r in rows:
        span = f' · {r["first"]} → {r["last"]}' if r["first"] else ""
        plural = "s" if r["posts"] != 1 else ""
        cards.append(
            '<div class="card"><div class="who">'
            '<img src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=tinysrgb&fit=crop&w=160&h=160"'
            f' alt="{r["name"]}" loading="lazy">'
            f'<div><h3 style="margin:0">{r["name"]}</h3>'
            f'<p class="muted" style="margin:2px 0 0">{r["posts"]} guide{plural}{span}</p>'
            "</div></div></div>"
        )
    people = "".join(cards) or '<div class="card"><p>No contributors yet.</p></div>'
    return f"""<p class="kicker">Contributors</p>
<h1>Who writes {SITE}</h1>
<p class="lede">{SITE} is written and maintained by the people below. Names, article counts and date
ranges are pulled straight from the published articles.</p>
<div class="grid">{people}</div>

<h2>How the work is split</h2>
<ul>
  <li><strong>Research and drafting</strong> — mostly {AUTHOR}, using AI assistance for first drafts
  and outlines.</li>
  <li><strong>Editing and fact-checking</strong> — a human pass on every article before it is
  published: numbers re-checked, unsupported claims removed, structure fixed.</li>
  <li><strong>Testing</strong> — brewed at home, on the equipment described.</li>
</ul>

<h2>Write for us</h2>
<p>Guest guides are welcome when they bring something we do not have: a specific brewing tradition, a
water-chemistry experiment, a roasting or farming perspective.</p>
<ul>
  <li>800–1,500 words, original, not published elsewhere.</li>
  <li>One clear question, answered with numbers or first-hand experience.</li>
  <li>No affiliate links, no product placements, no AI-spun filler.</li>
  <li>Pitch first — a two-paragraph outline to
  <a href="mailto:{CONTACT_EMAIL}?subject=Guest%20post%20pitch">{CONTACT_EMAIL}</a>.</li>
</ul>
<p class="muted">Accepted pieces are edited for clarity and SEO, published under your name, and
credited on this page.</p>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_pay_it_forward() -> str:
    return f"""<p class="kicker">Pay it forward</p>
<h1>Pay it forward</h1>
<p class="lede">A bag of coffee passes through a lot of hands before yours — pickers, mill workers,
truckers, roasters, baristas. This page is the short list of ways to send something back.</p>

<h2>1. Pay for the work, not just the bean</h2>
<p>The single most effective thing a home brewer can do is buy from roasters who publish what they
paid the farm, and who buy the same lot year after year. Long-term relationships beat one-off
"charity lots" every time. If a roaster cannot tell you where the coffee came from beyond the
country, that is the answer.</p>

<h2>2. Fund the research</h2>
<p>Leaf rust, drought and shrinking suitable land are existential for coffee. Two organisations doing
the unglamorous work:</p>
<ul>
  <li><a href="https://worldcoffeeresearch.org/" target="_blank" rel="noopener">World Coffee Research</a>
  — breeding better varieties openly available to farmers.</li>
  <li><a href="{FEATURED_EXTERNAL[0]}" target="_blank" rel="noopener">{FEATURED_EXTERNAL[1]}</a>
  — standards, education and the research network behind them.</li>
</ul>

<h2>3. Choose the labels that actually audit</h2>
<ul>
  <li><a href="https://www.fairtrade.net/uk-en.html" target="_blank" rel="noopener">Fairtrade</a> —
  a minimum price plus a premium that goes to the cooperative.</li>
  <li><a href="https://www.rainforest-alliance.org/" target="_blank" rel="noopener">Rainforest Alliance</a>
  — farm-level criteria covering shade, water and worker conditions.</li>
</ul>
<p>Certification is imperfect and no scheme fixes a broken price. It is still a better signal than a
roastery's own adjective count.</p>

<h2>4. Small gestures that compound</h2>
<ul>
  <li>Tip the barista who dialled in your espresso — that craft is paid hourly, not salaried.</li>
  <li>Leave a specific, honest review for small roasters. Reviews are free marketing for them, unlike
  ads.</li>
  <li>Use your grounds: compost, or a scrub for stubborn pans. Nothing in a coffee cherry needs to
  end up in landfill.</li>
</ul>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_sustainability() -> str:
    return f"""<p class="kicker">Sustainability</p>
<h1>Sustainability, without the greenwash</h1>
<p class="lede">Coffee is a crop with a real footprint — water, land, shipping, packaging. Here is
what is actually bigger, what is smaller, and what a home brewer can control.</p>

<h2>Where the impact really is</h2>
<ul>
  <li><strong>At the farm.</strong> Wet processing a single kilogram of green coffee can consume tens
  of litres of water, and it returns that water loaded with pulp and sugars. How a mill handles its
  wastewater matters more than how your coffee gets to you.</li>
  <li><strong>In the climate, on the farm.</strong> Arabica wants cool highlands; those belts are
  moving uphill and shrinking. That is why robusta — the bean Vietnamese coffee is built on — is
  getting a second look: it is hardier, and it grows lower.</li>
  <li><strong>In packaging.</strong> A capsule of coffee is a few grams of grounds wrapped in
  aluminium and plastic, and the two are bonded together. Capsules are small in volume, stubborn in
  sorting.</li>
  <li><strong>In your kitchen.</strong> Boiling a kettle and running a grinder is a rounding error
  next to the above. Waste is the part that is not: stale beans binned, brews poured down the sink.</li>
</ul>

<h2>What a home brewer can actually do</h2>
<ol>
  <li><strong>Waste less coffee.</strong> Buy bag sizes you will finish in two to four weeks, store
  them sealed and away from light, and re-brew only what you will drink. Cutting brewed-and-dumped
  coffee in half does more than switching packaging.</li>
  <li><strong>Pick a filter you will reuse.</strong> A cloth or metal filter, or a phin, removes a
  daily paper habit — and, usefully, it tastes different (filters trap oils; the same grind through
  paper and cloth are not the same cup).</li>
  <li><strong>Right-size your brew.</strong> Most of us brew 20–30 g of coffee per cup when 15–18 g
  dialled properly tastes better. Stronger is a grind problem, not a dose problem.</li>
  <li><strong>Compost the grounds.</strong> They are nitrogen-rich and acidic — good for soil, fine
  in most municipal green bins.</li>
  <li><strong>Prefer decaf in the evening to a staled third cup.</strong> Tossing a half-drunk pot
  wastes everything that went into the bean, not just the bean.</li>
</ol>

<h2>Read further</h2>
<ul>
  <li><a href="https://worldcoffeeresearch.org/" target="_blank" rel="noopener">World Coffee Research</a>
  — variety breeding, climate adaptation.</li>
  <li><a href="https://www.rainforest-alliance.org/" target="_blank" rel="noopener">Rainforest Alliance</a>
  — farm criteria including water and shade.</li>
  <li><a href="https://ico.org/" target="_blank" rel="noopener">International Coffee Organization</a>
  — production, trade and price statistics.</li>
  <li><a href="{FEATURED_EXTERNAL[0]}" target="_blank" rel="noopener">{FEATURED_EXTERNAL[1]}</a>
  — standards and sustainability programmes.</li>
  <li><a href="https://perfectdailygrind.com/" target="_blank" rel="noopener">Perfect Daily Grind</a>
  — trade-press coverage of origin-side practice.</li>
</ul>
<p class="back"><a href="/">← Back to all stories</a></p>"""


def page_privacy() -> str:
    return f"""<p class="kicker">Privacy</p>
<h1>Privacy policy</h1>
<p class="lede">Short version: we do not track you, we do not set cookies, and we do not sell
anything about you. Last updated 2026-09-20.</p>

<h2>What we collect</h2>
<p>Nothing that identifies you, and we run no analytics. There is no account system, no comment
system and no advertising script on this site.</p>

<h2>Third parties that see a request</h2>
<ul>
  <li><strong>Cloudflare Pages</strong> serves the site and keeps standard, short-lived access logs
  (IP address, user agent) for security and abuse prevention.</li>
  <li><strong>Unsplash</strong> hosts the photographs. Your browser loads them from
  <code>images.unsplash.com</code>, so Unsplash sees your IP address on those requests.</li>
  <li><strong>Google Fonts</strong> serves the typefaces used here; Google therefore sees a request
  from your browser.</li>
</ul>
<p>We do not receive any personal data from those services.</p>

<h2>Cookies</h2>
<p>None set by us. Share buttons are plain links — they do not load a social network's script until
you click through to that network.</p>

<h2>Email</h2>
<p>If you email the address on the <a href="/contact/">contact page</a>, we keep the message only for
as long as it takes to reply and do not add you to any list. There is no newsletter to be added to
yet; see the <a href="/newsletter/">newsletter page</a> for how the feed works instead.</p>

<h2>Your rights</h2>
<p>Since we hold no personal data, there is nothing to export or erase. If you believe a request from
your browser has been logged somewhere by us, write to
<a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> and we will check.</p>

<h2>Changes</h2>
<p>If the site ever gains analytics, a newsletter or ads, this page changes first — with a date — and
the change is announced in the feed.</p>
<p class="back"><a href="/">← Back to all stories</a></p>"""


PAGES = {
    "about": ("About", f"What {SITE} is, how the guides are researched and tested, and what you will not find here.", page_about),
    "contributors": ("Contributors", f"Who writes {SITE} — authors, article counts, and guest-post guidelines.", page_contributors),
    "contact": ("Contact", f"How to reach {SITE} for corrections, questions, story tips and guest posts.", page_contact),
    "newsletter": ("Newsletter", f"Brewing guides and bean notes by email — or by RSS while the list is closed.", page_newsletter),
    "pay-it-forward": ("Pay it Forward", "Concrete ways to send something back down the coffee chain: the work, the research, the labels.", page_pay_it_forward),
    "sustainability": ("Sustainability", "Coffee's real footprint — water, climate, packaging — and what a home brewer can control.", page_sustainability),
    "privacy": ("Privacy Policy", f"How {SITE} handles data: no cookies, no analytics, no tracking.", page_privacy),
}

NOT_FOUND = f"""<main class="page">
<p class="kicker">404</p>
<h1>That page is not here</h1>
<p class="lede">The link is broken, or the article moved. The coffee, however, is fine.</p>
<div class="card">
  <h3>Try one of these</h3>
  <ul>
    <li><a href="/">All stories on the homepage</a></li>
    <li><a href="/sitemap.xml">Every article (sitemap)</a></li>
    <li><a href="/rss.xml">Follow the feed</a></li>
    <li><a href="/contact/">Tell us which link broke</a></li>
  </ul>
</div>
<p class="back"><a href="/">← Back to all stories</a></p>
</main>"""


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, (title, desc, builder) in PAGES.items():
        if slug not in dict(STATIC_PAGES):
            print(f"⚠️  '{slug}' is generated but not listed in publish.STATIC_PAGES — footer/sitemap will miss it")
        d = PUBLIC / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(shell(slug, title, desc, builder()), encoding="utf-8")
        written.append(slug)
    # Real 404: Cloudflare Pages serves public/404.html (with a 404 status) for
    # unknown paths instead of falling back to index.html.
    notfound = SHELL.substitute(
        lang=LANG, title="Page not found", desc="That page is not here.",
        canonical=SITE_URL + "/", site=SITE, layout_css=LAYOUT_CSS, site_css=SITE_CSS,
        body=NOT_FOUND.split("<main class=\"page\">", 1)[1].rsplit("</main>", 1)[0],
        footer_cols=footer_cols_html(),
    )
    (PUBLIC / "404.html").write_text(notfound, encoding="utf-8")

    print(f"✅ Generated {len(written)} static pages + 404.html → {PUBLIC}/")
    print("   " + " · ".join(f"/{s}" for s in written))
    if CONTACT_EMAIL == "hello@dripper.top":
        print("ℹ️  CONTACT_EMAIL is the default (hello@dripper.top). Either enable Cloudflare "
              "Email Routing → that address, or set CONTACT_EMAIL in .env to an inbox you read.")
    if not NEWSLETTER_ACTION:
        print("ℹ️  NEWSLETTER_ACTION is empty → the newsletter page explains the list is closed "
              "and offers RSS (no fake signup form).")


if __name__ == "__main__":
    main()
