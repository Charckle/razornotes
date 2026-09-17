package tui

import (
	tea "github.com/charmbracelet/bubbletea"
)

func (m *Model) handleKey(msg tea.KeyMsg) tea.Cmd {
	s := msg.String()
	if s == "ctrl+c" {
		return m.quit()
	}

	if s == "Q" && !m.typing() && m.mode != modeLogin && m.mode != modeConnecting && m.mode != modeRecents && m.mode != modeURL {
		return m.goHome()
	}

	if m.mode == modeHelp {
		if s == "esc" || s == "q" {
			m.mode = m.helpFrom
		}
		return nil
	}

	if s == "?" && !m.typing() {
		m.helpFrom = m.mode
		m.mode = modeHelp
		return nil
	}

	switch m.mode {
	case modeRecents:
		return m.keysRecents(s)
	case modeURL:
		return m.keysURL(msg, s)
	case modeLogin:
		return m.keysLogin(msg, s)
	case modeConnecting:
		return nil
	case modeHome:
		return m.keysHome(s)
	case modeAll:
		return m.keysAll(s)
	case modeSearch:
		return m.keysSearch(msg, s)
	case modeDetail:
		return m.keysDetail(s)
	}
	return nil
}

func (m *Model) keysRecents(s string) tea.Cmd {
	switch s {
	case "esc":
		return nil
	case "q":
		return m.quit()
	case "n":
		return m.openNewURL()
	case "d", "x":
		return m.deleteRecent()
	case "enter", "l", "right":
		return m.selectRecent()
	}
	moveList(&m.servers, s, len(m.store.URLs()), m.recentsPage())
	return nil
}

func (m *Model) keysURL(msg tea.KeyMsg, s string) tea.Cmd {
	switch s {
	case "esc":
		if len(m.store.URLs()) > 0 {
			m.urlInput.Blur()
			m.mode = modeRecents
			return nil
		}
		return nil
	case "q":
		if m.urlInput.Value() == "" {
			if len(m.store.URLs()) > 0 {
				m.urlInput.Blur()
				m.mode = modeRecents
				return nil
			}
			return m.quit()
		}
	case "enter":
		return m.submitURL()
	}
	var cmd tea.Cmd
	m.urlInput, cmd = m.urlInput.Update(msg)
	return cmd
}

func (m *Model) keysLogin(msg tea.KeyMsg, s string) tea.Cmd {
	switch s {
	case "esc":
		return m.backToServers()
	case "q":
		if m.loginFocus == 1 && m.pwInput.Value() == "" {
			if m.userInput.Value() == "" {
				return m.backToServers()
			}
			m.loginFocus = 0
			m.pwInput.Blur()
			m.userInput.Focus()
			return nil
		}
		if m.loginFocus == 0 && m.userInput.Value() == "" {
			return m.backToServers()
		}
	case "tab", "down":
		if m.loginFocus == 0 {
			m.loginFocus = 1
			m.userInput.Blur()
			m.pwInput.Focus()
			return nil
		}
	case "shift+tab", "up":
		if m.loginFocus == 1 {
			m.loginFocus = 0
			m.pwInput.Blur()
			m.userInput.Focus()
			return nil
		}
	case "enter":
		if m.loginFocus == 0 {
			m.loginFocus = 1
			m.userInput.Blur()
			m.pwInput.Focus()
			return nil
		}
		return m.cmdLogin()
	}
	var cmd tea.Cmd
	if m.loginFocus == 0 {
		m.userInput, cmd = m.userInput.Update(msg)
	} else {
		m.pwInput, cmd = m.pwInput.Update(msg)
	}
	return cmd
}

func (m *Model) listKeys(s string, items []row, l *cursorList) tea.Cmd {
	switch s {
	case "esc":
		if m.mode == modeAll {
			return m.goHome()
		}
		return nil
	case "q":
		if m.mode == modeHome {
			return m.disconnect()
		}
		return m.goHome()
	case "enter", "l", "right":
		return m.openSelected(m.mode)
	case "/", "ctrl+f":
		return m.openSearch()
	case "a":
		return m.cmdLoadAll()
	case "r":
		return m.reload()
	case "y":
		return m.copyY()
	}
	m.moveSelectable(l, items, s, m.bodyHeight())
	return nil
}

