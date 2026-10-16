# ruff: noqa: E501 — the embedded HTML/JS page keeps its own line lengths
"""Local review screen for coded segments: `hrsurvey review-ui --wave W`.

Runs only on 127.0.0.1, reads and writes data/interim/<wave>/review_segments.csv directly, and
makes no outside requests — respondent text never leaves the machine. A random per-run token in
the URL guards the save endpoint against requests from other browser tabs.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from hrsurvey.text.review import REVIEW_STATUSES, SEGMENT_COLUMNS, ReviewError, read_review
from hrsurvey.text.review_labels import CATEGORIES_TR, LOCUS_TR, QUESTIONS_TR, THEMES_TR
from hrsurvey.text.settings import Codebook

MAX_BODY_BYTES = 5_000_000


def page_payload(review: pd.DataFrame, codebook: Codebook) -> dict:
    return {
        "rows": review.to_dict("records"),
        "columns": list(SEGMENT_COLUMNS),
        "themes": codebook.themes,
        "locus": codebook.locus,
        "codebookVersion": codebook.version,
        "themesTr": THEMES_TR,
        "categoriesTr": CATEGORIES_TR,
        "locusTr": LOCUS_TR,
        "questionsTr": QUESTIONS_TR,
    }


def build_page(review: pd.DataFrame, codebook: Codebook, token: str) -> str:
    data = json.dumps(page_payload(review, codebook), ensure_ascii=False)
    # "</" inside a JSON string would end the <script> element early
    safe = data.replace("</", "<\\/")
    return PAGE.replace("__DATA__", safe).replace("__TOKEN__", token)


def save_rows(path: Path, rows: list[dict]) -> int:
    """Validate an edited copy against the file on disk, then replace it atomically."""
    current = read_review(path)
    edited = pd.DataFrame(rows, dtype=str).fillna("")
    missing = set(SEGMENT_COLUMNS) - set(edited.columns)
    if missing:
        raise ReviewError(f"missing columns {sorted(missing)}")
    edited = edited[list(SEGMENT_COLUMNS)]
    if set(edited["segment_id"]) != set(current["segment_id"]) or len(edited) != len(current):
        raise ReviewError("segment list changed on disk — reload the page")
    if not edited["review_status"].isin(REVIEW_STATUSES).all():
        raise ReviewError("invalid review_status")
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".csv.tmp")
    os.close(fd)
    edited.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)
    return int((edited["review_status"] != "pending").sum())


def make_handler(path: Path, codebook: Codebook, token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # never log request lines (no data in logs)
            return

        def _send(self, status: int, body: str, content_type: str) -> None:
            raw = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path != f"/{token}":
                self._send(404, "not found", "text/plain")
                return
            page = build_page(read_review(path), codebook, token)
            self._send(200, page, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            if self.path != "/save" or self.headers.get("X-Token") != token:
                self._send(403, "forbidden", "text/plain")
                return
            if length > MAX_BODY_BYTES:
                self._send(413, "too large", "text/plain")
                return
            try:
                rows = json.loads(self.rfile.read(length))["rows"]
                decided = save_rows(path, rows)
            except (ReviewError, ValueError, KeyError) as err:
                self._send(400, json.dumps({"error": str(err)}), "application/json")
                return
            self._send(200, json.dumps({"ok": True, "decided": decided}), "application/json")

    return Handler


def serve(path: Path, codebook: Codebook, port: int) -> tuple[ThreadingHTTPServer, str]:
    token = secrets.token_urlsafe(16)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(path, codebook, token))
    return server, f"http://127.0.0.1:{server.server_address[1]}/{token}"


PAGE = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cevap Kontrolü</title>
<style>
:root {
  --bg: #f5f3ef; --surface: #ffffff; --ink: #1f1e1c; --muted: #6d6a64; --line: #e4e0d8;
  --accent: #2f5d8a; --accent-ink: #ffffff; --soft: #eef3f8;
  --ok: #2e7d4f; --ok-bg: #e5f2ea; --bad: #a8412f; --bad-bg: #f6e4df; --warn: #8a5d00; --warn-bg: #fbf0d6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #151514; --surface: #1f1e1c; --ink: #ecebe6; --muted: #a29f98; --line: #34322e;
    --accent: #86b4e2; --accent-ink: #10151b; --soft: #1d2732;
    --ok: #7fca9c; --ok-bg: #1b2c22; --bad: #e8907d; --bad-bg: #37211c; --warn: #e4b955; --warn-bg: #332914;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.wrap { max-width: 720px; margin: 0 auto; padding: 24px 16px 64px; }
.top { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
.progress { flex: 1 1 180px; height: 10px; background: var(--line); border-radius: 99px; overflow: hidden; }
.progress span { display: block; height: 100%; background: var(--ok); transition: width .25s; }
.count { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 14px; }
.saved { font-size: 13px; color: var(--muted); }
.saved.err { color: var(--bad); }
.link { background: none; border: 0; color: var(--accent); font: inherit; font-size: 14px; cursor: pointer; padding: 0; }
.link:disabled { color: var(--muted); cursor: default; opacity: .5; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 24px; }
h1 { font-size: 26px; margin: 0 0 6px; line-height: 1.25; }
h2 { font-size: 17px; margin: 22px 0 6px; }
.lead { color: var(--muted); margin: 0 0 16px; }
.step { display: flex; gap: 12px; margin: 12px 0; }
.num { flex: 0 0 28px; height: 28px; border-radius: 50%; background: var(--soft); color: var(--accent);
  display: grid; place-items: center; font-weight: 600; font-size: 14px; }
.eyebrow { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin: 0 0 4px; }
.question { font-size: 15px; margin: 0 0 18px; }
.quote { font-size: 19px; line-height: 1.5; margin: 0 0 6px; padding: 14px 16px; background: var(--soft);
  border-radius: 12px; }
.note { font-size: 13px; color: var(--muted); margin: 0 0 20px; }
.reading { border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; margin-bottom: 18px; }
.reading dl { display: grid; grid-template-columns: max-content 1fr; gap: 8px 14px; margin: 8px 0 0; }
.reading dt { color: var(--muted); font-size: 14px; }
.reading dd { margin: 0; font-weight: 500; }
.hint { border-radius: 10px; padding: 10px 14px; margin: 0 0 16px; font-size: 14px;
  background: var(--warn-bg); color: var(--warn); }
.ask { font-size: 18px; font-weight: 600; margin: 4px 0 12px; }
.choices { display: grid; gap: 10px; }
.big { display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; border: 1px solid var(--line);
  background: var(--surface); color: var(--ink); border-radius: 12px; padding: 14px 16px; font: inherit;
  font-size: 16px; cursor: pointer; }
.big:hover { border-color: var(--accent); }
.big .ico { font-size: 20px; width: 26px; text-align: center; }
.big small { display: block; color: var(--muted); font-size: 13px; }
.big.yes { background: var(--ok-bg); border-color: transparent; }
.big.no { background: var(--bad-bg); border-color: transparent; }
.primary { background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 12px; padding: 13px 22px;
  font: inherit; font-weight: 600; cursor: pointer; }
.secondary { background: none; border: 1px solid var(--line); color: var(--ink); border-radius: 12px; padding: 12px 18px;
  font: inherit; cursor: pointer; }
.row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.opts { display: grid; gap: 6px; max-height: 300px; overflow: auto; padding: 2px; }
.opt { display: flex; gap: 10px; align-items: flex-start; padding: 9px 12px; border: 1px solid var(--line);
  border-radius: 10px; cursor: pointer; background: var(--surface); }
.opt:has(input:checked) { border-color: var(--accent); background: var(--soft); }
.opt input { margin-top: 4px; }
select, input[type=text] { font: inherit; color: var(--ink); background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; padding: 9px 12px; width: 100%; }
.pills { display: flex; gap: 8px; flex-wrap: wrap; }
.pill { border: 1px solid var(--line); background: var(--surface); color: var(--ink); border-radius: 99px;
  padding: 8px 16px; font: inherit; cursor: pointer; }
.pill.on { background: var(--accent); color: var(--accent-ink); border-color: transparent; }
.done-ico { font-size: 44px; }
.stats { display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0; }
.stat { background: var(--soft); border-radius: 12px; padding: 10px 14px; min-width: 120px; }
.stat b { display: block; font-size: 22px; }
@media (max-width: 520px) { .panel { padding: 18px; } h1 { font-size: 22px; } .quote { font-size: 17px; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="top" id="top" hidden>
    <button class="link" id="back">← Önceki</button>
    <div class="progress"><span id="prog"></span></div>
    <span class="count" id="count"></span>
    <span class="saved" id="saved">Kaydedildi</span>
  </div>
  <div id="view"></div>
</div>
<script>
const DATA = __DATA__;
const TOKEN = "__TOKEN__";
const rows = DATA.rows.map(r => ({...r,
  sarcasm: String(r.sarcasm).toLowerCase() === "true" ? "true" : "false",
  actionable: String(r.actionable).toLowerCase() === "true" ? "true" : "false",
  review_status: String(r.review_status).trim().toLowerCase(),
  valence: String(r.valence).replace(/\.0$/, "")}));
const original = new Map(rows.map(r => [r.segment_id, snapshot(r)]));
function snapshot(r) { return [r.theme, r.secondary_theme, r.new_theme_label, r.locus, r.valence, r.sarcasm, r.actionable].join("|"); }

const T = DATA.themesTr, C = DATA.categoriesTr, L = DATA.locusTr, Q = DATA.questionsTr;
const themeText = code => code === "NEW" ? "Yeni konu" : (T[code] || DATA.themes[code] || code);
const catOf = code => code.split(".")[0];
const tone = v => ({"1": "🙂 Olumlu", "0": "😐 Nötr / sadece bilgi", "-1": "🙁 Olumsuz"})[v] || v;
const view = document.getElementById("view");
const h = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v; else if (k.startsWith("on")) n[k] = v;
    else if (v === true) n.setAttribute(k, ""); else if (v !== false && v != null) n.setAttribute(k, v);
  }
  kids.flat().forEach(c => c != null && n.append(c instanceof Node ? c : document.createTextNode(c)));
  return n;
};

let queue = rows.filter(r => r.review_status === "pending");
let pos = 0;
const history = [];

function updateTop() {
  const done = rows.filter(r => r.review_status !== "pending").length;
  document.getElementById("prog").style.width = (100 * done / rows.length) + "%";
  document.getElementById("count").textContent = `${done} / ${rows.length} kontrol edildi`;
  document.getElementById("back").disabled = !history.length;
}

function intro() {
  document.getElementById("top").hidden = true;
  const left = rows.filter(r => r.review_status === "pending").length;
  const minutes = Math.max(1, Math.round(left * 15 / 60));
  view.replaceChildren(h("div", {class: "panel"},
    h("h1", {}, "Yapay zekânın yorumlarını kontrol edelim"),
    h("p", {class: "lead"}, `Kalan ${left} parça · yaklaşık ${minutes} dakika`),
    h("div", {class: "step"}, h("span", {class: "num"}, "1"), h("div", {},
      h("b", {}, "Ne oldu? "), "Çalışanların yazılı cevaplarını yapay zekâ küçük parçalara böldü ve her parçanın ",
      h("i", {}, "neyle ilgili"), " olduğunu tahmin etti (ör. “kararlar çok geç çıkıyor”).")),
    h("div", {class: "step"}, h("span", {class: "num"}, "2"), h("div", {},
      h("b", {}, "Senin işin: "), "Her parçada bu tahminin doğru olup olmadığına bakmak. Raporlar bu etiketlerden çıkacak; yanlış etiket yanlış sonuç demek.")),
    h("div", {class: "step"}, h("span", {class: "num"}, "3"), h("div", {},
      h("b", {}, "Nasıl? "), "Her seferinde tek parça göreceksin ve üç seçenekten birine basacaksın: ",
      h("b", {}, "Doğru"), ", ", h("b", {}, "Düzelt"), " veya ", h("b", {}, "Çıkar"),
      ". Kararın anında kaydedilir; istediğin zaman bırakıp sonra devam edebilirsin.")),
    h("div", {class: "row"},
      left ? h("button", {class: "primary", onclick: () => show(0)}, "Başla →")
           : h("button", {class: "primary", onclick: done}, "Özeti gör"))));
}

function show(i) {
  pos = i;
  if (pos >= queue.length) return done();
  document.getElementById("top").hidden = false;
  updateTop();
  const r = queue[pos];
  const hints = [];
  if (r.var_id.startsWith("q14_") || r.var_id.startsWith("q15_"))
    hints.push("İpucu: Bu soruya bazen alaycı cevaplar verilir (ör. “en çok keyif aldığım şey kahve makinesi”). Cevap ciddi değilse “Düzelt” deyip “alaycı” işaretle.");
  if (r.confidence === "low") hints.push("Yapay zekâ bu yorumdan pek emin değil — biraz daha dikkatli bak.");
  if (r.theme === "NEW") hints.push(`Yapay zekâ listede uygun konu bulamadı ve yeni bir konu önerdi: “${r.new_theme_label}”. Uygunsa “Doğru” de, listeden daha iyi bir konu varsa “Düzelt”.`);
  const reading = h("div", {class: "reading"},
    h("p", {class: "eyebrow"}, "Yapay zekâ bunu şöyle yorumladı"),
    h("dl", {},
      h("dt", {}, "Konusu"), h("dd", {}, themeText(r.theme),
        r.theme !== "NEW" ? h("div", {class: "note", style: "margin:2px 0 0"}, C[catOf(r.theme)] || "") : null),
      r.secondary_theme ? h("dt", {}, "İkinci konusu") : null,
      r.secondary_theme ? h("dd", {}, themeText(r.secondary_theme)) : null,
      h("dt", {}, "Kimi / neyi işaret ediyor"), h("dd", {}, L[r.locus] || r.locus),
      h("dt", {}, "Tonu"), h("dd", {}, tone(r.valence), r.sarcasm === "true" ? " · alaycı (ironik) söylenmiş" : "",
        r.actionable === "true" ? " · 💡 öneri içeriyor" : "")));
  view.replaceChildren(h("div", {class: "panel"},
    h("p", {class: "eyebrow"}, "Çalışana sorulan soru"),
    h("p", {class: "question"}, Q[r.var_id] || r.q_no),
    h("p", {class: "eyebrow"}, "Cevaptan bir parça"),
    h("p", {class: "quote"}, `“${r.text_en}”`),
    h("p", {class: "note"}, "Cevaplar karşılaştırılabilsin diye İngilizceye çevrildi; isimler gibi kişisel bilgiler [PERSON] gibi işaretlerle gizlendi."),
    hints.map(t => h("p", {class: "hint"}, t)),
    reading,
    h("p", {class: "ask"}, "Bu yorum doğru mu?"),
    h("div", {class: "choices"},
      h("button", {class: "big yes", onclick: () => decide(r, "accept")},
        h("span", {class: "ico"}, "✓"), h("span", {}, "Evet, doğru", h("small", {}, "Etiket uygun, sonraki parçaya geç"))),
      h("button", {class: "big", onclick: () => edit(r)},
        h("span", {class: "ico"}, "✎"), h("span", {}, "Kısmen / hayır — düzelteyim", h("small", {}, "Konuyu, işaret ettiği tarafı veya tonu değiştir"))),
      h("button", {class: "big no", onclick: () => decide(r, "reject")},
        h("span", {class: "ico"}, "✗"), h("span", {}, "Bu parça bir şey anlatmıyor, çıkar", h("small", {}, "Analize hiç girmesin (ör. anlamsız ya da bölünmüş bir parça)"))))));
  window.scrollTo({top: 0});
}

function edit(r) {
  const draft = {theme: r.theme, new_theme_label: r.new_theme_label, locus: r.locus, valence: r.valence, sarcasm: r.sarcasm,
    actionable: r.actionable, secondary_theme: r.secondary_theme || "", reviewer_note: r.reviewer_note || ""};
  const cats = Object.keys(C).filter(c => Object.keys(DATA.themes).some(t => catOf(t) === c));
  let cat = draft.theme === "NEW" ? "NEW" : catOf(draft.theme);
  const themeBox = h("div");
  const catSel = h("select", {onchange: e => { cat = e.target.value; drawThemes(); }},
    cats.map(c => h("option", {value: c, selected: c === cat}, C[c])),
    h("option", {value: "NEW", selected: cat === "NEW"}, "Hiçbiri uymuyor — yeni konu yazacağım"));
  function drawThemes() {
    if (cat === "NEW") {
      draft.theme = "NEW";
      themeBox.replaceChildren(h("input", {type: "text", value: draft.new_theme_label || "",
        placeholder: "Yeni konunun kısa adı (ör. “uzaktan çalışma”) — yorum için en alttaki not alanını kullan",
        oninput: e => draft.new_theme_label = e.target.value}));
      return;
    }
    const codes = Object.keys(DATA.themes).filter(t => catOf(t) === cat);
    if (!codes.includes(draft.theme)) draft.theme = codes[0];
    themeBox.replaceChildren(h("div", {class: "opts"}, codes.map(code => h("label", {class: "opt"},
      h("input", {type: "radio", name: "theme", checked: code === draft.theme, onchange: () => draft.theme = code}),
      h("span", {}, themeText(code))))));
  }
  drawThemes();
  const pills = (field, values, labels) => {
    const box = h("div", {class: "pills"});
    const draw = () => box.replaceChildren(...values.map((v, i) => h("button", {class: "pill" + (draft[field] === v ? " on" : ""),
      onclick: () => { draft[field] = v; draw(); }}, labels[i])));
    draw(); return box;
  };
  view.replaceChildren(h("div", {class: "panel"},
    h("p", {class: "eyebrow"}, "Düzeltiyorsun"),
    h("p", {class: "quote"}, `“${r.text_en}”`),
    h("h2", {}, "1. Bu parça asıl neyle ilgili?"),
    h("p", {class: "note", style: "margin:0 0 8px"}, "Önce genel alanı seç, sonra en yakın açıklamayı işaretle."),
    catSel, h("div", {style: "height:10px"}), themeBox,
    h("h2", {}, "İkinci bir konusu da var mı? (isteğe bağlı)"),
    h("p", {class: "note", style: "margin:0 0 8px"}, "Parça iki konuya birden giriyorsa ikincisini seç (ör. hem “müşteri bilmiyor” hem “proaktif yaklaşım”)."),
    h("select", {onchange: e => draft.secondary_theme = e.target.value},
      h("option", {value: ""}, "— Yok —"),
      Object.keys(C).filter(c => Object.keys(DATA.themes).some(x => catOf(x) === c)).map(c =>
        h("optgroup", {label: C[c]}, Object.keys(DATA.themes).filter(x => catOf(x) === c).map(code =>
          h("option", {value: code, selected: code === draft.secondary_theme}, themeText(code)))))),
    h("h2", {}, "2. Kimi veya neyi işaret ediyor?"),
    h("div", {class: "opts"}, Object.keys(L).map(code => h("label", {class: "opt"},
      h("input", {type: "radio", name: "locus", checked: code === draft.locus, onchange: () => draft.locus = code}),
      h("span", {}, L[code])))),
    h("h2", {}, "3. Tonu nasıl? Bir öneri içeriyor mu?"),
    h("p", {class: "note", style: "margin:0 0 8px"}, "Ton ve öneri birbirinden bağımsız: “Maaşlar düşük, artırılmalı” hem olumsuz hem öneridir."),
    h("div", {class: "pills"},
      pills("valence", ["-1", "0", "1"], ["🙁 Olumsuz", "😐 Nötr", "🙂 Olumlu"]),
      pills("actionable", ["true", "false"], ["💡 Öneri var", "Öneri yok"])),
    h("h2", {}, "4. Alaycı (ironik) mi söylenmiş?"),
    pills("sarcasm", ["false", "true"], ["Hayır, ciddi", "Evet, alaycı"]),
    h("h2", {}, "5. Notun (isteğe bağlı)"),
    h("input", {type: "text", value: draft.reviewer_note, placeholder: "Yorum, şüphe ya da görüşmede sorulacak bir şey",
      oninput: e => draft.reviewer_note = e.target.value}),
    h("div", {class: "row"},
      h("button", {class: "primary", onclick: () => {
        if (draft.theme === "NEW" && !(draft.new_theme_label || "").trim()) { alert("Yeni konu için kısa bir ad yaz."); return; }
        Object.assign(r, draft);
        if (draft.theme !== "NEW") r.new_theme_label = "";
        if (r.secondary_theme === r.theme) r.secondary_theme = "";  // a topic cannot be its own second topic
        decide(r, "accept");
      }}, "Kaydet ve sonraki →"),
      h("button", {class: "secondary", onclick: () => show(pos)}, "Vazgeç"))));
  window.scrollTo({top: 0});
}

function decide(r, action) {
  r.review_status = action === "reject" ? "rejected" : (snapshot(r) === original.get(r.segment_id) ? "accepted" : "edited");
  history.push(pos);
  save();
  show(pos + 1);
}

document.getElementById("back").onclick = () => {
  if (!history.length) return;
  const prev = history.pop();
  queue[prev].review_status = "pending";
  save();
  show(prev);
};

function done() {
  document.getElementById("top").hidden = false; updateTop();
  const count = s => rows.filter(r => r.review_status === s).length;
  const pending = count("pending");
  view.replaceChildren(h("div", {class: "panel"},
    h("div", {class: "done-ico"}, pending ? "⏸" : "🎉"),
    h("h1", {}, pending ? "Şimdilik bu kadar" : "Hepsi tamam, teşekkürler!"),
    h("p", {class: "lead"}, pending
      ? `${pending} parça hâlâ bekliyor. İstediğin zaman bu sayfayı yeniden açıp devam edebilirsin.`
      : "Bütün parçalar kontrol edildi ve kaydedildi. Bu pencereyi kapatabilirsin."),
    h("div", {class: "stats"},
      h("div", {class: "stat"}, h("b", {}, count("accepted")), "doğru bulundu"),
      h("div", {class: "stat"}, h("b", {}, count("edited")), "düzeltildi"),
      h("div", {class: "stat"}, h("b", {}, count("rejected")), "çıkarıldı")),
    pending ? null : h("p", {}, h("b", {}, "Sıradaki adım: "), "Claude'a sohbette “bitti” yazman yeterli; sonuçları o aktaracak."),
    h("div", {class: "row"},
      pending ? h("button", {class: "primary", onclick: () => { queue = rows.filter(r => r.review_status === "pending"); history.length = 0; show(0); }}, "Kalanlara devam et") : null,
      h("button", {class: "secondary", onclick: () => { queue = rows.filter(r => r.coder !== "rule"); history.length = 0; show(0); }}, "Hepsini baştan gözden geçir"))));
}

let saving = Promise.resolve();
function save() {
  const s = document.getElementById("saved");
  s.textContent = "Kaydediliyor…"; s.className = "saved";
  saving = saving.then(async () => {
    try {
      const res = await fetch("/save", {method: "POST", headers: {"Content-Type": "application/json", "X-Token": TOKEN},
        body: JSON.stringify({rows})});
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || res.status);
      s.textContent = "✓ Kaydedildi"; s.className = "saved";
    } catch (e) { s.textContent = "Kaydedilemedi — sayfayı yenile (" + e.message + ")"; s.className = "saved err"; }
  });
}
intro();
</script>
</body>
</html>
"""
