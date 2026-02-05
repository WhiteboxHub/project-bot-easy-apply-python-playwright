"""
LinkedIn Profile Setup
Creates a persistent browser profile with your LinkedIn login saved
This helps avoid detection and you won't need to login every time
"""

import os
from playwright.sync_api import sync_playwright
import time

def setup_linkedin_profile():
    """
    Opens a browser, lets you login to LinkedIn, and saves the session
    """
    print("=" * 60)
    print("LINKEDIN PROFILE SETUP")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Open a browser window")
    print("2. Navigate to LinkedIn")
    print("3. Let you login manually")
    print("4. Save your session for future use")
    print()
    print("=" * 60)
    
    # Profile directory
    profile_dir = os.path.abspath("./linkedin_profile")
    
    if os.path.exists(profile_dir):
        print(f"\n  Profile directory already exists: {profile_dir}")
        response = input("Do you want to overwrite it? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        import shutil
        shutil.rmtree(profile_dir)
    
    print(f"\n Creating profile directory: {profile_dir}")
    os.makedirs(profile_dir, exist_ok=True)
    
    with sync_playwright() as p:
        print("\n Launching browser...")
        
        # Launch with persistent context (this is the key!)
        context = p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ],
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        print("\n Navigating to LinkedIn login...")
        page.goto("https://www.linkedin.com/login")
        
        print("\n" + "=" * 60)
        print("PLEASE LOGIN TO LINKEDIN IN THE BROWSER WINDOW")
        print("=" * 60)
        print()
        print("Steps:")
        print("1. Enter your email and password")
        print("2. Complete any 2FA/verification if prompted")
        print("3. Make sure you see your LinkedIn feed")
        print("4. Come back here and press Enter")
        print()
        
        input("Press Enter once you're logged in and see your feed...")
        
        # Verify login
        print("\n Verifying login...")
        current_url = page.url
        
        if "feed" in current_url or "mynetwork" in current_url:
            print(" Login successful!")
        else:
            print("  Warning: You might not be logged in properly.")
            print(f"Current URL: {current_url}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Please login and try again.")
                context.close()
                return
        
        # Test job search
        print("\n🔍 Testing job search...")
        try:
            page.goto("https://www.linkedin.com/jobs/search/?f_LF=f_AL&keywords=Software+Engineer", 
                     wait_until="domcontentloaded", timeout=10000)
            time.sleep(5)
        except Exception as e:
            # LinkedIn might redirect, that's OK
            print(f"   Note: LinkedIn redirected (this is normal): {e}")
            time.sleep(2)
        
        # Check if we can see jobs (try current page)
        try:
            job_cards = page.locator("div.job-card-container, li.jobs-search-results__list-item, ul.scaffold-layout__list-container li").count()
            
            if job_cards > 0:
                print(f"✅ Found {job_cards} job cards - profile is working!")
            else:
                print("⚠️  No job cards found on current page.")
                print("   This is OK - the profile has been saved successfully.")
                print("   LinkedIn might show jobs differently when the bot runs.")
        except Exception as e:
            print(f"   Could not check for job cards: {e}")
            print("   This is OK - the profile has been saved successfully.")
        
        print("\n" + "=" * 60)
        print("PROFILE SETUP COMPLETE!")
        print("=" * 60)
        print()
        print(f"✅ Profile saved to: {profile_dir}")
        print()
        print("Next steps:")
        print("1. Update config.yaml:")
        print(f"   profile_path: '{profile_dir}'")
        print()
        print("2. Run the bot:")
        print("   python main.py")
        print()
        print("The browser will close in 5 seconds...")
        time.sleep(5)
        
        context.close()
        
        # Update config.yaml automatically
        print("\n📝 Updating config.yaml...")
        try:
            with open("config.yaml", "r") as f:
                config_content = f.read()
            
            # Replace profile_path line
            import re
            config_content = re.sub(
                r"profile_path:.*",
                f"profile_path: '{profile_dir}'",
                config_content
            )
            
            with open("config.yaml", "w") as f:
                f.write(config_content)
            
            print("✅ config.yaml updated automatically!")
        except Exception as e:
            print(f"⚠️  Could not update config.yaml automatically: {e}")
            print(f"Please manually set: profile_path: '{profile_dir}'")
        
        print("\n🎉 All done! You can now run the bot with your saved profile.")


if __name__ == "__main__":
    try:
        setup_linkedin_profile()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
