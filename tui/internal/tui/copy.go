package tui

import (
	"time"

	"github.com/atotto/clipboard"
	tea "github.com/charmbracelet/bubbletea"
)

const clipboardTTL = 20 * time.Second

type copyKind string

const (
	copyBody copyKind = "body"
	copyClip copyKind = "clipboard"
)

type copiedMsg struct {
	kind copyKind
	seq  int
	err  error
}

type clearClipMsg struct {
	seq int
}

type clipLoadedMsg struct {
	text string
	seq  int
	err  error
}

func (m *Model) copyY() tea.Cmd {
	if m.mode == modeDetail {
		return m.copyBody()
	}
	if m.mode == modeHome || m.mode == modeAll || m.mode == modeSearch {
		return m.copyServerClipboard()
	}
	m.status = "nothing to copy"
	return nil
}

func (m *Model) copyBody() tea.Cmd {
	if m.detail == nil {
		m.status = "no note"
		return nil
	}
	text := m.detail.Text
	if text == "" {
		m.status = "empty note"
		return nil
	}
	m.clipSeq++
	seq := m.clipSeq
	m.clipOwned = false
	return func() tea.Msg {
		if err := clipboard.WriteAll(text); err != nil {
			return copiedMsg{kind: copyBody, seq: seq, err: err}
		}
		return copiedMsg{kind: copyBody, seq: seq}
	}
}

func (m *Model) copyServerClipboard() tea.Cmd {
	m.clipSeq++
	seq := m.clipSeq
	client := m.client
	return func() tea.Msg {
		text, err := client.Clipboard()
		return clipLoadedMsg{text: text, seq: seq, err: err}
	}
}

func (m *Model) handleClipLoaded(msg clipLoadedMsg) tea.Cmd {
	if msg.seq != m.clipSeq {
		return nil
	}
	if msg.err != nil {
		m.status = "clipboard: " + msg.err.Error()
		m.clipOwned = false
		return nil
	}
	text := msg.text
	seq := msg.seq
	return tea.Batch(
		func() tea.Msg {
			if err := clipboard.WriteAll(text); err != nil {
				return copiedMsg{kind: copyClip, seq: seq, err: err}
			}
			return copiedMsg{kind: copyClip, seq: seq}
		},
		tea.Tick(clipboardTTL, func(time.Time) tea.Msg {
			return clearClipMsg{seq: seq}
		}),
	)
}

func (m *Model) handleCopied(msg copiedMsg) {
	if msg.seq != m.clipSeq {
		return
	}
	if msg.err != nil {
		m.status = "clipboard: " + msg.err.Error()
		m.clipOwned = false
		return
	}
	switch msg.kind {
	case copyBody:
		m.clipOwned = false
		m.status = "copied body"
	case copyClip:
		m.clipOwned = true
		m.status = "copied clipboard, clears in 20s"
	}
}

func (m *Model) handleClearClip(msg clearClipMsg) {
	if msg.seq != m.clipSeq || !m.clipOwned {
		return
	}
	_ = clipboard.WriteAll("")
	m.clipOwned = false
	if m.status != "" {
		m.status = "clipboard cleared"
	}
}

func (m *Model) wipeClipboard() {
	if m.clipOwned {
		_ = clipboard.WriteAll("")
		m.clipOwned = false
	}
}
