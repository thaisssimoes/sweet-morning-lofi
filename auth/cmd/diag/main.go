package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/option"
	yt "google.golang.org/api/youtube/v3"
)

const suspectVideoID = "9lL1fzJhL8k"

func main() {
	_ = godotenv.Load(".env")

	clientID := os.Getenv("YOUTUBE_CLIENT_ID")
	clientSecret := os.Getenv("YOUTUBE_CLIENT_SECRET")
	refreshToken := os.Getenv("YOUTUBE_REFRESH_TOKEN")

	if clientID == "" || clientSecret == "" || refreshToken == "" {
		log.Fatal("YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET ou YOUTUBE_REFRESH_TOKEN ausentes no .env")
	}

	cfg := &oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		Endpoint:     google.Endpoint,
	}
	token := &oauth2.Token{
		RefreshToken: refreshToken,
		Expiry:       time.Now().Add(-time.Hour),
	}
	ctx := context.Background()
	svc, err := yt.NewService(ctx, option.WithTokenSource(cfg.TokenSource(ctx, token)))
	if err != nil {
		log.Fatalf("criando service: %v", err)
	}

	fmt.Println("── Canal(is) que essas credenciais controlam ──")
	chResp, err := svc.Channels.List([]string{"id", "snippet", "status"}).Mine(true).Do()
	if err != nil {
		log.Fatalf("channels.list: %v", err)
	}
	if len(chResp.Items) == 0 {
		fmt.Println("⚠️  Nenhum canal encontrado. A conta Google autenticada não tem canal YouTube criado.")
	}
	for _, ch := range chResp.Items {
		fmt.Printf("  ID:        %s\n", ch.Id)
		fmt.Printf("  Título:    %s\n", ch.Snippet.Title)
		fmt.Printf("  Descrição: %s\n", ch.Snippet.Description)
		fmt.Printf("  País:      %s\n", ch.Snippet.Country)
		fmt.Printf("  URL:       https://www.youtube.com/channel/%s\n", ch.Id)
		fmt.Println()
	}

	fmt.Printf("── Vídeo %s ──\n", suspectVideoID)
	vResp, err := svc.Videos.List([]string{"id", "snippet", "status"}).Id(suspectVideoID).Do()
	if err != nil {
		log.Fatalf("videos.list: %v", err)
	}
	if len(vResp.Items) == 0 {
		fmt.Println("⚠️  Vídeo não encontrado (ou não pertence às credenciais).")
		return
	}
	for _, v := range vResp.Items {
		fmt.Printf("  Título:         %s\n", v.Snippet.Title)
		fmt.Printf("  Canal dono ID:  %s\n", v.Snippet.ChannelId)
		fmt.Printf("  Canal dono:     %s\n", v.Snippet.ChannelTitle)
		fmt.Printf("  Privacy:        %s\n", v.Status.PrivacyStatus)
		fmt.Printf("  PublishAt:      %s\n", v.Status.PublishAt)
		fmt.Printf("  UploadStatus:   %s\n", v.Status.UploadStatus)
		fmt.Printf("  RejectionReason:%s\n", v.Status.RejectionReason)
		fmt.Printf("  FailureReason:  %s\n", v.Status.FailureReason)
		fmt.Printf("  Publicado em:   %s\n", v.Snippet.PublishedAt)
	}
}
