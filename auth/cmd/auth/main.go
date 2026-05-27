package main

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"

	"github.com/joho/godotenv"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	yt "google.golang.org/api/youtube/v3"
)

const redirectURI = "http://localhost:8090/callback"

func main() {
	_ = godotenv.Load(".env")

	clientID := os.Getenv("YOUTUBE_CLIENT_ID")
	clientSecret := os.Getenv("YOUTUBE_CLIENT_SECRET")

	scanner := bufio.NewScanner(os.Stdin)

	if clientID == "" {
		fmt.Print("Cole o Client ID: ")
		scanner.Scan()
		clientID = strings.TrimSpace(scanner.Text())
	} else {
		fmt.Printf("Client ID encontrado no .env: %s\n", clientID)
	}

	if clientSecret == "" {
		fmt.Print("Cole o Client Secret: ")
		scanner.Scan()
		clientSecret = strings.TrimSpace(scanner.Text())
	} else {
		fmt.Printf("Client Secret encontrado no .env: %s\n", clientSecret)
	}

	if clientID == "" || clientSecret == "" {
		log.Fatal("Client ID e Client Secret são obrigatórios.")
	}

	cfg := &oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		RedirectURL:  redirectURI,
		Endpoint:     google.Endpoint,
		Scopes:       []string{yt.YoutubeUploadScope, yt.YoutubeReadonlyScope},
	}

	codeCh := make(chan string, 1)
	srv := &http.Server{Addr: ":8090"}

	http.HandleFunc("/callback", func(w http.ResponseWriter, r *http.Request) {
		code := r.URL.Query().Get("code")
		if code == "" {
			http.Error(w, "missing code", http.StatusBadRequest)
			return
		}
		fmt.Fprintln(w, "<h1>Autorização concluída! Pode fechar esta janela.</h1>")
		codeCh <- code
	})

	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Erro no servidor local: %v", err)
		}
	}()

	authURL := cfg.AuthCodeURL("state", oauth2.AccessTypeOffline, oauth2.ApprovalForce)
	fmt.Println("\nAbrindo o browser para você autorizar...")
	fmt.Println("Se não abrir, copie e cole esta URL no browser:")
	fmt.Println(authURL)
	openBrowser(authURL)

	fmt.Println("\nAguardando autorização...")
	code := <-codeCh
	_ = srv.Shutdown(context.Background())

	token, err := cfg.Exchange(context.Background(), code)
	if err != nil {
		log.Fatalf("Erro ao obter token: %v", err)
	}

	fmt.Println("\n✅ Sucesso! Cole estas linhas no seu .env:")
	fmt.Println("─────────────────────────────────────────")
	fmt.Printf("YOUTUBE_CLIENT_ID=%s\n", clientID)
	fmt.Printf("YOUTUBE_CLIENT_SECRET=%s\n", clientSecret)
	fmt.Printf("YOUTUBE_REFRESH_TOKEN=%s\n", token.RefreshToken)
	fmt.Println("─────────────────────────────────────────")
}

func openBrowser(url string) {
	var err error
	switch runtime.GOOS {
	case "windows":
		err = exec.Command("powershell", "-NoProfile", "-Command", "Start-Process", fmt.Sprintf(`"%s"`, url)).Start()
	case "darwin":
		err = exec.Command("open", url).Start()
	default:
		err = exec.Command("xdg-open", url).Start()
	}
	if err != nil {
		log.Printf("Não foi possível abrir o browser automaticamente: %v", err)
	}
}
