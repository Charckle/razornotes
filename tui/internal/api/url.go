package api

import (
	"fmt"
	"net/url"
	"strings"
)

// NormalizeBase trims a user-supplied server URL so it is a scheme+host
// (and optional path) with no trailing slash and no /api/v1 suffix.
func NormalizeBase(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", fmt.Errorf("empty url")
	}
	if !strings.Contains(raw, "://") {
		raw = "https://" + raw
	}
	u, err := url.Parse(raw)
	if err != nil {
		return "", fmt.Errorf("invalid url: %w", err)
	}
	if u.Host == "" {
		return "", fmt.Errorf("invalid url: %s", raw)
	}
	u.Fragment = ""
	u.RawQuery = ""
	u.Path = strings.TrimSuffix(strings.TrimRight(u.Path, "/"), "/api/v1")
	u.Path = strings.TrimRight(u.Path, "/")
	out := u.Scheme + "://" + u.Host
	if u.Path != "" && u.Path != "/" {
		out += u.Path
	}
	return out, nil
}

// HostLabel is the short name shown in the TUI header.
func HostLabel(base string) string {
	u, err := url.Parse(base)
	if err != nil || u.Host == "" {
		return base
	}
	return u.Host
}
