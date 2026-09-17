package tui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
	"rnotes/internal/api"
)

func (m Model) View() string {
	if m.width <= 0 {
		return "rnotes"
	}
	w := m.contentWidth()
	header := m.viewHeader()
	ft := m.footerText()
	footer := footerStyle.Width(w).Render(trunc(ft, w))
	var status string
	if m.status != "" {
		status = okStyle.Width(w).Render(" " + trunc(m.status, w-1))
	}
	used := 4
	if status != "" {
		used++
	}
	bodyH := m.height - used
	if bodyH < 1 {
		bodyH = 1
	}
	body := m.fill(m.viewBody(bodyH), bodyH)

	var b strings.Builder
	b.WriteString(header)
	b.WriteString("\n")
	b.WriteString(body)
	if status != "" {
		b.WriteString("\n")
		b.WriteString(status)
	}
	b.WriteString("\n")
	b.WriteString(footer)
	return panelStyle.Render(b.String())
}

func (m Model) footerText() string {
	switch m.mode {
	case modeRecents:
		return footerRecents
	case modeURL:
		return footerURL
	case modeLogin, modeConnecting:
		return footerLogin
	case modeHome:
		return footerHome
	case modeAll:
		return footerList
	case modeSearch:
		return footerSearch
	case modeDetail:
		return footerDetail
	case modeHelp:
		return footerHelp
	}
	return footerHome
}

func (m Model) viewHeader() string {
	left := " rnotes"
	switch m.mode {
	case modeRecents:
		left += "  servers"
	case modeURL:
		left += "  server"
	case modeLogin, modeConnecting:
		left += "  sign in"
	case modeHome:
		left += "  /"
	case modeAll:
		left += "  /all"
	case modeSearch:
		left += "  /search"
	case modeDetail:
		if m.detail != nil {
			left += "  /" + m.detail.Title
		} else {
			left += "  /note"
		}
	case modeHelp:
		left += "  help"
	}
	right := ""
	if m.mode != modeRecents && m.mode != modeURL && m.url != "" {
		right = api.HostLabel(m.url)
	}
	w := m.contentWidth()
	gap := w - lipgloss.Width(left) - lipgloss.Width(right) - 1
	if gap < 1 {
		s := trunc(left, w)
		return headerStyle.Width(w).Render(s)
	}
	line := left + strings.Repeat(" ", gap) + right + " "
	return headerStyle.Width(w).Render(trunc(line, w))
}

func (m Model) viewBody(h int) string {
	switch m.mode {
	case modeRecents:
		return m.viewRecents(h)
	case modeURL:
		return m.viewURL(h)
	case modeLogin:
		return m.viewLogin(h)
	case modeConnecting:
		return m.viewConnecting(h)
	case modeHome, modeAll:
		return m.viewList(h)
	case modeSearch:
		return m.viewSearch(h)
	case modeDetail:
		return m.viewDetail(h)
	case modeHelp:
		return m.viewHelp(h)
	}
	return ""
}

func (m Model) viewRecents(h int) string {
	urls := m.store.URLs()
	_, inner := tileMetrics(m.contentWidth(), recentsTileMaxW)
	hint := "enter open    n new    q quit"
	var body string
	if len(urls) == 0 {
		body = dimStyle.Render("no servers yet")
		hint = "n add a URL"
	} else {
		page := m.recentsPage()
		lines := make([]string, 0, page)
		end := m.servers.offset + page
		for i := m.servers.offset; i < len(urls) && i < end; i++ {
			u := urls[i]
			label := api.HostLabel(u)
			extra := ""
			if srv, ok := m.store.Lookup(u); ok && srv.Username != "" {
				extra = srv.Username
			}
			sel := i == m.servers.cursor
			lines = append(lines, m.rowLineWidth(inner, iconNote, label, extra, entryIconStyle, entryStyle, sel))
		}
		body = strings.Join(lines, "\n")
	}
	return m.placeTile(h, recentsTileMaxW, "Servers", "", body, hint)
}

func (m Model) viewURL(h int) string {
	err := " "
	if m.urlErr != "" {
		_, inputW := tileMetrics(m.contentWidth(), urlTileMaxW)
		err = errStyle.Render(trunc(m.urlErr, inputW))
	}
	body := strings.Join([]string{
		m.urlInput.View(),
		"",
		err,
	}, "\n")
	hint := "enter connect"
	if len(m.store.URLs()) > 0 {
		hint = "enter connect    esc back"
	} else {
		hint = "enter connect    q quit"
	}
	return m.placeTile(h, urlTileMaxW, "Server URL", "", body, hint)
}

