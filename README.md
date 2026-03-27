# AutoFormBot 🤖📋

AutoFormBot is a complete, production-ready Python project that automatically parses and fills Google Forms using a configuration file. It uses Selenium with smart explicit waits to navigate dynamic content seamlessly.

## 🎯 Features

- **Form Parsing**: Automatically extract questions, types, and options and generate a config template.
- **Form Filling**: Fill text fields, single-choice (radio), and multi-choice (checkboxes) dynamically.
- **Headless Mode**: Run silently in the background without launching a visible browser.
- **Random Mode**: Easily load-test forms by randomly selecting available choices and generating dummy text.
- **Robustness**: Implements smart retries, explicit waits, and gracefully handles missing questions.

## 📦 Installation Steps

1. **Clone or Download the Project.**
2. **Ensure Python 3.10+ is installed.**
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

*Note: You do not need to download a ChromeDriver manually; `webdriver-manager` will automatically handle it for you under the hood.*

## 🚀 How to Run

Launch the interactive CLI by running in your terminal:
```bash
python main.py
```

### Steps to Automate a Form:

1. **Parse the Form:** Select Option `1` in the menu and paste your Google Form URL. This automatically interacts with the form and generates your schema as `config_template.json` in the project directory.
2. **Create Configuration:** Copy `config_template.json` to a new file named `config.json` and fill in your desired answers.
   - Text fields require just a string: `"Your Name": "Alice"`
   - Radio and Checkboxes require a list of your exact choices: `"Your Color": ["Red"]`
3. **Fill the Form:** Run the bot, select Option `2` (or `3` for testing using random auto-generated answers), and point it to your `config.json`. The bot will automatically inject your answers and submit the form.

## 📄 Example Usage

### `config.json` format:
```json
{
    "form_url": "https://docs.google.com/forms/d/e/1FAIpQLSc...",
    "answers": {
        "What is your name?": "John Doe",
        "Which color do you like?": ["Blue"],
        "Select your hobbies": ["Reading", "Traveling"],
        "Additional feedback": "This bot is awesome!"
    }
}
```

## ⚠️ Notes About Google Form Structure Changes

Google Forms dynamically generates its DOM structure which could change over time. 
* Currently, the bot parses form elements primarily by searching for `div[@role='listitem']`, roles for headers, input tags for strings, and roles for radios/checkboxes matching internal `data-value` and `aria-label` attributes.
* **If Google updates their HTML structure significantly, the XPath selectors in `parser.py` and `filler.py` will have to be updated to match the new structure.**
