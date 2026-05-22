# 📺 EPG Merger

Automatically fetches multiple XMLTV EPG sources and merges them into a single `epg_merged.xml` file — updated daily via GitHub Actions.

---

## 🗂 File structure

```
.
├── merge_epg.py              # Merger script (no external dependencies)
├── sources.json              # Your EPG source list (create from example below)
├── sources.example.json      # Template — copy to sources.json and edit
├── epg_merged.xml            # ✅ Auto-generated merged output
├── epg_status.json           # ✅ Auto-generated status/stats
└── .github/
    └── workflows/
        └── update_epg.yml    # GitHub Actions — runs daily at 04:00 UTC
```

---

## 🚀 Setup

### 1. Fork / clone this repo

### 2. Create your `sources.json`

Copy the example and add your real EPG URLs:

```bash
cp sources.example.json sources.json
```

Edit `sources.json`:

```json
{
  "sources": [
    {
      "name": "My First EPG",
      "url": "https://example.com/epg.xml",
      "enabled": true
    },
    {
      "name": "My Second EPG (gzip OK)",
      "url": "https://example.com/epg2.xml.gz",
      "enabled": true
    }
  ]
}
```

- Set `"enabled": false` to temporarily skip a source without deleting it.
- Both plain `.xml` and `.gz` compressed files are supported automatically.

### 3. Push to GitHub

The workflow runs automatically every day. You can also trigger it manually:  
**Actions → Merge & Sync EPG → Run workflow**

---

## ⚙️ Configuration

| Environment variable | Default          | Description                        |
|----------------------|------------------|------------------------------------|
| `OUTPUT_FILE`        | `epg_merged.xml` | Path/name of the merged output     |
| `FETCH_TIMEOUT`      | `30`             | Per-source download timeout (secs) |

Override these in `.github/workflows/update_epg.yml` under the `env:` block.

---

## 📅 Change the schedule

Edit the cron expression in `.github/workflows/update_epg.yml`:

```yaml
schedule:
  - cron: "0 4 * * *"   # Every day at 04:00 UTC
```

Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

---

## 📡 Using the merged EPG

After the first run, the raw URL to your merged file will be:

```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/epg_merged.xml
```

Paste this into your IPTV player (TiviMate, Jellyfin, Plex, etc.) as the EPG source.

---

## 🛠 Run locally

```bash
python merge_epg.py
```

Requires Python 3.12+ (stdlib only — no `pip install` needed).
