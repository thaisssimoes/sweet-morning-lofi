"""Testar puter.ai.chat com modelo gemini-2.5-flash-image (gera imagem via chat)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
OUT_HTML = ROOT / "output" / "_puter_chat_test.html"
OUT_HTML.write_text("""<!doctype html>
<html><body>
<script src="https://js.puter.com/v2/"></script>
<script>
  window._done = false;
  window._err  = null;
  window._imgUrl = null;
  window._text = null;
  (async () => {
    try {
      const result = await puter.ai.chat("Draw a cute small yellow chick standing in green grass garden, watercolor children book style", {
        model: "gemini-2.5-flash-image",
      });
      window._text = result.message.content || "";
      if (result.message.images && result.message.images.length > 0) {
        window._imgUrl = result.message.images[0].image_url.url;
      }
    } catch (e) {
      window._err = (e && e.message) || JSON.stringify(e).slice(0, 300) || String(e);
    }
    window._done = true;
  })();
</script>
</body></html>
""", encoding="utf-8")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(180_000)
    page.goto(OUT_HTML.as_uri())
    print("Aguardando puter.ai.chat (gemini)...")
    try:
        page.wait_for_function("window._done === true", timeout=180_000)
    except Exception as e:
        print(f"timeout: {e}")
        browser.close()
        raise SystemExit(1)
    err = page.evaluate("() => window._err")
    txt = page.evaluate("() => window._text")
    img = page.evaluate("() => window._imgUrl")
    print(f"ERR: {err}")
    print(f"TEXT: {(txt or '')[:200]}")
    print(f"IMG: {(img or '')[:120] if img else None}")
    browser.close()