func (m Model) viewLogin(h int) string {
	err := " "
	if m.pwErr != "" {
		_, inputW := tileMetrics(m.contentWidth(), loginTileMaxW)
		err = errStyle.Render(trunc(m.pwErr, inputW))
	}
	user := m.userInput.View()
	pw := m.pwInput.View()
	if m.loginFocus != 0 {
		user = dimStyle.Render(user)
	} else {
		pw = dimStyle.Render(pw)
	}
	body := strings.Join([]string{
		dimStyle.Render("username"),
		user,
		"",
		dimStyle.Render("password"),
		pw,
		"",
		err,
	}, "\n")
	return m.placeTile(h, loginTileMaxW, "Sign in", m.url, body, "enter sign in    esc servers")
}

func (m Model) viewConnecting(h int) string {
	body := strings.Join([]string{
		m.spin.View() + " " + m.connectMsg,
		"",
		" ",
	}, "\n")
	return m.placeTile(h, loginTileMaxW, "Razor Notes", m.url, body, "")
}

func (m Model) placeTile(h int, maxW int, title, subtitle, body, hint string) string {
	styleW, inner := tileMetrics(m.contentWidth(), maxW)
	header := titleStyle.Render(title)
	if subtitle != "" {
		header += "\n" + dimStyle.Render(trunc(subtitle, inner))
	}
	parts := []string{header, "", body}
	if hint != "" {
		parts = append(parts, "", dimStyle.Render(hint))
	}
	tile := tileStyle.Width(styleW).Render(strings.Join(parts, "\n"))
	return lipgloss.Place(m.contentWidth(), h, lipgloss.Center, lipgloss.Center, tile)
}

func (m Model) viewList(h int) string {
	if len(m.items) == 0 {
		return dimStyle.Render("  (no notes)")
	}
	lines := make([]string, 0, h)
	end := m.list.offset + h
	for i := m.list.offset; i < len(m.items) && i < end; i++ {
		sel := i == m.list.cursor && m.items[i].kind == rowNote
		lines = append(lines, m.renderRow(m.items[i], sel))
	}
	return strings.Join(lines, "\n")
}

func (m Model) renderRow(r row, selected bool) string {
	if r.kind == rowHeader {
		return groupStyle.Width(m.contentWidth()).Render("  " + r.title)
	}
	label := r.note.Title
	if label == "" {
		label = "(untitled)"
	}
	extra := r.snippet
	if extra == "" {
		extra = r.note.PreviewText()
	}
	icon := iconNote
	iconSt := entryIconStyle
	if r.note.NoteType == 1 {
		icon = iconTask
	}
	if r.note.Pinned {
		icon = iconPin
		iconSt = pinIconStyle
	}
	return m.rowLine(icon, label, extra, iconSt, entryStyle, selected)
}

func (m Model) viewSearch(h int) string {
	query := m.searchInput.View()
	if !m.searchFocusQuery {
		query = dimStyle.Render(query)
	}
	rest := h - 2
	if rest < 1 {
		rest = 1
	}
	var body string
	switch {
	case m.searchPending:
		body = dimStyle.Render("  " + m.spin.View() + " searching…")
	case strings.TrimSpace(m.searchInput.Value()) == "":
		body = dimStyle.Render("  type a query and press enter")
	case len(m.hits) == 0:
		body = dimStyle.Render("  no matches")
	default:
		lines := make([]string, 0, rest)
		end := m.search.offset + rest
		for i := m.search.offset; i < len(m.hits) && i < end; i++ {
			sel := !m.searchFocusQuery && i == m.search.cursor
			lines = append(lines, m.renderRow(m.hits[i], sel))
		}
		body = strings.Join(lines, "\n")
	}
	return query + "\n" + dimStyle.Render(strings.Repeat("─", m.contentWidth())) + "\n" + body
}

func (m *Model) buildDetailLines() {
	n := m.detail
	if n == nil {
		m.detailLines = nil
		return
	}
	meta := n.DateMod
	if n.Pinned {
		meta = "pinned  " + meta
	}
	if n.NoteType == 1 {
		meta = "task  " + meta
	}
	lines := []string{
		"  " + titleStyle.Render(orDash(n.Title)),
		"  " + dimStyle.Render(strings.TrimSpace(meta)),
		"",
	}
	body := n.Text
	if body == "" {
		lines = append(lines, "  "+dimStyle.Render("(empty)"))
	} else {
		wrapped := wrapStyle.Width(max(m.contentWidth()-4, 8)).Render(body)
		for _, ln := range strings.Split(wrapped, "\n") {
			lines = append(lines, "  "+ln)
		}
	}
	m.detailLines = lines
}

