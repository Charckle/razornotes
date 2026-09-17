package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"rnotes/internal/api"
	"rnotes/internal/auth"
)

type mode int

const (
	modeRecents mode = iota
	modeURL
	modeLogin
	modeConnecting
	modeHome
	modeAll
	modeSearch
	modeDetail
	modeHelp
)

const searchMin = 3

type rowKind int

const (
	rowHeader rowKind = iota
	rowNote
)

type row struct {
	kind    rowKind
	title   string
	note    api.Note
	snippet string
}

type probeResult struct {
	err error
}

type loginResult struct {
	err error
}

type refreshResult struct {
	err error
}

type homeResult struct {
	pinned []api.Note
	recent []api.Note
	err    error
}

type allResult struct {
	notes []api.Note
	err   error
}

type searchResult struct {
	query string
	hits  []api.SearchHit
	err   error
}

type noteResult struct {
	note api.Note
	from mode
	err  error
}

// Config is everything the TUI needs at startup.
type Config struct {
	StartURL string
	Store    *auth.Store
}

// Model is the rnotes TUI.
type Model struct {
	width, height int
	mode          mode
	helpFrom      mode

	url         string
	fromRecents bool
	store       *auth.Store
	client      *api.Client

	urlInput textinput.Model
	urlErr   string
	servers  cursorList

	userInput  textinput.Model
	pwInput    textinput.Model
	loginFocus int // 0 username, 1 password
	pwErr      string
	spin       spinner.Model
	connectMsg string

	homeItems []row
	items     []row
	list      cursorList

	searchInput      textinput.Model
	searchFocusQuery bool
	searchPending    bool
	hits             []row
	search           cursorList

	detail      *api.Note
	detailFrom  mode
	detailOff   int
	detailLines []string

	status    string
	clipSeq   int
	clipOwned bool
}

// New starts on recents, a URL prompt, or connecting if StartURL is set.
func New(cfg Config) Model {
	user := textinput.New()
	user.Prompt = ""
	user.Placeholder = "username or email"
	user.CharLimit = 256

	pw := textinput.New()
	pw.EchoMode = textinput.EchoPassword
	pw.EchoCharacter = '•'
	pw.Prompt = ""
	pw.Placeholder = "password"
	pw.CharLimit = 1024

	u := textinput.New()
	u.Prompt = ""
	u.Placeholder = "https://notes.example.com"
	u.CharLimit = 512

	se := textinput.New()
	se.Prompt = " / "
	se.Placeholder = "search (enter, 3+ chars)"
	se.CharLimit = 256

	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = pinIconStyle

	m := Model{
		store:       cfg.Store,
		userInput:   user,
		pwInput:     pw,
		urlInput:    u,
		searchInput: se,
		spin:        sp,
		connectMsg:  "checking server…",
	}
	m.resize(80, 24)
	switch {
	case cfg.StartURL != "":
		m.url = cfg.StartURL
		m.urlInput.SetValue(cfg.StartURL)
		m.client = api.NewClient(cfg.StartURL, nil)
		m.mode = modeConnecting
	case len(cfg.Store.URLs()) == 0:
		m.mode = modeURL
		m.urlInput.Focus()
	default:
		m.mode = modeRecents
	}
	return m
}

func (m Model) Init() tea.Cmd {
	if m.mode == modeConnecting {
		return tea.Batch(m.spin.Tick, m.cmdPing())
	}
	if m.mode == modeURL {
		return textinput.Blink
	}
	return nil
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	cmd := m.update(msg)
	return m, cmd
}

