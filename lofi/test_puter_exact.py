"""Teste do HTML exato passado pelo usuario, dentro do Playwright."""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
OUT_HTML = ROOT / "output" / "_puter_test.html"
OUT_HTML.write_text("""<!doctype html>
<html><body>
<script src="https://js.puter.com/v2/"></script>
<script>
  window._done = false;
  window._err  = null;
  puter.ai.txt2img("a cat playing the piano", {
    model: "gpt-image-1.5",
    quality: "low"
  }).then(img => {
    document.body.appendChild(img);
    window._imgSrc = img.src;
    window._done = true;
  }).catch(e => {
    window._err = (e && e.message) || String(e) || JSON.stringify(e);
    window._done = true;
  });
</script>
</body></html>
""", encoding="utf-8")

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(180_000)
    page.goto(OUT_HTML.as_uri())
    print("Aguardando puter.ai.txt2img...")
    page.wait_for_function("window._done === true", timeout=180_000)
    err = page.evaluate("() => window._err")
    src = page.evaluate("() => window._imgSrc")
    if err:
        print(f"ERRO: {err}")
    else:
        print(f"OK! src={src[:80] if src else None}")
    browser.close()
