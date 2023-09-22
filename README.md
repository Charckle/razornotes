#### Login
- Username: admin
- Password: banana

#### Environment variables
- `APP_NAME` - Defaults to `Razor Notes`
- `DB_HOST` - Database host
- `DB_USERNAME` - Database user
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name
- `DB_PORT` - Database port. Default 3306
- `API_SECRET` - The secret for api
- `SECRET_KEY` - Secret key for CSRF
- `MODULE_MEMORY` - Default False. Activates the menu item for the module
- `ICON_COLOR` - Default "RED". Color of the title icon, so to differentiate between instances in use.
    - Possible: RED, BLUE, L_BLUE, GREEN, ORANGE, BLACK, WHITE, GRAY, D_BROWN, L_BROWN, L_ORANGE, PINK, PURPLE, YELLOW

#### To DO
- new note templates: for certain tasks. Make it modular
- make index also search the name of the note
- make search not suck
- make it not generate the whole index each time you save a note
- cli installer: make it detect missing requirements (pip, etc)
- cli installer: https automatic setting
- change theme for different instances