func (m *Model) update(msg tea.Msg) tea.Cmd {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.resize(msg.Width, msg.Height)
		return nil

	case spinner.TickMsg:
		if m.mode == modeConnecting || m.searchPending {
			var cmd tea.Cmd
			m.spin, cmd = m.spin.Update(msg)
			return cmd
		}

	case probeResult:
		return m.handleProbe(msg)

	case refreshResult:
		if msg.err != nil {
			m.mode = modeLogin
			m.pwErr = msg.err.Error()
			if unauth(msg.err) {
				m.store.ForgetTokens(m.url)
				_ = m.store.Save()
			}
			m.focusLogin()
			return textinput.Blink
		}
		m.connectMsg = "loading notes…"
		return m.cmdLoadHome()

	case loginResult:
		if msg.err != nil {
			m.mode = modeLogin
			m.pwErr = msg.err.Error()
			m.pwInput.SetValue("")
			m.loginFocus = 1
			m.pwInput.Focus()
			m.userInput.Blur()
			return textinput.Blink
		}
		m.store.Set(m.url, auth.Server{
			Username: m.client.Username(),
			Refresh:  m.client.RefreshToken(),
		})
		_ = m.store.Save()
		m.resetLogin()
		m.mode = modeConnecting
		m.connectMsg = "loading notes…"
		return tea.Batch(m.spin.Tick, m.cmdLoadHome())

	case homeResult:
		if msg.err != nil {
			if unauth(msg.err) && m.mode == modeConnecting {
				m.mode = modeLogin
				m.pwErr = msg.err.Error()
				m.store.ForgetTokens(m.url)
				_ = m.store.Save()
				m.focusLogin()
				return textinput.Blink
			}
			if m.mode == modeConnecting {
				m.mode = modeHome
			}
			m.status = msg.err.Error()
			return nil
		}
		m.buildHome(msg.pinned, msg.recent)
		m.mode = modeHome
		m.status = ""
		return nil

	case allResult:
		if msg.err != nil {
			m.status = msg.err.Error()
			return nil
		}
		m.buildNoteList(msg.notes)
		m.mode = modeAll
		m.status = ""
		return nil

	case searchResult:
		m.searchPending = false
		if msg.query != strings.TrimSpace(m.searchInput.Value()) {
			return nil
		}
		if msg.err != nil {
			m.status = msg.err.Error()
			return nil
		}
		m.buildSearch(msg.hits)
		m.status = ""
		return nil

	case noteResult:
		if msg.err != nil {
			m.status = msg.err.Error()
			return nil
		}
		n := msg.note
		m.detail = &n
		m.detailFrom = msg.from
		m.detailOff = 0
		m.mode = modeDetail
		m.status = ""
		m.buildDetailLines()
		return nil

	case copiedMsg:
		m.handleCopied(msg)
		return nil

	case clipLoadedMsg:
		return m.handleClipLoaded(msg)

	case clearClipMsg:
		m.handleClearClip(msg)
		return nil

	case tea.KeyMsg:
		return m.handleKey(msg)
	}
	return nil
}

func (m *Model) resize(width, height int) {
	m.width = width
	m.height = height
	cw := m.contentWidth()
	_, inner := tileMetrics(cw, loginTileMaxW)
	m.userInput.Width = inner
	m.pwInput.Width = inner
	_, urlInner := tileMetrics(cw, urlTileMaxW)
	m.urlInput.Width = urlInner
	m.searchInput.Width = max(cw-4, 8)
	m.buildDetailLines()
}

func (m *Model) typing() bool {
	if m.mode == modeURL {
		return m.urlInput.Value() != ""
	}
	if m.mode == modeLogin {
		if m.loginFocus == 0 {
			return m.userInput.Value() != ""
		}
		return m.pwInput.Value() != ""
	}
	return m.mode == modeSearch && m.searchFocusQuery
}

func (m *Model) quit() tea.Cmd {
	m.wipeClipboard()
	return tea.Quit
}

func (m *Model) resetLogin() {
	m.pwInput.SetValue("")
	m.pwErr = ""
	m.urlErr = ""
}

func (m *Model) focusLogin() {
	if strings.TrimSpace(m.userInput.Value()) != "" {
		m.loginFocus = 1
		m.userInput.Blur()
		m.pwInput.Focus()
		return
	}
	m.loginFocus = 0
	m.pwInput.Blur()
	m.userInput.Focus()
}

func (m *Model) disconnect() tea.Cmd {
	m.wipeClipboard()
	m.homeItems = nil
	m.items = nil
	m.hits = nil
	m.clearDetail()
	m.searchInput.Blur()
	m.searchInput.SetValue("")
	m.status = ""
	if m.client != nil {
		m.client.Reset()
	}
	return m.backToServers()
}

func (m *Model) backToServers() tea.Cmd {
	m.resetLogin()
	m.pwInput.Blur()
	m.userInput.Blur()
	m.urlInput.Blur()
	if len(m.store.URLs()) == 0 {
		m.mode = modeURL
		m.urlInput.Focus()
		return textinput.Blink
	}
	m.servers.setLen(len(m.store.URLs()))
	m.mode = modeRecents
	return nil
}

func (m *Model) openNewURL() tea.Cmd {
	m.urlErr = ""
	m.urlInput.SetValue("")
	m.urlInput.Focus()
	m.mode = modeURL
	return textinput.Blink
}

func (m *Model) selectRecent() tea.Cmd {
	urls := m.store.URLs()
	if len(urls) == 0 {
		return m.openNewURL()
	}
	i := m.servers.cursor
	if i < 0 || i >= len(urls) {
		i = 0
	}
	return m.connectTo(urls[i], true)
}

