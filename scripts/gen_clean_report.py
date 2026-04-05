"""Generate clean HTML report from trend data JSON."""
import json
import html as H
import sys
from pathlib import Path


def gen_report(data_path):
    with open(data_path, encoding="utf-8") as f:
        d = json.load(f)

    e = lambda s: H.escape(str(s)) if s else ""

    status_color = {"surging": "#00E676", "steady": "#FFC107", "peaked": "#FF5252"}.get(d["status"], "#00E676")
    badge_bg = {"surging": "#dcfce7", "steady": "#fef9c3", "peaked": "#fee2e2"}.get(d["status"], "#dcfce7")

    # Timeline
    tl = ""
    for t in d.get("timeline", []):
        tl += f'<div class="ts-tl-item"><span class="d">{e(t["date"])}</span><div class="e">{e(t["event"])}</div></div>\n'

    # PESTAL
    pt = ""
    for p in d.get("pestal", []):
        pt += f'<tr><td><strong>{e(p["factor"])}</strong></td><td>{e(p["impact"])}</td></tr>\n'

    # JTBD
    jt = ""
    for j in d.get("jobs", []):
        jt += f'<div class="ts-job"><div class="ts-job-title">{e(j["job"])}</div><div class="ts-job-desc">{e(j["solution"])}</div></div>\n'

    # Market
    colors = ["#7b4fd4", "#0e7a5a", "#3b82f6", "#f59e0b", "#6b7280"]
    mk = ""
    for i, m in enumerate(d.get("market", [])):
        num = "".join(c for c in m["share"] if c.isdigit() or c == ".")
        w = min(float(num) if num else 10, 100)
        mk += (
            f'<div style="margin-bottom:16px">'
            f'<div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px">'
            f'<span style="font-weight:700">{e(m["name"])}</span>'
            f'<span style="color:#9ca3af">{e(m["share"])}</span></div>'
            f'<div style="height:14px;background:#f0f1f5;border-radius:4px;overflow:hidden">'
            f'<div style="height:100%;width:{w}%;background:{colors[i%5]};border-radius:4px"></div></div>'
            f'<div style="font-size:11px;color:#9ca3af;margin-top:2px">{e(m.get("loved",""))}</div></div>\n'
        )

    # Companies
    co = ""
    for c in d.get("competitors", []):
        co += f'<div class="ts-company"><div class="ts-company-name">{e(c["name"])}</div><div class="ts-company-desc">{e(c["detail"])}</div></div>\n'

    # Takeaways
    tk = ""
    for i, t in enumerate(d.get("takeaways", []), 1):
        tk += f'<div class="ts-rec"><div class="ts-rec-num">{i}</div><div class="ts-rec-text">{e(t)}</div></div>\n'

    cv = d.get("canvas", {})

    css = f""".ts-report{{font-family:-apple-system,'Inter',sans-serif;color:#1a1a2e;line-height:1.7;max-width:780px;margin:0 auto}}
.ts-report *{{box-sizing:border-box}}
.ts-badge{{display:inline-flex;align-items:center;gap:6px;padding:5px 14px;border-radius:100px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;background:{badge_bg};color:{status_color};border:1.5px solid {status_color}}}
.ts-hero{{text-align:center;padding:32px 0 24px}}
.ts-hero h1{{font-size:clamp(28px,5vw,42px);font-weight:900;letter-spacing:-1.5px;line-height:1.15;margin:12px 0 8px;color:#0a0a1a}}
.ts-hero .ts-sub{{font-size:14px;color:#6b7280}}
.ts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:24px 0}}
.ts-card{{background:#f8f9fc;border:1px solid #e5e7eb;border-radius:14px;padding:20px;text-align:center}}
.ts-card .label{{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#9ca3af;margin-bottom:6px}}
.ts-card .val{{font-size:28px;font-weight:800;font-family:'Courier New',monospace;color:{status_color}}}
.ts-section{{margin:32px 0}}
.ts-section h2{{font-size:20px;font-weight:700;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #f0f0f5}}
.ts-tl{{position:relative;padding-left:28px}}
.ts-tl::before{{content:'';position:absolute;left:5px;top:4px;bottom:4px;width:2px;background:linear-gradient(to bottom,{status_color},#a855f7)}}
.ts-tl-item{{position:relative;margin-bottom:16px;padding:14px 16px;background:#f8f9fc;border:1px solid #e5e7eb;border-radius:10px}}
.ts-tl-item .d{{font-family:'Courier New',monospace;font-size:12px;color:{status_color};font-weight:700}}
.ts-tl-item .e{{font-size:14px;margin-top:2px}}
.ts-table{{width:100%;border-collapse:separate;border-spacing:0;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;font-size:14px}}
.ts-table th{{background:#f0f1f5;padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#6b7280}}
.ts-table td{{padding:12px 16px;border-top:1px solid #e5e7eb}}
.ts-job,.ts-company{{background:#f8f9fc;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-bottom:12px}}
.ts-job-title,.ts-company-name{{font-weight:700;margin-bottom:4px}}
.ts-job-desc,.ts-company-desc{{font-size:13px;color:#6b7280}}
.ts-rec{{display:flex;gap:16px;margin-bottom:16px;align-items:flex-start}}
.ts-rec-num{{font-size:32px;font-weight:800;color:rgba(123,79,212,0.3);line-height:1;min-width:40px}}
.ts-rec-text{{font-size:14px;line-height:1.6}}
.ts-canvas{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.ts-canvas-item{{background:#f8f9fc;border:1px solid #e5e7eb;border-radius:10px;padding:16px}}
.ts-canvas-item h4{{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#9ca3af;margin:0 0 6px}}
.ts-canvas-item p{{font-size:13px;margin:0}}
.ts-sources{{margin-top:32px;padding:24px;background:#f8f9fc;border:1px solid #e5e7eb;border-radius:10px}}
.ts-sources h3{{font-size:16px;font-weight:700;margin-bottom:14px}}
.ts-sources ol{{padding-left:20px;margin:0}}
.ts-sources li{{font-size:13px;line-height:1.8;color:#4b5563}}
.ts-sources a{{color:#7b4fd4;text-decoration:none}}
.ts-end-cta{{background:#2D3A2D;padding:40px 24px;text-align:center;margin-top:40px;border-radius:10px}}
.ts-end-cta h3{{font-size:22px;font-weight:700;color:#EDE8E2;margin:0 0 10px}}
.ts-end-cta p{{color:#8BA886;font-size:15px;margin:0 0 20px;max-width:480px;margin-left:auto;margin-right:auto}}
.ts-end-cta a{{display:inline-block;background:#EDE8E2;color:#1A1F1A;padding:12px 28px;font-weight:700;text-decoration:none;border-radius:8px;font-size:14px}}
@media(max-width:640px){{.ts-canvas{{grid-template-columns:1fr}}.ts-grid{{grid-template-columns:1fr 1fr}}}}"""

    g5 = e(d["growth_5y"].split("—")[0].strip()[:15])
    g1 = e(d["growth_1y"].split("—")[0].strip()[:15])
    g3 = e(d["growth_3m"].split("—")[0].strip()[:15])

    return f"""<div class="ts-report">
<style>{css}</style>
<div class="ts-hero">
<span class="ts-badge">{d['status'].upper()}</span>
<h1>{e(d['trend_name'])}</h1>
<p class="ts-sub">{e(d['category'])}</p>
</div>
<div class="ts-grid">
<div class="ts-card"><div class="label">5 ans</div><div class="val">{g5}</div></div>
<div class="ts-card"><div class="label">1 an</div><div class="val">{g1}</div></div>
<div class="ts-card"><div class="label">3 mois</div><div class="val">{g3}</div></div>
</div>
<div class="ts-section"><h2>Catalyseur</h2><p>{e(d.get('trigger',''))}</p></div>
<div class="ts-section"><h2>Chronologie</h2><div class="ts-tl">{tl}</div></div>
<div class="ts-section"><h2>Analyse PESTAL</h2><table class="ts-table"><thead><tr><th>Facteur</th><th>Impact</th></tr></thead><tbody>{pt}</tbody></table></div>
<div class="ts-section"><h2>Jobs to Be Done</h2>{jt}</div>
<div class="ts-section"><h2>Consumer Trend Canvas</h2>
<div class="ts-canvas">
<div class="ts-canvas-item"><h4>Qui</h4><p>{e(cv.get('who',''))}</p></div>
<div class="ts-canvas-item"><h4>O\u00f9</h4><p>{e(cv.get('where',''))}</p></div>
<div class="ts-canvas-item"><h4>Pourquoi maintenant</h4><p>{e(cv.get('why_now',''))}</p></div>
<div class="ts-canvas-item"><h4>Comportement</h4><p>{e(cv.get('behavior',''))}</p></div>
</div>
<div class="ts-canvas" style="margin-top:16px">
<div class="ts-canvas-item" style="grid-column:1/-1"><h4>Besoins non satisfaits</h4><p>{e(cv.get('unmet',''))}</p></div>
</div></div>
<div class="ts-section"><h2>Positionnement march\u00e9</h2>{mk}</div>
<div class="ts-section"><h2>Acteurs \u00e0 surveiller</h2>{co}</div>
<div class="ts-section"><h2>Recommandations</h2>{tk}</div>
</div>"""


if __name__ == "__main__":
    data_path = sys.argv[1]
    out_path = sys.argv[2]
    html = gen_report(data_path)
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Generated: {len(html)} chars → {out_path}")