func (m Model) viewDetail(h int) string {
	if len(m.detailLines) == 0 {
		return ""
	}
	start := min(max(m.detailOff, 0), m.detailMaxOff(h))
	end := min(start+h, len(m.detailLines))
	w := m.contentWidth()
	out := make([]string, 0, end-start)
	for _, ln := range m.detailLines[start:end] {
		out = append(out, trunc(ln, w))
	}
	return strings.Join(out, "\n")
}

func (m Model) detailMaxOff(h int) int {
	return max(len(m.detailLines)-h, 0)
}

var helpLines = strings.Split(strings.TrimSpace(`
  servers
    enter        open selected server
    n            add a new URL
    d            remove from recents
    q            quit (on the server list)

  navigation
    j k  ↑ ↓     move
    enter  l     open note
    g  G         top / bottom
    a            all notes
    Q            home (pinned + recent)
    q            back to servers

  find & copy
    /  ctrl+f    search (enter to run)
    y            home/list: server clipboard (clears in 20s)
                 note: copy body
    r            reload this view
    esc          back (never quits)
    ?            this help

  session
    rnotes URL   skip the picker
    tokens       ~/.config/rnotes/tokens.json (0600)
    notes        never stored locally
`), "\n")

func (m Model) viewHelp(h int) string {
	n := min(h, len(helpLines))
	w := m.contentWidth()
	out := make([]string, n)
	for i, ln := range helpLines[:n] {
		out[i] = trunc(ln, w)
	}
	return strings.Join(out, "\n")
}

func (m Model) rowLine(icon, label, extra string, iconSt, labelSt lipgloss.Style, selected bool) string {
	return m.rowLineWidth(m.contentWidth(), icon, label, extra, iconSt, labelSt, selected)
}

func (m Model) rowLineWidth(w int, icon, label, extra string, iconSt, labelSt lipgloss.Style, selected bool) string {
	prefix := " " + icon + " "
	prefixW := lipgloss.Width(prefix)
	extraPart := ""
	if extra != "" {
		extraPart = "  " + extra
	}
	budget := w - prefixW - lipgloss.Width(extraPart)
	if budget < 8 && extraPart != "" {
		extraMax := w - prefixW - 2 - 8
		if extraMax < 4 {
			extraPart = ""
		} else {
			extraPart = "  " + trunc(extra, extraMax)
		}
		budget = w - prefixW - lipgloss.Width(extraPart)
	}
	if budget < 1 {
		budget = 1
	}
	label = trunc(label, budget)
	plain := prefix + label + extraPart
	if selected {
		return selectedStyle.Width(w).Render(trunc(plain, w))
	}
	line := iconSt.Render(prefix) + labelSt.Render(label)
	if extraPart != "" {
		line += dimStyle.Render(extraPart)
	}
	pad := w - lipgloss.Width(plain)
	if pad > 0 {
		line += strings.Repeat(" ", pad)
	}
	return line
}

func (m Model) fill(s string, h int) string {
	width := m.contentWidth()
	lines := strings.Split(s, "\n")
	if len(lines) == 1 && lines[0] == "" {
		lines = nil
	}
	for len(lines) < h {
		lines = append(lines, "")
	}
	if len(lines) > h {
		lines = lines[:h]
	}
	for i, ln := range lines {
		lw := lipgloss.Width(ln)
		if lw < width {
			lines[i] = ln + strings.Repeat(" ", width-lw)
		}
	}
	return strings.Join(lines, "\n")
}

func trunc(s string, w int) string {
	if w <= 0 {
		return ""
	}
	width := lipgloss.Width(s)
	if width <= w {
		return s
	}
	if w <= 1 {
		return "…"
	}
	if width == len(s) {
		return s[:w-1] + "…"
	}
	r := []rune(s)
	low, high := 0, len(r)
	for low < high {
		mid := (low + high + 1) / 2
		if lipgloss.Width(string(r[:mid])+"…") <= w {
			low = mid
		} else {
			high = mid - 1
		}
	}
	if low <= 0 {
		return "…"
	}
	return string(r[:low]) + "…"
}

func orDash(s string) string {
	if s == "" {
		return "—"
	}
	return s
}