func (m *Model) deleteRecent() tea.Cmd {
	urls := m.store.URLs()
	if len(urls) == 0 {
		return nil
	}
	i := m.servers.cursor
	if i < 0 || i >= len(urls) {
		return nil
	}
	m.store.Remove(urls[i])
	_ = m.store.Save()
	urls = m.store.URLs()
	m.servers.setLen(len(urls))
	if len(urls) == 0 {
		return m.openNewURL()
	}
	return nil
}

func (m *Model) submitURL() tea.Cmd {
	raw := strings.TrimSpace(m.urlInput.Value())
	if raw == "" {
		m.urlErr = "enter a server URL"
		return nil
	}
	return m.connectTo(raw, false)
}

func (m *Model) connectTo(raw string, fromRecents bool) tea.Cmd {
	base, err := api.NormalizeBase(raw)
	if err != nil {
		m.urlErr = err.Error()
		if fromRecents {
			m.status = err.Error()
			m.mode = modeRecents
			return nil
		}
		m.mode = modeURL
		m.urlInput.Focus()
		return textinput.Blink
	}
	m.fromRecents = fromRecents
	m.url = base
	m.urlErr = ""
	m.status = ""
	m.client = api.NewClient(base, nil)
	if srv, ok := m.store.Lookup(base); ok {
		m.userInput.SetValue(srv.Username)
	} else {
		m.userInput.SetValue("")
	}
	m.resetLogin()
	m.mode = modeConnecting
	m.connectMsg = "checking server…"
	return tea.Batch(m.spin.Tick, m.cmdPing())
}

func (m *Model) handleProbe(msg probeResult) tea.Cmd {
	if msg.err != nil {
		m.urlErr = msg.err.Error()
		if m.fromRecents {
			m.status = "unreachable: " + msg.err.Error()
			m.mode = modeRecents
			return nil
		}
		m.mode = modeURL
		m.urlInput.Focus()
		return textinput.Blink
	}
	m.store.Touch(m.url)
	_ = m.store.Save()
	if srv, ok := m.store.Get(m.url); ok {
		m.client.SetRefresh(srv.Refresh, srv.Username)
		m.userInput.SetValue(srv.Username)
		m.connectMsg = "signing in…"
		return tea.Batch(m.spin.Tick, m.cmdRefresh())
	}
	m.mode = modeLogin
	m.focusLogin()
	return textinput.Blink
}

func (m *Model) cmdPing() tea.Cmd {
	client := m.client
	return func() tea.Msg {
		if client == nil {
			return probeResult{err: fmt.Errorf("no server")}
		}
		return probeResult{err: client.Ping()}
	}
}

func (m *Model) goHome() tea.Cmd {
	m.searchInput.Blur()
	m.searchInput.SetValue("")
	m.searchPending = false
	m.clearDetail()
	if len(m.homeItems) == 0 {
		m.mode = modeConnecting
		m.connectMsg = "loading notes…"
		return tea.Batch(m.spin.Tick, m.cmdLoadHome())
	}
	m.items = append(m.items[:0], m.homeItems...)
	m.list.setLen(len(m.items))
	m.snapToNote(&m.list, m.items)
	m.mode = modeHome
	return nil
}

func (m *Model) openSearch() tea.Cmd {
	m.clearDetail()
	m.mode = modeSearch
	m.searchFocusQuery = true
	m.searchPending = false
	m.searchInput.SetValue("")
	m.searchInput.Focus()
	m.hits = nil
	m.search.setLen(0)
	return textinput.Blink
}

func (m *Model) closeSearch() tea.Cmd {
	m.searchInput.Blur()
	m.searchInput.SetValue("")
	m.searchPending = false
	m.hits = nil
	return m.goHome()
}

func (m *Model) clearDetail() {
	m.detail = nil
	m.detailLines = nil
	m.detailOff = 0
}

func (m *Model) buildHome(pinned, recent []api.Note) {
	m.items = m.items[:0]
	if len(pinned) > 0 {
		m.items = append(m.items, row{kind: rowHeader, title: "Pinned"})
		for _, n := range pinned {
			m.items = append(m.items, row{kind: rowNote, note: n})
		}
	}
	if len(recent) > 0 {
		m.items = append(m.items, row{kind: rowHeader, title: "Recent"})
		for _, n := range recent {
			m.items = append(m.items, row{kind: rowNote, note: n})
		}
	}
	m.homeItems = append(m.homeItems[:0], m.items...)
	m.list.setLen(len(m.items))
	m.snapToNote(&m.list, m.items)
}

