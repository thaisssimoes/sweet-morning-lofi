"""
Generate images via puter.ai.txt2img() using Playwright + a real (headless) browser.

Puter.js handles its own anonymous auth (temp user) under the hood. Rather than
reverse-engineer that, we just run their official client library in a headless
Chromium and grab the resulting image.

Usage:
    from puter_image import PuterImageGen
    gen = PuterImageGen()                       # opens browser once
    gen.txt2img("cute yellow chick", out_path)
    gen.close()
"""
import base64
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


_HTML = """<!doctype html>
<html><head>
  <meta charset="utf-8">
  <script src="https://js.puter.com/v2/"></script>
</head><body>
  <div id="status">loading...</div>
  <script>
    window._puterReady = new Promise(r => {
        const t = setInterval(() => {
            if (window.puter && puter.ai && puter.ai.txt2img) {
                clearInterval(t);
                document.getElementById('status').textContent = 'ready';
                r();
            }
        }, 50);
    });

    // Fetch the generated image element and return its data URL.
    // Surface any failure as a structured error message string.
    window.genImage = async (prompt, opts) => {
        try {
            await window._puterReady;
            const result = await puter.ai.txt2img(prompt, opts || {});
            // puter usually returns an <img> element; sometimes a URL string.
            let src;
            if (typeof result === 'string') src = result;
            else if (result && result.src) src = result.src;
            else throw new Error('unknown txt2img result: ' + JSON.stringify(result).slice(0, 200));
            if (src.startsWith('data:')) return src;
            const res = await fetch(src);
            if (!res.ok) throw new Error('fetch failed: ' + res.status);
            const blob = await res.blob();
            return await new Promise((resolve) => {
                const r = new FileReader();
                r.onloadend = () => resolve(r.result);
                r.readAsDataURL(blob);
            });
        } catch (e) {
            // re-throw as a plain string so Python sees a real message
            const msg = e && (e.message || JSON.stringify(e).slice(0, 300)) || String(e);
            throw 'PUTER_ERR: ' + msg;
        }
    };
  </script>
</body></html>"""


_HOST_URL = "https://puter.com/_mock_host.html"


class PuterImageGen:
    def __init__(self, headless: bool = True, timeout_ms: int = 180_000):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        ctx = self._browser.new_context()
        # Intercept a fake puter.com URL and serve our test HTML so the page
        # has the right origin for puter.js's anonymous-auth flow.
        ctx.route(_HOST_URL, lambda route: route.fulfill(
            status=200, content_type="text/html", body=_HTML))
        self._page = ctx.new_page()
        self._page.set_default_timeout(timeout_ms)
        self._page.goto(_HOST_URL)
        self._page.wait_for_function(
            "document.getElementById('status').textContent === 'ready'")

    def txt2img(self, prompt: str, out_path: Path,
                model: str = "gpt-image-1", quality: str = "medium",
                retries: int = 3) -> None:
        opts = {"model": model, "quality": quality}
        last_err = None
        for attempt in range(retries):
            try:
                data_url = self._page.evaluate(
                    "([p,o]) => window.genImage(p, o)",
                    [prompt, opts],
                )
                if not data_url or "," not in data_url:
                    raise RuntimeError("empty data URL")
                head, b64 = data_url.split(",", 1)
                out_path.write_bytes(base64.b64decode(b64))
                if out_path.stat().st_size < 2048:
                    out_path.unlink(missing_ok=True)
                    raise RuntimeError("file too small")
                return
            except Exception as exc:
                last_err = exc
                print(f"      retry {attempt+1}/{retries}: {exc}")
                time.sleep(4)
        raise RuntimeError(f"Puter txt2img failed after {retries} tries: {last_err}")

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()


if __name__ == "__main__":
    # quick smoke test
    import sys
    out = Path(__file__).parent.parent / "output" / "_puter_smoke.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    g = PuterImageGen()
    try:
        print("Generating smoke test image...")
        g.txt2img("a cute small yellow chick standing in green grass, watercolor", out)
        print(f"OK: {out}  ({out.stat().st_size} bytes)")
    finally:
        g.close()
