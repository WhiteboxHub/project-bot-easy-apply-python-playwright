# LinkedIn EasyApply Bot 2.0 - Playwright Edition

A robust, stealthy, and modular bot to automate LinkedIn Easy Apply applications using Playwright.

## 🚀 New Features (Playwright Version)

### 🛡️ Anti-Detection & Human Behavior
*   **Playwright Stealth**: Uses Playwright's native capabilities with custom stealth scripts to bypass bot detection.
*   **Variable Fingerprinting**: Randomizes WebGL, Canvas, user agent, and other browser fingerprints.
*   **Natural Human Behavior**:
    *   **Mouse**: Moves cursor in Bezier curves to mimic physical hand movement.
    *   **Scrolling**: Natural "stuttering" scrolling with random pauses and micro-reversals.
    *   **Typing**: Character-by-character typing with random delays.
*   **Profile Persistence**: Loads your browser profile to maintain cookies and session state.

### ⚡ Reliability & Safeguards
*   **Auto-Waiting**: Playwright's built-in auto-waiting eliminates most stale element issues.
*   **Scroll Tracking**: Robust pagination and scroll tracking to prevent infinite loops.
*   **Execution Safeguards**:
    *   **Max Applications**: Stops after a configurable number of submissions (default: 10).
    *   **Cooldown**: Random sleep between applications (default: 90s).
*   **Dry Run Mode**: Test flows securely without submitting (`dry_run: true`).

### 💾 Data & Security
*   **DuckDB Integration**: Local high-performance SQL database (`data/bot_data.duckdb`).
*   **Secure Credentials**: Loads sensitive data (`username`, `password`) from a `.env` file.
*   **Automatic Migration**: Automatically imports legacy CSV data on first run.

### 🧩 Architecture
*   **Modular Design**: Code is split into `bot/core`, `bot/discovery`, `bot/application`, and `bot/persistence`.
*   **Manual Intervention Mode**: If the bot encounters a field it cannot fill, it will **pause indefinitely**, allowing you to fill it manually. It resumes automatically once the error is cleared.
*   **Structured Logging**: Machine-parseable logs with `job_id`, `step`, and `event` for easier debugging.

---

## 🛠️ Setup

### 1. Prerequisites
*   Python 3.10+
*   Playwright browsers

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Credentials (.env)
Rename `.env.example` to `.env` and add your details. This file is ignored by Git to keep your data safe.
```ini
LINKEDIN_USERNAME=your_email@example.com
LINKEDIN_PASSWORD=your_password
PHONE_NUMBER=1234567890
```

### 4. Configure Bot (config.yaml)
Edit `config.yaml` for job search parameters and execution speed.
```yaml
execution:
  max_applications_per_run: 10
  cooldown_seconds: 5  # Time to wait between applications
  dry_run: true       # Set to false to actually apply
```
*Note: Place your resume and cover letter in the `assets/` folder.*

---

## ▶️ Execution

### Run the Bot
**IMPORTANT**: Close all browser windows before running (if using profile persistence).

```bash
python main.py
```

### Checking Logs
Logs are printed to the console in a structured format:
```
2024-01-20 12:00:00 INFO job_id=12345 step=apply event=success message=Application Submitted
```

### Session Summary
When the bot finishes (or is interrupted), it prints a summary:
```
================ SESSION SUMMARY ================
Attempted:  12
Submitted:  5
Skipped:    6
Failed:     1
=================================================
```

---

## 📂 Project Structure
```
.
├── main.py              # Entry point
├── config.yaml          # Configuration
├── .env                 # Secrets (ignored by git)
├── bot/                 # Source code
│   ├── core/            # Browser, Session, Metrics, Guard
│   ├── discovery/       # Search, Scroll, Job Identity
│   ├── application/     # Workflow, Form Filler
│   ├── persistence/     # Store (DuckDB)
│   └── utils/           # Human Interaction, Logger, Retry
├── data/                # Database (bot_data.duckdb) & Outputs
├── assets/              # Input PDFs (Resume, CL)
└── requirements.txt     # Python dependencies
```

---

## 🎯 Key Differences from Selenium Version

### Advantages of Playwright
1. **Better Stealth**: Playwright is harder to detect than Selenium
2. **Auto-Waiting**: Built-in smart waiting reduces timing issues
3. **Modern API**: Cleaner, more intuitive API
4. **Better Performance**: Faster page loads and interactions
5. **Network Control**: Better control over network requests

### Migration Notes
- Removed `undetected-chromedriver` dependency
- Removed `selenium-stealth` dependency
- Removed `humancursor` dependency (implemented custom Bezier curves)
- All Selenium locators converted to Playwright selectors
- Improved error handling with Playwright's timeout system

---

## 🐛 Troubleshooting

### Browser Not Found
```bash
playwright install chromium
```

### Login Issues
- Check credentials in `.env` file
- If 2FA is enabled, you may need to manually verify on first run
- Consider using profile persistence to avoid repeated logins

### Application Not Submitting
- Check `dry_run` setting in `config.yaml`
- Review logs for specific errors
- Ensure resume/cover letter paths are correct

---

## ⚠️ Disclaimer

This bot is for educational purposes only. Use at your own risk. Automated job applications may violate LinkedIn's Terms of Service. The authors are not responsible for any consequences of using this software.

---

## 📝 License

See LICENSE file for details.
