package shorts

import (
	"fmt"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// TTS wraps edge-tts (Python package, installed via pip --user).
// We call it as a CLI subprocess: edge-tts --voice ... --text ... --write-media out.mp3
type TTS struct {
	Voice     string // e.g. "pt-BR-AntonioNeural"
	Rate      string // e.g. "+0%" or "-5%" — slower reads better for documentary
	OutputDir string
}

// Synth generates an MP3 for the given narration and returns the file path plus its duration in seconds.
func (t *TTS) Synth(sceneIdx int, narration string) (string, float64, error) {
	outPath := filepath.Join(t.OutputDir, fmt.Sprintf("scene_%02d.mp3", sceneIdx))

	args := []string{
		"--voice", t.Voice,
		"--text", narration,
		"--write-media", outPath,
	}
	if r := strings.TrimSpace(t.Rate); r != "" {
		// Use --rate=VALUE form so leading '-' (e.g. "-5%") isn't parsed as a flag.
		args = append(args, "--rate="+r)
	}

	cmd := exec.Command("edge-tts", args...)
	if out, err := cmd.CombinedOutput(); err != nil {
		return "", 0, fmt.Errorf("edge-tts failed for scene %d: %w\n%s", sceneIdx, err, string(out))
	}

	dur, err := ProbeAudioDuration(outPath)
	if err != nil {
		return "", 0, fmt.Errorf("probing duration for scene %d: %w", sceneIdx, err)
	}
	return outPath, dur, nil
}

// ProbeAudioDuration uses ffprobe to read the audio length in seconds.
func ProbeAudioDuration(path string) (float64, error) {
	cmd := exec.Command("ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		path,
	)
	out, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("ffprobe: %w", err)
	}
	s := strings.TrimSpace(string(out))
	d, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, fmt.Errorf("parsing duration %q: %w", s, err)
	}
	return d, nil
}
