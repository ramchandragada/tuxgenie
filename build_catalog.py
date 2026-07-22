#!/usr/bin/env python3
"""Generate docs/catalog.html — a full, searchable reference of everything
TuxGenie can do — straight from tuxgenie.py so it can never go stale.

Run:  python3 build_catalog.py
CI runs this on every push to main (see .github/workflows/release.yml) and
commits the result only if it changed.

Pure standard library. Imports tuxgenie with a stubbed 'anthropic' module so it
works in CI without the SDK installed (main() is guarded, so nothing executes).
"""
import html as _html
import os
import sys
import types

sys.modules.setdefault("anthropic", types.ModuleType("anthropic"))
import tuxgenie as tg  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs", "catalog.html")


def esc(s):
    return _html.escape(str(s))


def _grouped(items, key="cat"):
    """Return [(category, [items…])] preserving first-seen category order."""
    order, buckets = [], {}
    for it in items:
        c = it[key]
        if c not in buckets:
            buckets[c] = []
            order.append(c)
        buckets[c].append(it)
    return [(c, buckets[c]) for c in order]


def _card(name, desc):
    s = f"{name} {desc}".lower().replace('"', "")
    return (f'<div class="item" data-s="{esc(s)}">'
            f'<div class="nm">{esc(name)}</div>'
            f'<div class="ds">{esc(desc)}</div></div>')


def _block(title, items):
    cards = "\n".join(_card(it["name"], it.get("desc", "")) for it in items)
    return (f'<section class="cat" data-cat="{esc(title)}">'
            f'<h3>{esc(title)} <span class="cnt">{len(items)}</span></h3>'
            f'<div class="grid">{cards}</div></section>')


def _feature_card(num, name, desc):
    s = f"{num} {name} {desc}".lower().replace('"', "")
    return (f'<div class="item" data-s="{esc(s)}">'
            f'<div class="nm"><span class="num">{esc(num)}</span> {esc(name)}</div>'
            f'<div class="ds">{esc(desc)}</div></div>')


