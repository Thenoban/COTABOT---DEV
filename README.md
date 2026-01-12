# Cotabot - Discord Bot for Squad Server Management

Discord bot for managing Squad game clan, tracking player statistics, events, and activity.

## Features

- 🎮 Squad player statistics tracking (MySquadStats integration)
- 📊 Activity monitoring and reporting
- 📅 Event management system
- 🔄 Google Sheets synchronization
- 📈 Live server status panels
- 💾 SQLite database for data persistence

## Tech Stack

- Python 3.12+
- discord.py - Discord API wrapper
- SQLAlchemy - ORM for database
- aiohttp - Async HTTP requests
- BattleMetrics API - Server data
- Google Sheets API - Data sync

## Setup

### Prerequisites

- Python 3.12 or higher
- Discord Bot Token
- BattleMetrics API key
- Google Sheets API credentials (optional)

### Installation

1. Clone the repository
```bash
git clone <repo-url>
cd "COTABOT - DEV"
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment variables
Create a `.env` file:
```env
DISCORD_TOKEN=your_discord_bot_token
BATTLEMETRICS_TOKEN=your_battlemetrics_token
GOOGLE_SHEET_KEY=your_sheet_key
```

4. Run database migration (first time only)
```bash
python -m database.migrations.json_to_sqlite
```

5. Start the bot
```bash
python main.py
```

## Project Structure

```
COTABOT - DEV/
├── cogs/               # Bot command modules
│   ├── squad_players.py
│   ├── squad_server.py
│   ├── event.py
│   └── passive.py
├── database/           # Database layer
│   ├── models.py       # SQLAlchemy models
│   ├── adapter.py      # Database operations
│   └── migrations/     # Migration scripts
├── main.py            # Bot entry point
├── requirements.txt   # Dependencies
└── .env              # Environment variables (not in repo)
```

## Commands

- `!profil [player]` - View player statistics
- `!aktiflik_panel [sheets|internal]` - Activity tracking panel
- `!panel_kur` - Setup live server status panel
- `!etkinlik` - Event management

## Development

### Database

The bot uses SQLite for local development. Database schema is managed via SQLAlchemy models in `database/models.py`.

To create a fresh database:
```bash
python -m database.migrations.json_to_sqlite
```

### Adding New Features

1. Create/modify cog in `cogs/` directory
2. Update database models if needed
3. Test in DEV environment
4. Deploy to production

## License

Private project - All rights reserved

## Support

For issues and questions, contact the development team.
