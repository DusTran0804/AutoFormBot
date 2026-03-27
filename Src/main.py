import sys
from parser import FormParser
from filler import FormFiller

def print_menu():
    print("\n=============================================")
    print("🤖 AutoFormBot Menu - Google Forms Automation")
    print("=============================================")
    print("1. Parse Form & Generate Template (config_template.json)")
    print("2. Fill Form (Standard Mode)")
    print("3. Fill Form (Random Mode for Testing)")
    print("4. Exit")
    print("=============================================")

def main():
    while True:
        print_menu()
        choice = input("Select an option (1-4): ").strip()
        
        if choice == '1':
            url = input("Enter Google Form URL: ").strip()
            print("⏳ Parsing form...")
            try:
                # ✅ FIX: bỏ num_pages
                parser = FormParser(url)
                parser.parse()
            except Exception as e:
                print(f"❌ Error during parsing: {e}")
                
        elif choice == '2':
            config_file = input("Enter config file path [config.json]: ").strip() or "config.json"
            headless_input = input("Run in headless mode? (y/n) [n]: ").strip().lower()
            headless = headless_input == 'y'
            num_input = input("Enter number of submissions [1]: ").strip()
            num_submissions = int(num_input) if num_input.isdigit() else 1
            workers_input = input("Enter number of concurrent windows (requires Chrome for >1) [1]: ").strip()
            max_workers = int(workers_input) if workers_input.isdigit() else 1
            
            print(f"🚀 Running Form Filler (Standard Mode) for {num_submissions} submission(s) across {max_workers} thread(s)...")
            try:
                filler = FormFiller(config_file=config_file, headless=headless, random_mode=False)
                filler.fill(num_submissions=num_submissions, max_workers=max_workers)
            except Exception as e:
                print(f"❌ Error: {e}")
            
        elif choice == '3':
            config_file = input("Enter config file path [config.json]: ").strip() or "config.json"
            headless_input = input("Run in headless mode? (y/n) [n]: ").strip().lower()
            headless = headless_input == 'y'
            num_input = input("Enter number of submissions [1]: ").strip()
            num_submissions = int(num_input) if num_input.isdigit() else 1
            workers_input = input("Enter number of concurrent windows (requires Chrome for >1) [1]: ").strip()
            max_workers = int(workers_input) if workers_input.isdigit() else 1
            
            print(f"🧪 Running Form Filler (Random Mode) for {num_submissions} submission(s) across {max_workers} thread(s)...")
            try:
                filler = FormFiller(config_file=config_file, headless=headless, random_mode=True)
                filler.fill(num_submissions=num_submissions, max_workers=max_workers)
            except Exception as e:
                print(f"❌ Error: {e}")
            
        elif choice == '4':
            print("👋 Exiting AutoFormBot. Goodbye!")
            sys.exit(0)
        else:
            print("⚠️ Invalid option. Please select 1-4.")

if __name__ == "__main__":
    main()