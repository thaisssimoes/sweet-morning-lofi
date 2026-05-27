package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"shorts/internal/shorts"
)

func main() {
	// Final video matches source image resolution — upscaling Pollinations 1080p output to
	// 4K via lanczos only softens it without adding real detail. YouTube Shorts native is 1080x1920.
	width := flag.Int("w", 1080, "final video width (Shorts native = 1080)")
	height := flag.Int("h", 1920, "final video height (Shorts native = 1920)")
	imgWidth := flag.Int("img-w", 1080, "source image width (Pollinations request)")
	imgHeight := flag.Int("img-h", 1920, "source image height (Pollinations request)")
	fps := flag.Int("fps", 30, "output frames per second")
	concurrency := flag.Int("c", 1, "image generation concurrency (1 = strict serial to avoid 402)")
	spacingSec := flag.Float64("spacing", 8, "seconds between Pollinations requests (rate-limit pacing)")
	voice := flag.String("voice", "pt-BR-AntonioNeural", "edge-tts voice id")
	rate := flag.String("rate", "-5%", "edge-tts rate adjustment (e.g. -5% for slightly slower documentary read)")
	noMusic := flag.Bool("no-music", false, "skip background music")
	workFlag := flag.String("work", "", "reuse an existing work dir (resumes: skips audio/image/bgm files already present)")
	flag.Parse()

	root, err := os.Getwd()
	if err != nil {
		fatal("getwd: %v", err)
	}

	stamp := time.Now().Format("20060102_150405")
	var workDir string
	if *workFlag != "" {
		workDir = *workFlag
		if !filepath.IsAbs(workDir) {
			workDir = filepath.Join(root, workDir)
		}
	} else {
		workDir = filepath.Join(root, "assets", "shorts", "kursk_"+stamp)
	}
	outDir := filepath.Join(root, "output", "shorts")
	imgDir := filepath.Join(workDir, "images")
	audioDir := filepath.Join(workDir, "audio")
	bgmDir := filepath.Join(workDir, "bgm")
	clipDir := filepath.Join(workDir, "clips")

	for _, d := range []string{workDir, outDir, imgDir, audioDir, bgmDir, clipDir} {
		if err := os.MkdirAll(d, 0755); err != nil {
			fatal("mkdir %s: %v", d, err)
		}
	}

	fmt.Printf("== Kursk shorts POC ==\n")
	fmt.Printf("work dir: %s\n", workDir)
	fmt.Printf("output:   %s\n", outDir)

	scenes := shorts.KurskScenes()
	fmt.Printf("scenes:   %d\n\n", len(scenes))

	// --- 1) TTS sequentially (skip per scene if mp3 already exists) -------
	fmt.Println("[1/4] Generating narration with edge-tts...")
	tts := &shorts.TTS{Voice: *voice, Rate: *rate, OutputDir: audioDir}
	var ttsTotalDur float64
	for i := range scenes {
		expected := filepath.Join(audioDir, fmt.Sprintf("scene_%02d.mp3", scenes[i].Index))
		if st, err := os.Stat(expected); err == nil && st.Size() > 0 {
			dur, perr := shorts.ProbeAudioDuration(expected)
			if perr == nil {
				scenes[i].AudioPath = expected
				scenes[i].DurationSeconds = dur
				ttsTotalDur += dur
				fmt.Printf("  [voice %2d/%d] %.2fs (cached)\n", i+1, len(scenes), dur)
				continue
			}
		}
		t0 := time.Now()
		path, dur, err := tts.Synth(scenes[i].Index, scenes[i].Narration)
		if err != nil {
			fatal("tts scene %d: %v", scenes[i].Index, err)
		}
		scenes[i].AudioPath = path
		scenes[i].DurationSeconds = dur
		ttsTotalDur += dur
		fmt.Printf("  [voice %2d/%d] %.2fs (took %v)\n", i+1, len(scenes), dur, time.Since(t0).Round(time.Millisecond))
	}
	fmt.Printf("  total narration: %.1fs (%.2f min)\n\n", ttsTotalDur, ttsTotalDur/60)

	// --- 2) Images (parallel) + BGM (parallel) ----------------------------
	fmt.Println("[2/4] Generating images (Pollinations, flux→turbo fallback) + fetching BGM...")
	gen := &shorts.ImageGen{
		Width: *imgWidth, Height: *imgHeight,
		OutputDir:   imgDir,
		Seed:        1943,
		Timeout:     240 * time.Second,
		MinSpacing:  time.Duration(*spacingSec * float64(time.Second)),
		MaxAttempts: 5,
		Models:      []string{"flux", "turbo"},
	}

	// Filter out scenes whose images already exist on disk
	pending := make([]shorts.Scene, 0, len(scenes))
	for i := range scenes {
		expected := filepath.Join(imgDir, fmt.Sprintf("scene_%02d.jpg", scenes[i].Index))
		if st, err := os.Stat(expected); err == nil && st.Size() > 1024 {
			scenes[i].ImagePath = expected
			fmt.Printf("  [image %2d/%d] %s (cached)\n", i+1, len(scenes), filepath.Base(expected))
			continue
		}
		pending = append(pending, scenes[i])
	}

	var imgErr error
	var bgmPath, bgmLicense, bgmTitle string
	var wg sync.WaitGroup
	if len(pending) > 0 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, imgErr = gen.GenerateAll(pending, *concurrency)
		}()
	}
	wg.Add(1)
	go func() {
		defer wg.Done()
		if *noMusic {
			return
		}
		// Skip download if already cached
		cached := filepath.Join(bgmDir, "bgm.mp3")
		if st, err := os.Stat(cached); err == nil && st.Size() > 1024 {
			bgmPath = cached
			bgmTitle = "(cached)"
			bgmLicense = "(see previous run)"
			fmt.Printf("  music: cached %s\n", cached)
			return
		}
		bgmPath, bgmLicense, bgmTitle = shorts.DownloadFirstWorking(bgmDir)
	}()
	wg.Wait()
	if imgErr != nil {
		fatal("image generation: %v", imgErr)
	}
	// Re-resolve image paths for pending scenes
	for i := range scenes {
		if scenes[i].ImagePath != "" {
			continue
		}
		scenes[i].ImagePath = filepath.Join(imgDir, fmt.Sprintf("scene_%02d.jpg", scenes[i].Index))
	}
	if bgmPath == "" && !*noMusic {
		fmt.Println("  warning: no BGM track could be downloaded, continuing without music")
	} else if bgmPath != "" {
		fmt.Printf("  bgm: %s\n", bgmPath)
	}
	fmt.Println()

	// --- 3) Per-scene clips ------------------------------------------------
	fmt.Println("[3/4] Rendering per-scene clips with Ken Burns zoom + upscale to 4K...")
	r := &shorts.Renderer{
		Width: *width, Height: *height,
		FPS: *fps, CRF: 18,
		AudioBitrate: "192k",
		WorkDir:      clipDir,
		OutputDir:    outDir,
	}
	clipPaths := make([]string, len(scenes))
	for i := range scenes {
		t0 := time.Now()
		p, err := r.RenderScene(scenes[i])
		if err != nil {
			fatal("render scene %d: %v", i, err)
		}
		clipPaths[i] = p
		fmt.Printf("  [clip  %2d/%d] %s (%v)\n", i+1, len(scenes), filepath.Base(p), time.Since(t0).Round(time.Millisecond))
	}
	fmt.Println()

	// --- 4) Assemble final -------------------------------------------------
	fmt.Println("[4/4] Assembling final short...")
	outName := "kursk_" + filepath.Base(workDir) + ".mp4"
	finalPath, err := r.Assemble(scenes, clipPaths, bgmPath, outName)
	if err != nil {
		fatal("assemble: %v", err)
	}
	fmt.Printf("  final: %s\n\n", finalPath)

	fmt.Println("== DONE ==")
	fmt.Printf("Video: %s\n", finalPath)
	fmt.Printf("Total narration: %.1fs (~%.1f min)\n", ttsTotalDur, ttsTotalDur/60)
	if bgmTitle != "" {
		fmt.Printf("Music: %q — %s (attribute in description)\n", bgmTitle, bgmLicense)
	}
}

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "FATAL: "+format+"\n", args...)
	os.Exit(1)
}
