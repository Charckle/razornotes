package auth

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

const (
	appName  = "rnotes"
	fileName = "tokens.json"
	maxKeep  = 15
)

// Server is the persisted session for one Razor Notes URL.
type Server struct {
	Username string `json:"username"`
	Refresh  string `json:"refresh"`
}

// Store is ~/.config/rnotes/tokens.json (mode 0600). It never holds
// passwords or access tokens — only server URLs and refresh JWTs.
type Store struct {
	Recents []string          `json:"recents"`
	Servers map[string]Server `json:"servers"`
	path    string
}

// Path is RNOTES_TOKEN_FILE, or ~/.config/rnotes/tokens.json.
func Path() (string, error) {
	if p := os.Getenv("RNOTES_TOKEN_FILE"); p != "" {
		return p, nil
	}
	dir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, appName, fileName), nil
}

// Load reads a token file. A missing file is an empty store, not an error.
func Load(path string) (*Store, error) {
	s := &Store{path: path, Recents: []string{}, Servers: map[string]Server{}}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return s, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(data, s); err != nil {
		return nil, fmt.Errorf("tokens: %w", err)
	}
	if s.Servers == nil {
		s.Servers = map[string]Server{}
	}
	if s.Recents == nil {
		s.Recents = []string{}
	}
	s.backfillRecents()
	s.path = path
	return s, nil
}

func (s *Store) backfillRecents() {
	if len(s.Recents) > 0 || len(s.Servers) == 0 {
		return
	}
	for u := range s.Servers {
		s.Recents = append(s.Recents, u)
	}
}

// Save writes the store with mode 0600.
func (s *Store) Save() error {
	if s.path == "" {
		return fmt.Errorf("tokens: no path")
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return err
	}
	if s.Servers == nil {
		s.Servers = map[string]Server{}
	}
	if s.Recents == nil {
		s.Recents = []string{}
	}
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	if err := os.Chmod(tmp, 0o600); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	return os.Rename(tmp, s.path)
}

// URLs is the recents list, most recent first.
func (s *Store) URLs() []string {
	if s == nil || s.Recents == nil {
		return nil
	}
	out := make([]string, len(s.Recents))
	copy(out, s.Recents)
	return out
}

// Lookup returns any saved record for baseURL, even without a refresh token.
func (s *Store) Lookup(baseURL string) (Server, bool) {
	if s == nil || s.Servers == nil {
		return Server{}, false
	}
	srv, ok := s.Servers[baseURL]
	return srv, ok
}

// Get returns the saved session for baseURL when a refresh token is present.
func (s *Store) Get(baseURL string) (Server, bool) {
	srv, ok := s.Lookup(baseURL)
	return srv, ok && srv.Refresh != ""
}

// Touch records baseURL as most-recent. Call Save afterwards.
func (s *Store) Touch(baseURL string) {
	if baseURL == "" {
		return
	}
	if s.Servers == nil {
		s.Servers = map[string]Server{}
	}
	out := make([]string, 0, len(s.Recents)+1)
	out = append(out, baseURL)
	for _, u := range s.Recents {
		if u != baseURL {
			out = append(out, u)
		}
	}
	if len(out) > maxKeep {
		for _, u := range out[maxKeep:] {
			delete(s.Servers, u)
		}
		out = out[:maxKeep]
	}
	s.Recents = out
	if _, ok := s.Servers[baseURL]; !ok {
		s.Servers[baseURL] = Server{}
	}
}

// Set stores a session for baseURL and marks it most recent. Call Save afterwards.
func (s *Store) Set(baseURL string, srv Server) {
	s.Touch(baseURL)
	s.Servers[baseURL] = srv
}

// ForgetTokens drops the refresh JWT but keeps the URL in recents.
func (s *Store) ForgetTokens(baseURL string) {
	if s.Servers == nil {
		return
	}
	srv, ok := s.Servers[baseURL]
	if !ok {
		return
	}
	srv.Refresh = ""
	s.Servers[baseURL] = srv
}

// Remove drops a server from recents and tokens. Call Save afterwards.
func (s *Store) Remove(baseURL string) {
	if s.Servers != nil {
		delete(s.Servers, baseURL)
	}
	out := s.Recents[:0]
	for _, u := range s.Recents {
		if u != baseURL {
			out = append(out, u)
		}
	}
	s.Recents = out
}
