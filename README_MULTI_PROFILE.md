# 🚀 LinkedIn Easy Apply Bot - Multi-Profile Edition

## ✅ What's New

### 1. **Multi-Candidate Support**
- Use `config/candidates.yaml` to manage multiple profiles
- Each candidate has their own credentials, resumes, and job preferences
- Select profile at startup

### 2. **Smart Form Filling**
- Auto-fills form fields using candidate profile data
- **Human-in-Loop**: If bot doesn't know an answer, it asks you
- **Answer Learning**: Saves your answers for future applications
- No more false submissions!

### 3. **Fixed Bugs**
- ✅ **False Positive Fixed**: Verifies submission success before marking as complete
- ✅ **Dropdown Support**: Uses correct `.select_option()` for dropdowns
- ✅ **Form Filling Order**: Fills fields BEFORE clicking Submit
- ✅ **Email Verification**: Prevents applying with wrong account

---

## 📁 Configuration

### Option 1: Multi-Profile (Recommended)

Edit `config/candidates.yaml`:

```yaml
candidates:
  - id: candidate_001
    name: "Your Name"
    enabled: true
    
    credentials:
      email: "your.email@gmail.com"
      password: ""  # Leave empty to use .env
      phone: "1234567890"
    
    profile_data:
      full_name: "Your Full Name"
      email: "your.email@gmail.com"
      phone: "1234567890"
      country_code: "United States (+1)"
      years_experience: "3"
      sponsorship_required: "No"
      willing_to_relocate: "Yes"
      # Add more fields as needed
    
    search:
      positions:
        - Software Engineer
        - Full Stack Developer
      locations:
        - Remote
        - San Francisco
      experience_level:
        - 2  # Associate
        - 3  # Mid-Senior
    
    uploads:
      Resume: ./assets/candidates/candidate_001/resume.pdf
    
    preferences:
      max_applications_per_run: 50
      cooldown_seconds: 5
      dry_run: false
```

### Option 2: Legacy Mode

Use old `config.yaml` (still supported).

---

## 🎯 How It Works

### 1. **Startup**
```bash
python main.py
```

You'll be prompted to select a profile:
```
SELECT CANDIDATE PROFILE
======================================================================
1. Jane Smit (candidate_001)
2. Jane Smith (candidate_002)
======================================================================
Enter number: 1
```

### 2. **Profile Verification**
Bot asks you to confirm the logged-in account matches:
```
⚠️  PROFILE VERIFICATION
======================================================================
Expected Email: usermail@gmail.com
Please verify the LinkedIn profile in the browser matches this email.
======================================================================
Continue? (yes/no):
```

### 3. **Auto-Fill with Human-in-Loop**

Bot processes each job:
- **Known fields**: Auto-filled from `profile_data`
- **Unknown fields**: Bot pauses and asks you

Example unknown question:
```
======================================================================
⚠️  UNKNOWN QUESTION - HUMAN INPUT NEEDED
======================================================================
Question: What is your expected start date?
======================================================================
Options:
  1. Fill the answer in the BROWSER and press ENTER
  2. Type 'skip' to skip this field
======================================================================
Press ENTER when filled (or type 'skip'):
```

The field will be **highlighted in orange** in the browser. Fill it, press Enter, and the bot continues.

### 4. **Answer Learning**
Your answer is saved to `learned_answers` for future use:
```
✅ Answer 'Immediately' saved for future use!
```

### 5. **Submission Verification**
Bot now verifies submissions:
- ❌ Before: Click Submit → Assume success
- ✅ Now: Click Submit → Wait → Check for errors → Verify modal closed → Mark success

---

## 🔑 Profile Data Fields

Common fields in `profile_data`:

| Field | Example | Used For |
|-------|---------|----------|
| `email` | `john@example.com` | Email fields |
| `phone` | `1234567890` | Phone number |
| `country_code` | `United States (+1)` | Phone country code |
| `years_experience` | `"3"` | Years of experience |
| `years_python` | `"3"` | Python experience |
| `sponsorship_required` | `"No"` | Sponsorship questions |
| `willing_to_relocate` | `"Yes"` | Relocation questions |
| `current_salary` | `"80000"` | Salary fields |
| `portfolio_url` | `https://github.com/user` | Portfolio/website |

Add more fields as you encounter new questions!

---

## 🐛 Troubleshooting

### Issue: Bot doesn't auto-fill dropdown

**Cause**: Field not in `profile_data`  
**Solution**: Answer manually when prompted, it will be saved

### Issue: False positive "Application Submitted"

**Fixed!** Bot now verifies modal closed before marking success.

### Issue: Wrong profile applied

**Solution**: Use email verification prompt - abort if mismatch

### Issue: "No enabled candidates"

**Solution**: Set `enabled: true` in `candidates.yaml`

---

## 📊 Logs

Watch for these key events:

```
✅ Application Submitted Successfully!  # Real success
⚠️ Submit failed - errors appeared       # Validation failed
⚠️ UNKNOWN QUESTION                     # Human input needed
✅ Answer saved for future use!         # Learning happened
```

---

## 🎓 Best Practices

1. **Start with `dry_run: true`** to test without submitting
2. **Fill `profile_data` completely** to minimize human prompts
3. **Use separate resumes per profile** for different roles
4. **Review learned answers** periodically for accuracy
5. **Keep `max_applications_per_run` reasonable** (20-50)

---

## 🚦 Next Steps

1. Fill out your `profile_data` in `candidates.yaml`
2. Run `python main.py`
3. Select your profile
4. Let bot auto-fill known fields
5. Answer unknown questions when prompted
6. Bot learns and gets smarter!

---

## 🔮 Future Enhancements

- [ ] GLiNER integration for smarter question matching
- [ ] Auto-save learned answers to YAML
- [ ] Resume selector based on job keywords
- [ ] Company blacklist per profile
- [ ] Scheduling (run at specific times)

---

**Questions?** Check logs or run `python test_smart_filler.py` to test profile matching.
