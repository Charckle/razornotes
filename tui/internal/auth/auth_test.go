package auth

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadMissingIsEmpty(t *testing.T) {
	s, err := Load(filepath.Join(t.TempDir(), "missing.json"))
	if err != nil {
		t.Fatal(err)
	}
	if len(s.Servers) != 0 || len(s.URLs()) != 0 {
		t.Fatalf("got %+v recents=%v", s.Servers, s.URLs())
	}
}

func TestSaveRoundTripAndMode(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tokens.json")
	s, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	s.Set("https://notes.example.com", Server{Username: "admin", Refresh: "tok"})
	if err := s.Save(); err != nil {
		t.Fatal(err)
	}

	st, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if st.Mode().Perm() != 0o600 {
		t.Fatalf("mode %o, want 0600", st.Mode().Perm())
	}

	got, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	srv, ok := got.Get("https://notes.example.com")
	if !ok || srv.Username != "admin" || srv.Refresh != "tok" {
		t.Fatalf("got %+v ok=%v", srv, ok)
	}
	if urls := got.URLs(); len(urls) != 1 || urls[0] != "https://notes.example.com" {
		t.Fatalf("recents %v", urls)
	}

	got.ForgetTokens("https://notes.example.com")
	if err := got.Save(); err != nil {
		t.Fatal(err)
	}
	got, err = Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := got.Get("https://notes.example.com"); ok {
		t.Fatal("expected tokens cleared")
	}
	if _, ok := got.Lookup("https://notes.example.com"); !ok {
		t.Fatal("url should remain in recents")
	}
}

func TestTouchOrderAndRemove(t *testing.T) {
	s, err := Load(filepath.Join(t.TempDir(), "tokens.json"))
	if err != nil {
		t.Fatal(err)
	}
	s.Touch("https://a.example")
	s.Touch("https://b.example")
	s.Touch("https://a.example")
	urls := s.URLs()
	if len(urls) != 2 || urls[0] != "https://a.example" || urls[1] != "https://b.example" {
		t.Fatalf("got %v", urls)
	}
	s.Remove("https://a.example")
	urls = s.URLs()
	if len(urls) != 1 || urls[0] != "https://b.example" {
		t.Fatalf("got %v", urls)
	}
	if _, ok := s.Lookup("https://a.example"); ok {
		t.Fatal("removed url still present")
	}
}

func TestBackfillRecentsFromOldFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tokens.json")
	raw := []byte(`{"servers":{"https://old.example":{"username":"u","refresh":"r"}}}` + "\n")
	if err := os.WriteFile(path, raw, 0o600); err != nil {
		t.Fatal(err)
	}
	s, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if urls := s.URLs(); len(urls) != 1 || urls[0] != "https://old.example" {
		t.Fatalf("got %v", urls)
	}
}
