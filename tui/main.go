package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"rnotes/internal/api"
	"rnotes/internal/auth"
	"rnotes/internal/tui"
)

const usage = `rnotes - read-only Razor Notes TUI

Usage:
  rnotes              Pick a saved server, or enter a URL
  rnotes <url>        Open that server (also set by RNOTES_URL)

Environment:
  RNOTES_URL          Skip the picker and open this server
  RNOTES_TOKEN_FILE   Override ~/.config/rnotes/tokens.json

Notes stay on the server. Server URLs and a refresh token are stored
locally (mode 0600). The password is never stored.
`

func main() {
	arg, hasArg := "", len(os.Args) > 1
	if hasArg {
		arg = os.Args[1]
		switch arg {
		case "-h", "--help", "help":
			fmt.Fprint(os.Stdout, usage)
			return
		}
	}

	raw := arg
	if raw == "" {
		raw = os.Getenv("RNOTES_URL")
	}
	var startURL string
	if raw != "" {
		base, err := api.NormalizeBase(raw)
		if err != nil {
			fatal(err)
		}
		startURL = base
	}

	tokenPath := os.Getenv("RNOTES_TOKEN_FILE")
	if tokenPath == "" {
		var err error
		tokenPath, err = auth.Path()
		if err != nil {
			fatal(err)
		}
	}
	store, err := auth.Load(tokenPath)
	if err != nil {
		fatal(err)
	}

	m := tui.New(tui.Config{
		StartURL: startURL,
		Store:    store,
	})
	p := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fatal(err)
	}
}

func fatal(err error) {
	fmt.Fprintf(os.Stderr, "rnotes: %v\n", err)
	os.Exit(1)
}
