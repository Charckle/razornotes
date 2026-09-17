package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	apiPrefix = "/api/v1"
	timeout   = 12 * time.Second
)

var htmlTag = regexp.MustCompile(`<[^>]+>`)

// Error is a non-2xx API response.
type Error struct {
	Status  int
	Message string
}

func (e *Error) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return fmt.Sprintf("HTTP %d", e.Status)
}

// Unauthorized reports a dead session (login required).
func (e *Error) Unauthorized() bool {
	return e.Status == 401 || e.Status == 422
}

// Note is a Razor Notes API note.
type Note struct {
	ID       int    `json:"id"`
	Title    string `json:"title"`
	Text     string `json:"text"`
	Preview  string `json:"preview"`
	Pinned   bool   `json:"pinned"`
	Relevant bool   `json:"relevant"`
	DateMod  string `json:"date_mod"`
	VHash    string `json:"v_hash"`
	Active   bool   `json:"active"`
	NoteType int    `json:"note_type"`
}

// PreviewText is the list-row extra: API preview, else truncated body.
func (n Note) PreviewText() string {
	s := strings.TrimSpace(n.Preview)
	if s == "" {
		s = strings.TrimSpace(n.Text)
	}
	s = strings.Join(strings.Fields(s), " ")
	return s
}

// SearchHit is one Whoosh result from POST /search.
type SearchHit struct {
	ID      int
	Title   string
	Snippet string
}

type tokenResponse struct {
	Access   string `json:"access"`
	Refresh  string `json:"refresh"`
	Username string `json:"username"`
}

type clipboardResponse struct {
	Clipboard string `json:"clipboard"`
}

type msgBody struct {
	Message string `json:"message"`
	Msg     string `json:"msg"`
}

// Client talks to /api/v1. Access tokens stay in memory; refresh is
// supplied by the caller and persisted outside this package.
type Client struct {
	BaseURL string
	HTTP    *http.Client

	mu       sync.Mutex
	access   string
	refresh  string
	username string
}

// NewClient uses a 12s timeout unless httpClient is set.
func NewClient(baseURL string, httpClient *http.Client) *Client {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: timeout}
	}
	return &Client{BaseURL: strings.TrimRight(baseURL, "/"), HTTP: httpClient}
}

func (c *Client) SetRefresh(refresh, username string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.refresh = refresh
	c.username = username
	c.access = ""
}

func (c *Client) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.access = ""
	c.refresh = ""
	c.username = ""
}

// Ping checks that the server answers. /health returning anything (even
// 500) still counts — the host is reachable.
func (c *Client) Ping() error {
	req, err := http.NewRequest(http.MethodGet, c.BaseURL+"/health", nil)
	if err != nil {
		return err
	}
	res, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	_, _ = io.Copy(io.Discard, res.Body)
	return nil
}

func (c *Client) RefreshToken() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.refresh
}

func (c *Client) Username() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.username
}

func (c *Client) setAccess(access, refresh, username string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if access != "" {
		c.access = access
	}
	if refresh != "" {
		c.refresh = refresh
	}
	if username != "" {
		c.username = username
	}
}

func (c *Client) apiURL(path string) string {
	return c.BaseURL + apiPrefix + path
}

// Login posts username/password and stores both tokens.
func (c *Client) Login(username, password string) error {
	form := url.Values{
		"username": {username},
		"password": {password},
	}
	req, err := http.NewRequest(http.MethodPost, c.apiURL("/login"), strings.NewReader(form.Encode()))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	var tok tokenResponse
	if err := c.do(req, &tok, false); err != nil {
		return err
	}
	if tok.Access == "" || tok.Refresh == "" {
		return fmt.Errorf("login: missing tokens")
	}
	c.setAccess(tok.Access, tok.Refresh, firstNonEmpty(tok.Username, username))
	return nil
}

// Refresh exchanges the refresh JWT for a new access token.
func (c *Client) Refresh() error {
	c.mu.Lock()
	refresh := c.refresh
	c.mu.Unlock()
	if refresh == "" {
		return &Error{Status: 401, Message: "not signed in"}
	}
	req, err := http.NewRequest(http.MethodPost, c.apiURL("/refresh"), nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+refresh)
	var tok tokenResponse
	if err := c.do(req, &tok, false); err != nil {
		return err
	}
	if tok.Access == "" {
		return fmt.Errorf("refresh: missing access token")
	}
	c.setAccess(tok.Access, "", tok.Username)
	return nil
}

func (c *Client) Pinned() ([]Note, error) {
	var notes []Note
	err := c.get("/notes/pinned", &notes)
	return notes, err
}

