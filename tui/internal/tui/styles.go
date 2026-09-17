package tui

import "github.com/charmbracelet/lipgloss"

const (
	iconNote = "•"
	iconPin  = "*"
	iconTask = "☑"
)

var (
	colHeaderBg   = lipgloss.Color("136")
	colFooterBg   = lipgloss.Color("94")
	colCream      = lipgloss.Color("187")
	colAmber      = lipgloss.Color("179")
	colEntry      = lipgloss.Color("229")
	colSelectedBg = lipgloss.Color("137")
	colSelectedFg = lipgloss.Color("235")
	colDim        = lipgloss.Color("101")
	colBorder     = lipgloss.Color("136")
	colBody       = lipgloss.Color("252")
	colRed        = lipgloss.Color("167")
	colGreen      = lipgloss.Color("150")

	headerStyle = lipgloss.NewStyle().
			Background(colHeaderBg).
			Foreground(colCream).
			Bold(true)

	footerStyle = lipgloss.NewStyle().
			Background(colFooterBg).
			Foreground(colCream)

	selectedStyle = lipgloss.NewStyle().
			Background(colSelectedBg).
			Foreground(colSelectedFg).
			Bold(true)

	groupStyle = lipgloss.NewStyle().
			Foreground(colAmber).
			Bold(true)

	entryStyle = lipgloss.NewStyle().
			Foreground(colEntry)

	entryIconStyle = lipgloss.NewStyle().
			Foreground(colDim)

	pinIconStyle = lipgloss.NewStyle().
			Foreground(colAmber).
			Bold(true)

	dimStyle = lipgloss.NewStyle().
			Foreground(colDim)

	errStyle = lipgloss.NewStyle().
			Foreground(colRed)

	okStyle = lipgloss.NewStyle().
		Foreground(colGreen)

	titleStyle = lipgloss.NewStyle().
			Foreground(colCream).
			Bold(true)

	tileStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colAmber).
			Padding(1, 2)

	panelStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colBorder)

	wrapStyle = lipgloss.NewStyle().
			Foreground(colBody)
)

const (
	footerHome      = " ? help   / search   a all   y clipboard   r reload   enter open   q servers"
	footerList      = " ? help   / search   y clipboard   r reload   enter open   esc back   q back"
	footerSearch    = " ? help   enter search   ↓ results   y clipboard   esc back"
	footerDetail    = " ? help   y copy body   j/k scroll   esc back   q back"
	footerLogin     = " enter sign in    tab next field    esc servers    ? help"
	footerRecents   = " enter open    n new    d remove    j/k move    q quit    ? help"
	footerURL       = " enter connect    esc/q back    ? help"
	footerHelp      = " esc back"
	loginTileMaxW   = 54
	urlTileMaxW     = 72
	recentsTileMaxW = 72
)

func tileWidth(termW, maxW int) int {
	w := maxW
	if avail := termW - 4; avail > 0 && avail < w {
		w = avail
	}
	if w < 22 {
		w = termW
		if w < 18 {
			w = 18
		}
	}
	return w
}

func tileMetrics(termW, maxW int) (styleW, innerW int) {
	styleW = max(tileWidth(termW, maxW)-2, 16)
	innerW = max(styleW-4, 8)
	return styleW, innerW
}
