# Setup Guide: GLiNER + Resume Configuration

## Step 1: Install GLiNER (Optional but Recommended)

GLiNER helps the bot understand questions better. If not installed, bot falls back to keyword matching (which works but is less accurate).

### Installation:

```bash
pip install gliner
```

**Note:** GLiNER will download a ~500MB model on first run. If you don't want this, skip GLiNER and use keyword matching only (already working).

---

## Step 2: Configure Resume Paths

### Option A: Using `candidates.yaml` (Multi-Profile)

Edit `config/candidates.yaml`:

```yaml
candidates:
  - id: candidate_001
    name:  "user_name"
    enabled: true
    
    # Resume paths
    uploads:
      Resume: ./assets/candidates/candidate_001/resume.pdf
      Cover Letter: ./assets/candidates/candidate_001/cover_letter.pdf  # Optional
```

**Create the folder structure:**
```
assets/
├── candidates/
│   ├── candidate_001/
│   │   ├── resume.pdf          ← Your resume here
│   │   └── cover_letter.pdf    ← Optional
```

### Option B: Using `config.yaml` (Legacy)

Edit `config.yaml`:

```yaml
uploads:
  Resume: ./assets/resume.pdf
  Cover Letter: ./assets/cover_letter.pdf  # Optional
```

**Create the folder:**
```
assets/
├── resume.pdf          ← Your resume here
├── cover_letter.pdf    ← Optional
```

---

## Step 3: Add Your Resume

**Windows:**
```powershell
# Create folders
mkdir assets\candidates\candidate_001

# Copy your resume there
# Place your resume.pdf in: assets\candidates\candidate_001\resume.pdf
```

**Verify paths in YAML match your actual files!**

---

## Step 4: Fill Profile Data

Edit `config/candidates.yaml` → `profile_data` section:

```yaml
profile_data:
  # Contact
  full_name: "user_name"
  email: "usermail@gmail.com"
  phone: "1234567890"
  country_code: "India (+91)"
  
  # Experience
  years_experience: "3"
  years_python: "3"
  years_javascript: "2"
  years_react: "2"
  
  # Work Authorization
  sponsorship_required: "No"
  authorized_to_work: "Yes"
  willing_to_relocate: "Yes"
  
  # Salary
  current_salary: "800000"
  expected_salary: "1200000"
  
  # Links
  linkedin_url: "https://www.linkedin.com/in/user_name"
  github_url: "https://github.com/user_name"
  portfolio_url: "https://user_name.dev"
  
  # Education
  degree: "Bachelor of Technology"
  university: "Your University"
  graduation_year: "2021"
```

**Add more fields as you encounter new questions!**

---

## Step 5: Test Without GLiNER First

**Run the bot:**
```bash
python main.py
```

**What to expect:**
1. Select your profile
2. Login
3. Bot finds jobs and applies
4. For **known questions** → Auto-filled from `profile_data`
5. For **unknown questions** → Bot asks you to fill

**If keyword matching works well, you might not need GLiNER!**

---

## Step 6: (Optional) Enable GLiNER for Better Matching

**Only do this if:**
- Keyword matching misses too many questions
- You want more intelligent question understanding

### Install:
```bash
pip install gliner
```

### Update `smart_form_filler.py`:

The code already has GLiNER support but it's disabled. To enable, uncomment lines in `SmartFormFiller.__init__`:

```python
# Try to load GLiNER
try:
    from gliner import GLiNER
    self.gliner = GLiNER.from_pretrained("urchade/gliner_base")
    logger.info("GLiNER loaded successfully", step="init")
except ImportError:
    logger.warning("GLiNER not installed, using keyword matching only", step="init")
    self.gliner = None
except Exception as e:
    logger.warning(f"Could not load GLiNER: {e}", step="init")
    self.gliner = None
```

**First run will download ~500MB model.**

---

## Step 7: Monitor and Improve

### As bot runs:

1. **Unknown questions appear** → You fill manually
2. **Bot saves answers** to `learned_answers`
3. **Next application** → Bot reuses saved answers

### Continuously improve `profile_data`:

Every time bot asks you a new question, add it to `profile_data`:

```yaml
profile_data:
  # ... existing fields ...
  
  # New fields you discovered
  preferred_work_location: "Remote"
  notice_period: "2 weeks"
  referral_source: "LinkedIn"
```

---

## Quick Start Checklist:

- [ ] Create `assets/candidates/candidate_001/` folder
- [ ] Put `resume.pdf` in that folder
- [ ] Update `uploads.Resume` path in `candidates.yaml`
- [ ] Fill `profile_data` section with your info
- [ ] Run `python main.py`
- [ ] Monitor first few applications
- [ ] Add new fields to `profile_data` as needed
- [ ] (Optional) Install GLiNER if keyword matching isn't enough

---

## Current Status:

✅ **No GLiNER needed initially** - Keyword matching works well  
✅ **Resume upload ready** - Just need correct path  
✅ **Human-in-loop ready** - Bot asks for unknown fields  
✅ **Answer learning ready** - Saves your responses  

**Start with keyword matching, add GLiNER later if needed!**

---

## Troubleshooting:

### Resume not uploading?
- Check path in YAML: `./assets/candidates/candidate_001/resume.pdf`
- Verify file exists at that location
- Use forward slashes `/` even on Windows

### Bot asks too many questions?
- Fill more fields in `profile_data`
- Check logs to see which questions are asked
- Add those fields to YAML

### Want better question understanding?
- Install GLiNER: `pip install gliner`
- Wait for model download (~500MB)
- Restart bot

---

**Ready to go! Start with Step 2 (configure resume paths).**