def build():
    ver = tg.__version__
    apps = tg.APP_CATALOG
    ais = tg.AI_CATALOG
    clouds = tg.CLOUD_PROVIDERS
    feats = [(n, name, desc) for (n, kw, name, desc, fn) in tg.MENU_ITEMS if str(n).isdigit()]
    feats.sort(key=lambda t: int(t[0]))

    parts = []

    # ── Features & guided setups ─────────────────────────────────────────────
    feat_cards = "\n".join(_feature_card(n, name, desc) for n, name, desc in feats)
    parts.append(
        f'<section class="cat" data-cat="Features">'
        f'<h3>Features &amp; Guided Setups <span class="cnt">{len(feats)}</span></h3>'
        f'<div class="grid">{feat_cards}</div></section>'
    )

    # ── App catalog (grouped) ────────────────────────────────────────────────
    app_groups = _grouped(apps)
    parts.append(f'<h2 id="apps">📦 App Catalog <span class="tot">{len(apps)} apps</span></h2>')
    parts.append('<p class="lead">Install any of these with one tap from menu <b>[77]</b> — or just tell '
                 'TuxGenie the app name.</p>')
    for cat, items in app_groups:
        parts.append(_block(cat, items))

    # ── AI tools (grouped) ───────────────────────────────────────────────────
    ai_groups = _grouped(ais)
    parts.append(f'<h2 id="ai">🤖 AI Tools <span class="tot">{len(ais)} tools</span></h2>')
    parts.append('<p class="lead">One-tap AI tooling from menu <b>[99]</b> — editors, local models, '
                 'terminals and more.</p>')
    for cat, items in ai_groups:
        parts.append(_block(cat, items))

    # ── Cloud sync ───────────────────────────────────────────────────────────
    cloud_items = [{"name": c["name"], "desc": f'{c.get("type", "")} · {c.get("auth", "")}'.strip(" ·")}
                   for c in clouds]
    parts.append(f'<h2 id="cloud">☁️ Cloud Sync <span class="tot">{len(clouds)} providers</span></h2>')
    parts.append('<p class="lead">Guided setup from menu <b>[88]</b> — connect and sync in a few steps.</p>')
    parts.append(_block("Cloud providers", cloud_items))

    body = "\n".join(parts)

    tools_count = len(feats)
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="tuxgenie.svg">
<link rel="icon" type="image/png" sizes="64x64" href="favicon-64.png">
<link rel="apple-touch-icon" href="tuxgenie-256.png">
<title>TuxGenie — Full Catalog ({len(apps)} apps · {len(ais)} AI tools · {tools_count} features)</title>
<meta name="description" content="The complete TuxGenie reference: {tools_count} features and guided setups, {len(apps)} one-tap apps, {len(ais)} AI tools, and {len(clouds)} cloud providers. Search everything TuxGenie can install and do.">
<style>
:root{{--bg:#faf9ff;--card:#fff;--t1:#14152e;--t2:#4b4d6e;--t3:#8b8da8;--border:#e7e5f2;--indigo:#4f46e5;--purple:#7e22ce;--grad1:#6d28d9;--grad2:#4f46e5;}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1020;--card:#181a2e;--t1:#f2f2fa;--t2:#b9bbd6;--t3:#8385a6;--border:#26284a;}}}}
:root[data-theme="dark"]{{--bg:#0f1020;--card:#181a2e;--t1:#f2f2fa;--t2:#b9bbd6;--t3:#8385a6;--border:#26284a;}}
:root[data-theme="light"]{{--bg:#faf9ff;--card:#fff;--t1:#14152e;--t2:#4b4d6e;--t3:#8b8da8;--border:#e7e5f2;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--t1);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;}}
a{{color:var(--indigo);text-decoration:none;}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 20px 80px;}}
header{{background:linear-gradient(135deg,var(--grad1),var(--grad2));color:#fff;padding:34px 0 30px;}}
header .wrap{{padding-bottom:0;}}
header a{{color:#e9e6ff;}}
h1{{font-size:30px;margin:8px 0 6px;font-weight:800;}}
.sub{{color:#e3e0ff;font-size:15px;margin:0 0 18px;}}
.searchbar{{position:sticky;top:0;z-index:10;background:var(--bg);padding:16px 0;border-bottom:1px solid var(--border);}}
#q{{width:100%;padding:13px 16px;font-size:16px;border:2px solid var(--border);border-radius:12px;background:var(--card);color:var(--t1);outline:none;}}
#q:focus{{border-color:var(--indigo);}}
.count{{color:var(--t3);font-size:13px;margin-top:8px;}}
h2{{font-size:22px;margin:38px 0 4px;padding-top:10px;font-weight:800;}}
h2 .tot{{font-size:13px;font-weight:600;color:#fff;background:var(--indigo);padding:3px 10px;border-radius:20px;vertical-align:middle;margin-left:8px;}}
.lead{{color:var(--t2);margin:4px 0 16px;font-size:14px;}}
.cat{{margin:22px 0;}}
.cat h3{{font-size:15px;color:var(--purple);margin:0 0 10px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;}}
.cat h3 .cnt{{color:var(--t3);font-size:12px;font-weight:600;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;}}
.item{{background:var(--card);border:1px solid var(--border);border-radius:11px;padding:11px 13px;}}
.nm{{font-weight:700;font-size:14px;color:var(--t1);}}
.nm .num{{display:inline-block;min-width:24px;color:#fff;background:var(--indigo);border-radius:6px;font-size:11px;text-align:center;padding:1px 5px;margin-right:5px;}}
.ds{{color:var(--t2);font-size:12.5px;margin-top:3px;}}
.empty{{display:none;color:var(--t3);padding:30px 0;text-align:center;font-size:15px;}}
footer{{text-align:center;color:var(--t3);font-size:13px;margin-top:50px;}}
.hide{{display:none!important;}}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <a href="index.html">← Back to TuxGenie</a>
    <h1>🐧 TuxGenie — Full Catalog</h1>
    <p class="sub">Everything TuxGenie can install and do · v{ver} · Free &amp; open source</p>
  </div>
</header>
<div class="wrap">
  <div class="searchbar">
    <input id="q" type="search" placeholder="🔍 Search apps, AI tools, features…  (e.g. 'video editor', 'docker', 'privacy')" autocomplete="off" aria-label="Search the catalog">
    <div class="count" id="count"></div>
  </div>
  {body}
  <div class="empty" id="empty">No matches — try a different word.</div>
  <footer>
    <p>TuxGenie v{ver} · <a href="index.html">tuxgenie.com</a> ·
    <a href="https://github.com/ramchandragada/tuxgenie">GitHub</a> · MIT · Free forever</p>
    <p>You never have to pick from this list — just tell TuxGenie what you need in plain English.</p>
  </footer>
</div>
<script>
(function(){{
  var q=document.getElementById('q'), items=[].slice.call(document.querySelectorAll('.item'));
  var cats=[].slice.call(document.querySelectorAll('.cat')), empty=document.getElementById('empty');
  var count=document.getElementById('count'), total=items.length;
  function apply(){{
    var t=q.value.trim().toLowerCase(), shown=0;
    items.forEach(function(el){{
      var m=!t||el.getAttribute('data-s').indexOf(t)>-1;
      el.classList.toggle('hide',!m); if(m)shown++;
    }});
    cats.forEach(function(c){{
      var any=c.querySelectorAll('.item:not(.hide)').length>0;
      c.classList.toggle('hide',!any);
    }});
    empty.style.display=shown?'none':'block';
    count.textContent=t?(shown+' of '+total+' shown'):(total+' items — start typing to filter');
  }}
  q.addEventListener('input',apply); apply();
}})();
</script>
</body>
</html>
"""
    return html_doc


def main():
    doc = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = ""
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = f.read()
    if old == doc:
        print("catalog.html already current — nothing to write.")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Wrote {OUT} ({len(doc):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
