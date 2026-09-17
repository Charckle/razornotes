# rnotes

Read-only Razor Notes TUI. Browse pinned and recent notes, search the server, and copy a note body or the server clipboard.

Online only: note content is never written to disk. Server URLs and a refresh token are stored at `~/.config/rnotes/tokens.json` (mode `0600`).

## Requirements

- [Go](https://go.dev/dl/) 1.25 or newer
- A running Razor Notes server
- Linux clipboard: `xclip` or `xsel` (`sudo apt install xclip`)

## Install (Ubuntu)

From this directory:

```bash
chmod +x install.sh
./install.sh
```

That builds `rnotes` and copies it to `~/.local/bin/rnotes`.

```bash
rnotes
```

On first run it asks for the server URL, checks `/health`, then asks for username and password. After that, `rnotes` opens a list of saved servers.

A URL argument (or `RNOTES_URL`) skips the picker:

```bash
rnotes http://127.0.0.1:5000
```

Optional: `RNOTES_TOKEN_FILE` to put the token file somewhere other than `~/.config/rnotes/tokens.json`.

Uninstall:

```bash
rm -f ~/.local/bin/rnotes
```

### Build without installing

```bash
go build -o rnotes .
./rnotes
```

## Keys

| Key | Action |
|-----|--------|
| `j` `k` / arrows | Move |
| `enter` `l` | Open server or note |
| `n` | Add a server URL (on the server list) |
| `d` | Remove a server from recents |
| `a` | All notes |
| `/` `ctrl+f` | Search (type, then enter; 3+ characters) |
| `↓` `tab` | Jump from search box to results |
| `y` | Home / list: copy server clipboard (clears after 20s). Note view: copy body |
| `r` | Reload this view |
| `?` | Help |
| `esc` | Back (never quits) |
| `q` | Back to servers; quit on the server list / empty first URL |
| `Q` | Home (pinned + recent) |
| `ctrl+c` | Quit always |

## Notes

- View only: it never creates or edits notes.
- The password is never stored. After a successful login, only the refresh JWT is kept.
- The access token lives in memory and is refreshed on 401.
- Clipboard over SSH is not supported.