func (m *Model) keysHome(s string) tea.Cmd {
	return m.listKeys(s, m.items, &m.list)
}

func (m *Model) keysAll(s string) tea.Cmd {
	return m.listKeys(s, m.items, &m.list)
}

func (m *Model) keysSearch(msg tea.KeyMsg, s string) tea.Cmd {
	page := max(m.bodyHeight()-2, 1)
	n := len(m.hits)

	if m.searchFocusQuery {
		switch s {
		case "esc":
			return m.closeSearch()
		case "down", "ctrl+n", "tab":
			if n > 0 {
				m.searchFocusQuery = false
				m.searchInput.Blur()
			}
			return nil
		case "enter":
			return m.cmdSearch()
		}
		var cmd tea.Cmd
		m.searchInput, cmd = m.searchInput.Update(msg)
		return cmd
	}

	switch s {
	case "esc", "q":
		return m.closeSearch()
	case "/", "ctrl+f":
		m.searchFocusQuery = true
		m.searchInput.Focus()
		return nil
	case "up", "ctrl+p", "k":
		if m.search.cursor == 0 {
			m.searchFocusQuery = true
			m.searchInput.Focus()
			return nil
		}
		m.search.move(-1, n, page)
		return nil
	case "enter", "l", "right":
		return m.openSelected(modeSearch)
	case "r":
		return m.reload()
	case "y":
		return m.copyY()
	}
	if moveList(&m.search, s, n, page) {
		return nil
	}
	return nil
}

func moveList(l *cursorList, s string, n, page int) bool {
	switch s {
	case "up", "k":
		l.move(-1, n, page)
	case "down", "j":
		l.move(1, n, page)
	case "pgup":
		l.move(-page, n, page)
	case "pgdown":
		l.move(page, n, page)
	case "home", "g":
		l.move(-n, n, page)
	case "end", "G":
		l.move(n, n, page)
	default:
		return false
	}
	return true
}

func (m *Model) keysDetail(s string) tea.Cmd {
	switch s {
	case "esc", "q", "h", "left":
		from := m.detailFrom
		m.clearDetail()
		m.mode = from
		if m.mode == modeSearch && m.searchFocusQuery {
			m.searchInput.Focus()
		}
		return nil
	case "up", "k":
		if m.detailOff > 0 {
			m.detailOff--
		}
		return nil
	case "down", "j":
		if m.detailOff < m.detailMaxOff(m.bodyHeight()) {
			m.detailOff++
		}
		return nil
	case "r":
		return m.reload()
	case "y":
		return m.copyY()
	case "/", "ctrl+f":
		return m.openSearch()
	}
	return nil
}

func (m *Model) moveSelectable(l *cursorList, items []row, s string, page int) {
	n := len(items)
	if n == 0 {
		return
	}
	delta := 0
	switch s {
	case "up", "k":
		delta = -1
	case "down", "j":
		delta = 1
	case "pgup":
		delta = -page
	case "pgdown":
		delta = page
	case "home", "g":
		for i, r := range items {
			if r.kind == rowNote {
				l.cursor = i
				l.reveal(n, page)
				return
			}
		}
		return
	case "end", "G":
		for i := n - 1; i >= 0; i-- {
			if items[i].kind == rowNote {
				l.cursor = i
				l.reveal(n, page)
				return
			}
		}
		return
	default:
		return
	}
	step := 1
	if delta < 0 {
		step = -1
	}
	i := l.cursor
	left := delta
	if left < 0 {
		left = -left
	}
	for left > 0 {
		next := i + step
		if next < 0 || next >= n {
			break
		}
		i = next
		if items[i].kind == rowNote {
			left--
		}
	}
	if items[i].kind != rowNote {
		return
	}
	l.cursor = i
	l.reveal(n, page)
}

func (m Model) recentsPage() int {
	page := m.bodyHeight() - 10
	if page < 1 {
		page = 1
	}
	if page > 12 {
		page = 12
	}
	return page
}

func (m Model) bodyHeight() int {
	h := m.height - 4
	if m.status != "" {
		h--
	}
	if h < 1 {
		return 1
	}
	return h
}

func (m Model) contentWidth() int {
	w := m.width - 2
	if w < 1 {
		return 1
	}
	return w
}
