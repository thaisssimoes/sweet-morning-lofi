package shorts

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Renderer assembles the final vertical short out of per-scene images + narration MP3s plus optional BGM.
type Renderer struct {
	Width        int    // 2160 for 4K vertical
	Height       int    // 3840
	FPS          int    // 30
	CRF          int    // 18 = visually lossless-ish for h264
	AudioBitrate string // "192k"
	WorkDir      string // intermediate per-scene clips
	OutputDir    string // final mp4
}

// RenderScene produces one clip: still image with slow Ken Burns zoom synced to the narration audio.
func (r *Renderer) RenderScene(s Scene) (string, error) {
	if err := os.MkdirAll(r.WorkDir, 0755); err != nil {
		return "", err
	}
	out := filepath.Join(r.WorkDir, fmt.Sprintf("scene_%02d.mp4", s.Index))

	dur := s.DurationSeconds
	if dur <= 0 {
		return "", fmt.Errorf("scene %d has no duration", s.Index)
	}

	// Total output frames: ceil(dur * fps). zoompan uses output frame number `on` to ramp zoom.
	totalFrames := int(dur*float64(r.FPS)) + 1

	// Alternating Ken Burns direction so cuts feel less mechanical.
	// Even scenes: slow zoom in (1.00 -> 1.18). Odd scenes: slow zoom out (1.18 -> 1.00).
	var zoomExpr, xExpr, yExpr string
	xExpr = "iw/2-(iw/zoom/2)"
	yExpr = "ih/2-(ih/zoom/2)"
	if s.Index%2 == 0 {
		zoomExpr = fmt.Sprintf("min(1.0+0.18*on/%d,1.18)", totalFrames)
	} else {
		zoomExpr = fmt.Sprintf("max(1.18-0.18*on/%d,1.0)", totalFrames)
	}

	// No pre-upscale: source images are already at output resolution. Zoompan crops
	// directly from the source and only ever "downsamples" (or 1:1) within its crop window,
	// so the image stays sharp.
	vf := fmt.Sprintf(
		"zoompan=z='%s':x='%s':y='%s':d=1:s=%dx%d:fps=%d,format=yuv420p",
		zoomExpr, xExpr, yExpr,
		r.Width, r.Height, r.FPS,
	)

	args := []string{
		"-y",
		"-loop", "1",
		"-framerate", fmt.Sprintf("%d", r.FPS),
		"-t", fmt.Sprintf("%.3f", dur),
		"-i", s.ImagePath,
		"-i", s.AudioPath,
		"-filter_complex", fmt.Sprintf("[0:v]%s[v]", vf),
		"-map", "[v]",
		"-map", "1:a:0",
		"-c:v", "libx264",
		"-preset", "medium",
		"-crf", fmt.Sprintf("%d", r.CRF),
		"-pix_fmt", "yuv420p",
		"-c:a", "aac",
		"-b:a", r.AudioBitrate,
		"-shortest",
		out,
	}
	cmd := exec.Command("ffmpeg", args...)
	if outBytes, err := cmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("scene %d ffmpeg failed: %w\n%s", s.Index, err, tailLines(string(outBytes), 30))
	}
	return out, nil
}

// Assemble concatenates per-scene clips and mixes in background music at low volume.
// bgmPath may be empty — in that case the narration alone is the audio.
func (r *Renderer) Assemble(scenes []Scene, scenePaths []string, bgmPath, outName string) (string, error) {
	if err := os.MkdirAll(r.OutputDir, 0755); err != nil {
		return "", err
	}

	// concat demuxer manifest
	manifest := filepath.Join(r.WorkDir, "concat.txt")
	var b strings.Builder
	for _, p := range scenePaths {
		// concat demuxer needs forward slashes and escaped single quotes; we just wrap path in '' since none contain quotes
		abs, err := filepath.Abs(p)
		if err != nil {
			return "", err
		}
		fmt.Fprintf(&b, "file '%s'\n", filepath.ToSlash(abs))
	}
	if err := os.WriteFile(manifest, []byte(b.String()), 0644); err != nil {
		return "", err
	}

	out := filepath.Join(r.OutputDir, outName)

	args := []string{
		"-y",
		"-f", "concat",
		"-safe", "0",
		"-i", manifest,
	}
	if bgmPath != "" {
		args = append(args, "-stream_loop", "-1", "-i", bgmPath)
	}

	if bgmPath != "" {
		// Mix narration with BGM, BGM at ~12%, fade BGM in/out, clip to narration length.
		filter := "[1:a]volume=0.12,afade=t=in:st=0:d=1.5[bgm];" +
			"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2,afade=t=out:st=" +
			fmt.Sprintf("%.2f", totalDuration(scenes)-1.5) +
			":d=1.5[aout]"
		args = append(args,
			"-filter_complex", filter,
			"-map", "0:v",
			"-map", "[aout]",
		)
	} else {
		args = append(args,
			"-map", "0:v",
			"-map", "0:a",
		)
	}

	args = append(args,
		"-c:v", "copy",
		"-c:a", "aac",
		"-b:a", r.AudioBitrate,
		"-movflags", "+faststart",
		out,
	)

	cmd := exec.Command("ffmpeg", args...)
	if outBytes, err := cmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("assemble ffmpeg failed: %w\n%s", err, tailLines(string(outBytes), 40))
	}
	return out, nil
}

func totalDuration(scenes []Scene) float64 {
	var t float64
	for _, s := range scenes {
		t += s.DurationSeconds
	}
	return t
}

func tailLines(s string, n int) string {
	lines := strings.Split(s, "\n")
	if len(lines) <= n {
		return s
	}
	return strings.Join(lines[len(lines)-n:], "\n")
}