func (m *Model) buildNoteList(notes []api.Note) {
	m.items = m.items[:0]
	for _, n := range notes {
		m.items = append(m.items, row{kind: rowNote, note: n})
	}
	m.list.setLen(len(m.items))
	m.snapToNote(&m.list, m.items)
}

func (m *Model) buildSearch(hits []api.SearchHit) {
	m.hits = m.hits[:0]
	for _, h := range hits {
		m.hits = append(m.hits, row{
			kind:    rowNote,
			note:    api.Note{ID: h.ID, Title: h.Title, Preview: h.Snippet},
			snippet: h.Snippet,
		})
	}
	m.search.setLen(len(m.hits))
	m.search.cursor = 0
	m.search.offset = 0
}

func (m *Model) snapToNote(l *cursorList, items []row) {
	if len(items) == 0 {
		return
	}
	if l.cursor >= 0 && l.cursor < len(items) && items[l.cursor].kind == rowNote {
		return
	}
	for i, r := range items {
		if r.kind == rowNote {
			l.cursor = i
			l.reveal(len(items), m.bodyHeight())
			return
		}
	}
}

func (m *Model) selectedNote(items []row, l cursorList) *api.Note {
	if l.cursor < 0 || l.cursor >= len(items) {
		return nil
	}
	r := items[l.cursor]
	if r.kind != rowNote {
		return nil
	}
	n := r.note
	return &n
}

func (m *Model) openSelected(from mode) tea.Cmd {
	var n *api.Note
	switch from {
	case modeSearch:
		n = m.selectedNote(m.hits, m.search)
	default:
		n = m.selectedNote(m.items, m.list)
	}
	if n == nil {
		m.status = "select a note"
		return nil
	}
	id := n.ID
	client := m.client
	m.status = "loading…"
	return func() tea.Msg {
		note, err := client.Note(id)
		return noteResult{note: note, from: from, err: err}
	}
}

func (m *Model) cmdRefresh() tea.Cmd {
	client := m.client
	return func() tea.Msg {
		return refreshResult{err: client.Refresh()}
	}
}

func (m *Model) cmdLogin() tea.Cmd {
	user := strings.TrimSpace(m.userInput.Value())
	pass := m.pwInput.Value()
	if user == "" {
		m.pwErr = "enter a username"
		m.loginFocus = 0
		m.pwInput.Blur()
		m.userInput.Focus()
		return textinput.Blink
	}
	if pass == "" {
		m.pwErr = "enter the password"
		m.loginFocus = 1
		m.userInput.Blur()
		m.pwInput.Focus()
		return textinput.Blink
	}
	m.pwInput.SetValue("")
	m.mode = modeConnecting
	m.connectMsg = "signing in…"
	m.pwErr = ""
	client := m.client
	return tea.Batch(m.spin.Tick, func() tea.Msg {
		return loginResult{err: client.Login(user, pass)}
	})
}

func (m *Model) cmdLoadHome() tea.Cmd {
	client := m.client
	return func() tea.Msg {
		pinned, err := client.Pinned()
		if err != nil {
			return homeResult{err: err}
		}
		recent, err := client.Index()
		if err != nil {
			return homeResult{err: err}
		}
		return homeResult{pinned: pinned, recent: recent}
	}
}

func (m *Model) cmdLoadAll() tea.Cmd {
	client := m.client
	m.status = "loading…"
	return func() tea.Msg {
		notes, err := client.Meta()
		return allResult{notes: notes, err: err}
	}
}

func (m *Model) cmdSearch() tea.Cmd {
	q := strings.TrimSpace(m.searchInput.Value())
	if len(q) < searchMin {
		m.status = "type at least 3 characters"
		return nil
	}
	m.searchPending = true
	m.status = ""
	client := m.client
	return tea.Batch(m.spin.Tick, func() tea.Msg {
		hits, err := client.Search(q)
		return searchResult{query: q, hits: hits, err: err}
	})
}

func (m *Model) reload() tea.Cmd {
	switch m.mode {
	case modeHome:
		m.status = "loading…"
		return m.cmdLoadHome()
	case modeAll:
		return m.cmdLoadAll()
	case modeSearch:
		return m.cmdSearch()
	case modeDetail:
		if m.detail == nil {
			return nil
		}
		id := m.detail.ID
		from := m.detailFrom
		client := m.client
		m.status = "loading…"
		return func() tea.Msg {
			note, err := client.Note(id)
			return noteResult{note: note, from: from, err: err}
		}
	}
	return nil
}

func unauth(err error) bool {
	if err == nil {
		return false
	}
	ae, ok := err.(*api.Error)
	return ok && ae.Unauthorized()
}
