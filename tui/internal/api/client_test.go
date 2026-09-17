package api

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestLoginAndNotes(t *testing.T) {
	var authed int
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == "POST" && r.URL.Path == "/api/v1/login":
			if err := r.ParseForm(); err != nil {
				t.Fatal(err)
			}
			if r.Form.Get("username") != "admin" || r.Form.Get("password") != "banana" {
				http.Error(w, `{"message":"bad login"}`, 404)
				return
			}
			json.NewEncoder(w).Encode(map[string]string{
				"access": "acc-1", "refresh": "ref-1", "username": "admin",
			})
		case r.URL.Path == "/api/v1/notes/pinned":
			if r.Header.Get("Authorization") != "Bearer acc-1" {
				http.Error(w, `{"msg":"missing"}`, 401)
				return
			}
			authed++
			io.WriteString(w, `[{"id":1,"title":"Pin","text":"hi","pinned":true}]`)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(srv.Close)

	c := NewClient(srv.URL, srv.Client())
	if err := c.Login("admin", "banana"); err != nil {
		t.Fatal(err)
	}
	if c.RefreshToken() != "ref-1" || c.Username() != "admin" {
		t.Fatalf("tokens %+v %s", c.RefreshToken(), c.Username())
	}
	notes, err := c.Pinned()
	if err != nil {
		t.Fatal(err)
	}
	if len(notes) != 1 || notes[0].Title != "Pin" || !notes[0].Pinned {
		t.Fatalf("got %+v", notes)
	}
	if authed != 1 {
		t.Fatalf("authed %d", authed)
	}
}

func TestRefreshRetry(t *testing.T) {
	accessOK := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/refresh":
			if r.Header.Get("Authorization") != "Bearer ref-old" {
				http.Error(w, `{"msg":"no"}`, 401)
				return
			}
			json.NewEncoder(w).Encode(map[string]string{"access": "acc-new"})
		case "/api/v1/notes/index":
			if r.Header.Get("Authorization") != "Bearer acc-new" {
				http.Error(w, `{"msg":"expired"}`, 401)
				return
			}
			accessOK = true
			io.WriteString(w, `[]`)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(srv.Close)

	c := NewClient(srv.URL, srv.Client())
	c.SetRefresh("ref-old", "admin")
	notes, err := c.Index()
	if err != nil {
		t.Fatal(err)
	}
	if notes == nil || !accessOK {
		t.Fatalf("notes=%v accessOK=%v", notes, accessOK)
	}
}

func TestSearchOrderAndSnippets(t *testing.T) {
	raw := []byte(`{"12":["Alpha","a <b>hit</b> here"],"3":["Beta","plain"]}`)
	hits, err := parseSearch(raw)
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 2 {
		t.Fatalf("len %d", len(hits))
	}
	if hits[0].ID != 12 || hits[0].Title != "Alpha" || hits[0].Snippet != "a hit here" {
		t.Fatalf("first %+v", hits[0])
	}
	if hits[1].ID != 3 || hits[1].Title != "Beta" {
		t.Fatalf("second %+v", hits[1])
	}
}

func TestClipboard(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer a" {
			http.Error(w, `{"msg":"no"}`, 401)
			return
		}
		io.WriteString(w, `{"clipboard":"secret"}`)
	}))
	t.Cleanup(srv.Close)
	c := NewClient(srv.URL, srv.Client())
	c.setAccess("a", "", "")
	got, err := c.Clipboard()
	if err != nil {
		t.Fatal(err)
	}
	if got != "secret" {
		t.Fatalf("got %q", got)
	}
}

func TestUnauthorizedError(t *testing.T) {
	err := &Error{Status: 401, Message: "no"}
	if !err.Unauthorized() || !strings.Contains(err.Error(), "no") {
		t.Fatalf("%v", err)
	}
}

func TestPing(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			http.NotFound(w, r)
			return
		}
		w.WriteHeader(500)
		io.WriteString(w, `{"status":"not healthy"}`)
	}))
	t.Cleanup(srv.Close)
	c := NewClient(srv.URL, srv.Client())
	if err := c.Ping(); err != nil {
		t.Fatal(err)
	}
}
