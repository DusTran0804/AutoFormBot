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

### [Option 1] Parse Form & Generate Template (Tạo file cấu hình)
*Dùng khi bạn có một link Google Form mới và muốn tool quét cấu trúc của nó.*
1. Chọn Option 1 và dán link Google Form của bạn vào.
2. Bot sẽ mở trình duyệt và tự động quét từng câu hỏi. Hãy chú ý màn hình Terminal:
   * **Với câu trắc nghiệm/Dropdown/Ma trận:** Nhập tỷ lệ % bạn muốn cho từng đáp án, cách nhau bằng dấu phẩy (vd: `50, 30, 20`).
   * **Nếu muốn chia đều (Nhanh):** Chỉ cần nhấn `ENTER`, Bot tự tính toán chia đều % và ép tùy chọn *"Mục khác (Other)"* về 0%.
   * **Với câu điền chữ/số:** Gõ nội dung bạn muốn điền, hoặc nhấn `ENTER` để xài chữ mặc định ("Văn bản mẫu").
3. **Chốt trạm chuyển trang:** Ở cuối mỗi trang, Bot sẽ tạm dừng. Nếu form có rẽ nhánh logic, hãy tự tay click chọn nhánh mong muốn trên trình duyệt, rồi quay lại Terminal nhấn `ENTER` để Bot quét tiếp.
4. Hoàn tất, tool sẽ sinh ra file `config_template.json`. **Hãy đổi tên file này thành `config.json`** để chuẩn bị cho bước điền form.

### [Option 2] Fill Form (Standard Mode - Điền form theo tỷ lệ)
*Dùng để điền form tự động hàng loạt dựa trên tỷ lệ % đã setup ở Option 1.*
1. Đảm bảo file `config.json` đã sẵn sàng trong thư mục.
2. Chọn Option 2 và thiết lập các thông số:
   * **Headless mode (y/n)?** Nhập `y` nếu muốn Bot chạy ngầm (giúp tăng tốc độ tối đa), hoặc `n` nếu muốn xem trực tiếp trình duyệt tự động click.
   * **Number of submissions:** Số lượng form muốn điền (VD: `100`).
   * **Concurrent windows:** Số luồng chạy song song (VD: Nhập `5` thì Bot sẽ mở 5 tab chạy cùng lúc để tiết kiệm thời gian).

### [Option 3] Fill Form (Random Mode - Chế độ điền bừa)
*Dùng để test hệ thống nhanh với dữ liệu hoàn toàn ngẫu nhiên.*
* Cách thiết lập giống hệt Option 2, nhưng Bot sẽ bỏ qua tỷ lệ % trong file config và tự động **tích bừa/chọn ngẫu nhiên** mọi đáp án trên màn hình. Rất thích hợp để stress-test (ép tải) form.

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
