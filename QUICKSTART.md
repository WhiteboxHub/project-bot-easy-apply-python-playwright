# Quick Start Guide - LinkedIn EasyApply Bot (Playwright)

## Installation (5 minutes)

### Step 1: Install Python Dependencies
```bash
cd "c:\Users\user_name\Desktop\easy_apply_playwright\project-bot-easy-apply-python-playwright"
pip install -r requirements.txt
```

### Step 2: Install Playwright Browser
```bash
playwright install chromium
```

### Step 3: Configure Credentials
1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your LinkedIn credentials:
   ```ini
   LINKEDIN_USERNAME=your_email@example.com
   LINKEDIN_PASSWORD=your_password
   PHONE_NUMBER=1234567890
   ```

### Step 4: Configure Job Search
Edit `config.yaml`:
```yaml
positions:
  - Software Engineer
  - Python Developer

locations:
  - Remote
  - New York

execution:
  max_applications_per_run: 5
  cooldown_seconds: 5
  dry_run: true  # IMPORTANT: Keep true for testing!
```

### Step 5: Add Your Resume
Place your resume in the `assets/` folder:
- `assets/cv.pdf` (your resume)
- `assets/cl.pdf` (your cover letter, optional)

---

## First Run (Dry Run Mode)

**IMPORTANT**: Always test in dry run mode first!

```bash
python main.py
```

### What to Expect:
1. Browser will open automatically
2. Bot will log into LinkedIn
3. Bot will search for jobs
4. Bot will click "Easy Apply" buttons
5. Bot will fill out forms
6. **Bot will NOT submit** (dry run mode)
7. You'll see a summary at the end

---

## Tips

### Manual Intervention
If the bot encounters a question it can't answer, it will:
- Pause and wait for you
- Display a message in the console
- Resume automatically once you fill the field

### Stopping the Bot
Press `Ctrl+C` to stop the bot gracefully. It will:
- Save all progress
- Print a summary
- Close the browser

### Checking Results
All applications are saved in `data/bot_data.duckdb`. You can query it:
```python
import duckdb
con = duckdb.connect('data/bot_data.duckdb')
print(con.execute('SELECT * FROM applications').fetchdf())
```

---

## Common Issues

### "Browser not found"
```bash
playwright install chromium
```

### "Login failed"
- Check credentials in `.env`
- If you have 2FA, you may need to verify manually on first run

### "No jobs found"
- Check your `positions` and `locations` in `config.yaml`
- Try broader search terms

---

## Next Steps

1. ✅ Test in dry run mode
2. ✅ Review the logs
3. ✅ Check the database
4. ✅ Adjust configuration
5. ✅ Go live with small batches
6. ✅ Monitor and iterate

Happy job hunting! 🚀
