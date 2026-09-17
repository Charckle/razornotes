package api

import "testing"

func TestNormalizeBase(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"https://notes.example.com", "https://notes.example.com"},
		{"https://notes.example.com/", "https://notes.example.com"},
		{"https://notes.example.com/api/v1", "https://notes.example.com"},
		{"http://127.0.0.1:5000", "http://127.0.0.1:5000"},
		{"notes.example.com", "https://notes.example.com"},
	}
	for _, c := range cases {
		got, err := NormalizeBase(c.in)
		if err != nil {
			t.Fatalf("%s: %v", c.in, err)
		}
		if got != c.want {
			t.Fatalf("%s: got %s want %s", c.in, got, c.want)
		}
	}
	if _, err := NormalizeBase(""); err == nil {
		t.Fatal("expected error")
	}
}

func TestHostLabel(t *testing.T) {
	if got := HostLabel("https://notes.example.com"); got != "notes.example.com" {
		t.Fatalf("got %s", got)
	}
}
