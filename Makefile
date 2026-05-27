.PHONY: lofi shorts-build auth-build auth-diag deps-shorts deps-auth

# ── lofi (Python) ──────────────────────────────────────────────────────────────
lofi:
	cd lofi && python generate_videos.py

lofi-upload:
	cd lofi && python generate_videos.py --upload-from $(from)

# ── shorts (Go) ────────────────────────────────────────────────────────────────
shorts-build:
	cd shorts && go build -o shorts.exe .

shorts-run: shorts-build
	cd shorts && ./shorts.exe

deps-shorts:
	cd shorts && go mod tidy

# ── auth (Go) ──────────────────────────────────────────────────────────────────
auth-build:
	cd auth && go build -o auth.exe ./cmd/auth && go build -o diag.exe ./cmd/diag

auth-run:
	cd auth && go build -o auth.exe ./cmd/auth && ./auth.exe

auth-diag:
	cd auth && go build -o diag.exe ./cmd/diag && ./diag.exe

deps-auth:
	cd auth && go mod tidy
