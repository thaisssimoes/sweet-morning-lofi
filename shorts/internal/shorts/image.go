package shorts

import (
	"fmt"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

const pollinationsBase = "https://image.pollinations.ai/prompt"

// ImageGen requests images from Pollinations.
// The free / anonymous tier rate-limits aggressively with 402 once you exceed quota,
// so callers should use low concurrency and pacing between requests. We also fall back
// from `flux` to `turbo` when flux is throttled — turbo has a separate, more permissive quota.
type ImageGen struct {
	Width        int // e.g. 1080 for vertical short
	Height       int // e.g. 1920
	OutputDir    string
	Seed         int           // base seed; per-scene offset added so each scene varies but is reproducible
	Timeout      time.Duration // per-request HTTP timeout
	MinSpacing   time.Duration // minimum wall-clock gap between any two successful requests (rate-limit avoidance)
	MaxAttempts  int           // attempts per model before falling back to next model
	Models       []string      // ordered fallback list, e.g. ["flux", "turbo"]
	mu           sync.Mutex
	lastReqStart time.Time
}

// throttle blocks until at least MinSpacing has passed since the previous request started.
func (g *ImageGen) throttle() {
	if g.MinSpacing <= 0 {
		return
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	wait := time.Until(g.lastReqStart.Add(g.MinSpacing))
	if wait > 0 {
		time.Sleep(wait)
	}
	g.lastReqStart = time.Now()
}

// GenerateOne fetches a single scene's image. Tries each model in turn; for each model
// retries up to MaxAttempts on non-200 responses with exponential backoff.
func (g *ImageGen) GenerateOne(sceneIdx int, prompt string) (string, error) {
	seed := g.Seed + sceneIdx*1000
	encoded := url.PathEscape(prompt)

	timeout := g.Timeout
	if timeout == 0 {
		timeout = 240 * time.Second
	}
	maxAttempts := g.MaxAttempts
	if maxAttempts <= 0 {
		maxAttempts = 4
	}
	models := g.Models
	if len(models) == 0 {
		models = []string{"flux", "turbo"}
	}
	if err := os.MkdirAll(g.OutputDir, 0755); err != nil {
		return "", fmt.Errorf("scene %d: mkdir: %w", sceneIdx, err)
	}
	out := filepath.Join(g.OutputDir, fmt.Sprintf("scene_%02d.jpg", sceneIdx))

	var lastErr error
	for _, model := range models {
		u := fmt.Sprintf(
			"%s/%s?width=%d&height=%d&nologo=true&model=%s&seed=%d",
			pollinationsBase, encoded, g.Width, g.Height, model, seed,
		)
		backoff := 6 * time.Second
		for attempt := 1; attempt <= maxAttempts; attempt++ {
			g.throttle()
			// Use curl as subprocess — Go's net/http appears to be filtered by
			// Pollinations (possibly TLS fingerprinting via Cloudflare), while curl gets 200.
			err := curlDownload(u, out, timeout)
			if err == nil {
				// Sanity check size — Pollinations sometimes returns tiny error blobs as 200.
				if st, serr := os.Stat(out); serr == nil && st.Size() >= 1024 {
					return out, nil
				}
				os.Remove(out)
				lastErr = fmt.Errorf("response too small")
			} else {
				lastErr = err
			}
			if attempt < maxAttempts {
				time.Sleep(backoff)
				backoff *= 2
			}
		}
		// fall through to next model in fallback list
	}
	return "", fmt.Errorf("scene %d: pollinations failed all models: %v", sceneIdx, lastErr)
}

// curlDownload shells out to curl. Returns nil on success (HTTP 200 written to outPath).
// We rely on curl's --fail flag to turn 4xx/5xx into a non-zero exit.
func curlDownload(rawURL, outPath string, timeout time.Duration) error {
	maxSecs := int(timeout.Seconds())
	if maxSecs <= 0 {
		maxSecs = 240
	}
	cmd := exec.Command("curl",
		"-sS",
		"--fail",
		"--max-time", fmt.Sprintf("%d", maxSecs),
		"-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
		"-H", "Accept: image/jpeg,image/*,*/*;q=0.8",
		"-H", "Referer: https://pollinations.ai/",
		"-o", outPath,
		rawURL,
	)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("curl: %w (stderr: %s)", err, string(out))
	}
	return nil
}

// GenerateAll runs generations with a concurrency cap.
// Returns paths in scene-index order; on any failure returns the first error encountered.
func (g *ImageGen) GenerateAll(scenes []Scene, concurrency int) ([]string, error) {
	if concurrency <= 0 {
		concurrency = 1
	}
	paths := make([]string, len(scenes))
	errs := make([]error, len(scenes))

	sem := make(chan struct{}, concurrency)
	var wg sync.WaitGroup
	for i := range scenes {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int) {
			defer wg.Done()
			defer func() { <-sem }()
			p, err := g.GenerateOne(scenes[i].Index, scenes[i].ImagePrompt)
			if err != nil {
				errs[i] = err
				return
			}
			paths[i] = p
			fmt.Printf("  [image %2d/%d] %s\n", i+1, len(scenes), filepath.Base(p))
		}(i)
	}
	wg.Wait()

	for _, e := range errs {
		if e != nil {
			return paths, e
		}
	}
	return paths, nil
}
