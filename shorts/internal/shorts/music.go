package shorts

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// MusicCandidate is a royalty-free background track we can try to fetch.
// Order matters — first one that succeeds wins.
type MusicCandidate struct {
	URL     string
	License string
	Title   string
}

// EpicTracks is a small ordered list of royalty-free orchestral / cinematic tracks.
// All Kevin MacLeod — CC BY 3.0 / 4.0, requires attribution in video description.
var EpicTracks = []MusicCandidate{
	{
		URL:     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Descent.mp3",
		License: "CC BY 4.0 — Kevin MacLeod (incompetech.com)",
		Title:   "The Descent",
	},
	{
		URL:     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hitman.mp3",
		License: "CC BY 4.0 — Kevin MacLeod (incompetech.com)",
		Title:   "Hitman",
	},
	{
		URL:     "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Long%20Note%20Three.mp3",
		License: "CC BY 4.0 — Kevin MacLeod (incompetech.com)",
		Title:   "Long Note Three",
	},
}

// DownloadFirstWorking tries each candidate until one downloads successfully.
// Returns the local path, license string, and title. If none succeed, returns "".
func DownloadFirstWorking(outDir string) (string, string, string) {
	if err := os.MkdirAll(outDir, 0755); err != nil {
		return "", "", ""
	}
	client := &http.Client{Timeout: 60 * time.Second}
	for _, c := range EpicTracks {
		req, err := http.NewRequest("GET", c.URL, nil)
		if err != nil {
			continue
		}
		req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; shorts-poc/0.1)")
		resp, err := client.Do(req)
		if err != nil {
			fmt.Printf("  music: %s failed: %v\n", c.Title, err)
			continue
		}
		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			fmt.Printf("  music: %s status %d\n", c.Title, resp.StatusCode)
			continue
		}
		out := filepath.Join(outDir, "bgm.mp3")
		f, err := os.Create(out)
		if err != nil {
			resp.Body.Close()
			continue
		}
		_, err = io.Copy(f, resp.Body)
		f.Close()
		resp.Body.Close()
		if err != nil {
			os.Remove(out)
			continue
		}
		fmt.Printf("  music: downloaded %q (%s)\n", c.Title, c.License)
		return out, c.License, c.Title
	}
	return "", "", ""
}
