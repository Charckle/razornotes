#### Functions
- Note creation
    - simplemde markdown editor for editing.
- Pin notes to front page
- Hide notes from frontpage
- Color tags
- Trash before deletion
- Fuzzy search
- Cli app
- Clipboard save option
- Note templates
- Import Export in json
- Notes downloadable to .md files
- File attachments
- A memory subapp
- A secrets sharing subapp, for passwords etc
- fido2 login

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
- `JWT_SECRET_KEY` - The secret for jwt api
- `SECRET_KEY` - Secret key for CSRF
- `RP_ID` - WebAuthn variable, it is the base domain. When developing localy, use "localhost"
- `RP_NAME` - WebAuthn variable, for identification of the application.
- `RP_PORT` - WebAuthn requires also the port, so we configure it here. Insert "" for 443 or 80, otherwise ":5000" or the other port. The column is required.
- `RP_PROTOCOL` - WebAuthn requires the protocol
- `IP_RESTRICTION` - If set to 1, it activates the restriction based on ip and networks defined in the next variable. Fibo2 login will not be restricted.
- `IPS_NETWORKS` - IPs and networks that the users are allowed to login from, delimited by a comma. Default is set to "127.0.0.1,127.0.0.0/8"
- `MODULE_MEMORY` - Default False. Activates the menu item for the module
- `MODULE_SECRETS` - Default False. Activates the menu item for the module
- `WTF_CSRF_ENABLED` - Default True. If false, it wont check CRSF tokens in the forms in ALL forms.
- `ICON_COLOR` - Default "RED". Color of the title icon, so to differentiate between instances in use.
    - Possible: RED, BLUE, L_BLUE, GREEN, ORANGE, BLACK, WHITE, GRAY, D_BROWN, L_BROWN, L_ORANGE, PINK, PURPLE, YELLOW

#### To DO
- fix multi ip in ip restriction
- create a gitlab cicd, that uses semantic-release for versioning, and trivy tests for iamges and code
- business mode: for personal use, the notes could be used for private and business settings. Add a mode to only show one or the other
     - as in, if you are at work and you use this app, you do not want people near you seeing you your personal notes poping up
- make it so that if the database is not accessible, healthcheck works
- add IAA (I am alive) ping to central razor server once a day
- mysql replication
- pagination for all notes
- create sql pooling for connections
- add OTP verification
- fuzzy search
- ip restriction from web browser instead of environment
- hash check if the note has changed while the note was being edited
- related notes: add existing notes to notes, for easier browsing
- clustering
- qr code for note
- sql conn pool
- make tasks have a deadline and marked as completed
- make the version of the app bit somewhat connected with the option to import it, so you do not mess it up if the version is not compatible
- make index also search the name of the note
- make it not generate the whole index each time you save a note
- cli installer: make it detect missing requirements (pip, etc)
- cli installer: https automatic setting
- change theme for different instances

#### Troubleshooting
- is python throws and error, that six is not installed, uninstall it and reinstall it:
    - `pip uninstall six`
    - `pip install six`