func (c *Client) Index() ([]Note, error) {
	var notes []Note
	err := c.get("/notes/index", &notes)
	return notes, err
}

func (c *Client) Meta() ([]Note, error) {
	var notes []Note
	err := c.get("/notes/meta", &notes)
	return notes, err
}

func (c *Client) Note(id int) (Note, error) {
	var n Note
	err := c.get("/note/"+strconv.Itoa(id), &n)
	return n, err
}

func (c *Client) Clipboard() (string, error) {
	var body clipboardResponse
	if err := c.get("/clipboard", &body); err != nil {
		return "", err
	}
	return body.Clipboard, nil
}

func (c *Client) Search(key string) ([]SearchHit, error) {
	payload, err := json.Marshal(map[string]string{"key": key})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequest(http.MethodPost, c.apiURL("/search"), bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.GetBody = func() (io.ReadCloser, error) {
		return io.NopCloser(bytes.NewReader(payload)), nil
	}
	var raw json.RawMessage
	if err := c.doAuth(req, &raw); err != nil {
		return nil, err
	}
	return parseSearch(raw)
}

func (c *Client) get(path string, out any) error {
	req, err := http.NewRequest(http.MethodGet, c.apiURL(path), nil)
	if err != nil {
		return err
	}
	return c.doAuth(req, out)
}

func (c *Client) doAuth(req *http.Request, out any) error {
	if err := c.do(req, out, true); err == nil {
		return nil
	} else if ae, ok := err.(*Error); !ok || !ae.Unauthorized() {
		return err
	}
	if err := c.Refresh(); err != nil {
		return err
	}
	// Rebuild a GET/POST with the same URL and a fresh body if we had one.
	retry, err := cloneRequest(req)
	if err != nil {
		return err
	}
	return c.do(retry, out, true)
}

func (c *Client) do(req *http.Request, out any, withAccess bool) error {
	if withAccess {
		c.mu.Lock()
		access := c.access
		c.mu.Unlock()
		if access != "" {
			req.Header.Set("Authorization", "Bearer "+access)
		}
	}
	res, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	data, err := io.ReadAll(res.Body)
	if err != nil {
		return err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		return &Error{Status: res.StatusCode, Message: parseMsg(data)}
	}
	if out == nil || len(data) == 0 || string(data) == "null" {
		return nil
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("decode: %w", err)
	}
	return nil
}

func cloneRequest(req *http.Request) (*http.Request, error) {
	var body io.Reader
	if req.GetBody != nil {
		rc, err := req.GetBody()
		if err != nil {
			return nil, err
		}
		body = rc
	} else if req.Body == nil || req.Body == http.NoBody {
		body = nil
	} else {
		return nil, fmt.Errorf("cannot retry request")
	}
	retry, err := http.NewRequest(req.Method, req.URL.String(), body)
	if err != nil {
		return nil, err
	}
	retry.Header = req.Header.Clone()
	retry.Header.Del("Authorization")
	return retry, nil
}

func parseMsg(data []byte) string {
	var m msgBody
	if err := json.Unmarshal(data, &m); err == nil {
		if m.Message != "" {
			return m.Message
		}
		if m.Msg != "" {
			return m.Msg
		}
	}
	s := strings.TrimSpace(string(data))
	if s == "" {
		return ""
	}
	return s
}

func parseSearch(raw json.RawMessage) ([]SearchHit, error) {
	if len(raw) == 0 || string(raw) == "null" || string(raw) == "{}" {
		return nil, nil
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	d, ok := tok.(json.Delim)
	if !ok || d != '{' {
		return nil, fmt.Errorf("search: expected object")
	}
	var hits []SearchHit
	for dec.More() {
		kt, err := dec.Token()
		if err != nil {
			return nil, err
		}
		key, _ := kt.(string)
		var pair []string
		if err := dec.Decode(&pair); err != nil {
			return nil, err
		}
		id, err := strconv.Atoi(key)
		if err != nil {
			continue
		}
		title, snippet := "", ""
		if len(pair) > 0 {
			title = pair[0]
		}
		if len(pair) > 1 {
			snippet = stripTags(pair[1])
		}
		hits = append(hits, SearchHit{ID: id, Title: title, Snippet: snippet})
	}
	return hits, nil
}

func stripTags(s string) string {
	s = htmlTag.ReplaceAllString(s, "")
	s = strings.ReplaceAll(s, "&nbsp;", " ")
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", "\"")
	return strings.Join(strings.Fields(s), " ")
}

func firstNonEmpty(a, b string) string {
	if a != "" {
		return a
	}
	return b
}
