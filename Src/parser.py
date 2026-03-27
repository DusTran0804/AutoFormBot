import json
import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import get_driver, logger, retry_click

class FormParser:
    def __init__(self, url, headless=False):
        self.url = url
        self.headless = headless

    def _get_user_weights(self, question_text, options):
        print(f"\n" + "="*60)
        print(f" Câu hỏi: {question_text}")
        print(f" Lựa chọn: {options}")
        
        while True:
            try:
                user_input = input("Nhập tỷ lệ % cách nhau bằng dấu phẩy (vd: 50,30,20)\nHoặc nhấn ENTER để chia đều (Tự động loại bỏ Mục khác): ").strip()
            except EOFError:
                user_input = "" # Phòng ngừa lỗi môi trường terminal
                
            if not user_input:
                valid_opts = [o for o in options if o != "__other_option__" and o != "Mục khác:"]
                if valid_opts:
                    weight = round(100.0 / len(valid_opts), 1)
                    return {opt: (weight if opt in valid_opts else 0.0) for opt in options}
                else:
                    weight = round(100.0 / len(options), 1)
                    return {opt: weight for opt in options}
            
            parts = [p.strip() for p in user_input.split(',')]
            if len(parts) != len(options):
                print(f"⚠️ LỖI: Câu này có {len(options)} lựa chọn, nhưng bạn mới nhập {len(parts)} số. Vui lòng nhập lại!")
                continue
            
            try:
                weights = [float(p) for p in parts]
                return {opt: w for opt, w in zip(options, weights)}
            except ValueError:
                print("⚠️ LỖI: Chỉ được nhập số và dấu phẩy. Thử lại nhé!")

    def parse(self):
        logger.info(f"Đang khởi động Form Parser Tương Tác cho URL: {self.url}")
        driver = get_driver(headless=self.headless)
        config_template = {
            "form_url": self.url,
            "answers": {}
        }
        
        try:
            driver.get(self.url)
            driver.implicitly_wait(0)
            time.sleep(3)
            
            page_num = 1
            while True:
                logger.info(f"\n--- ĐANG QUÉT TRANG {page_num} ---")
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.find_elements(By.XPATH, "//div[@role='listitem']") or d.find_elements(By.XPATH, "//div[@role='button']")
                    )
                except: pass
                time.sleep(1)
                
                items = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                
                for item in items:
                    try:
                        if not item.is_displayed():
                            continue
                            
                        heading = item.find_element(By.XPATH, ".//div[@role='heading']")
                        question_text = heading.text.strip()
                        if question_text.endswith(" *"): question_text = question_text[:-2]
                        elif question_text.endswith("*"): question_text = question_text[:-1]
                        question_text = question_text.strip()
                    except:
                        continue
                    
                    if not question_text: continue
                    
                    choices = item.find_elements(By.XPATH, ".//div[@role='radio'] | .//div[@role='checkbox']")
                    data_values = []
                    valid_choices = []
                    
                    for c in choices:
                        val = c.get_attribute("data-value") or c.get_attribute("data-answer-value")
                        aria = c.get_attribute("aria-label") or ""
                        if val and val not in ["true", "false"] and not str(val).startswith("Đã chọn"):
                            data_values.append(val)
                            valid_choices.append((val, aria))
                    
                    # XỬ LÝ 1: CÂU HỎI BẢNG (GRID)
                    if len(data_values) > 0 and len(data_values) != len(set(data_values)):
                        columns = list(dict.fromkeys(data_values)) 
                        print(f"\n[DẠNG BẢNG MA TRẬN]")
                        col_weights = self._get_user_weights(question_text, columns)
                        
                        grid_data = {}
                        for val, aria in valid_choices:
                            row_name = aria.replace(val, "").strip(" ,:-")
                            if row_name.lower().startswith("hàng "): row_name = row_name[5:].strip(" ,:-")
                            if row_name:
                                if row_name not in grid_data: grid_data[row_name] = {}
                                grid_data[row_name][val] = col_weights[val]
                                
                        if grid_data:
                            config_template["answers"][question_text] = grid_data
                            for c in choices:
                                try: driver.execute_script("arguments[0].click();", c)
                                except: pass
                            continue

                    # XỬ LÝ 2: TRẮC NGHIỆM BÌNH THƯỜNG
                    if len(set(data_values)) > 0:
                        options = list(dict.fromkeys(data_values))
                        config_template["answers"][question_text] = self._get_user_weights(question_text, options)
                        if choices:
                            try: driver.execute_script("arguments[0].click();", choices[0])
                            except: pass
                        continue
                    
                    # XỬ LÝ 3: DROPDOWN
                    listboxes = item.find_elements(By.XPATH, ".//div[@role='listbox']")
                    if listboxes:
                        try:
                            listbox = listboxes[0]
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", listbox)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", listbox)
                            time.sleep(1)
                            
                            dropdown_options = driver.find_elements(By.XPATH, "//div[@role='option']")
                            options = []
                            valid_elements = []
                            for opt in dropdown_options:
                                val = opt.get_attribute("data-value")
                                if val and val not in ["Chọn", "Choose", ""]:
                                    if val not in options: 
                                        options.append(val)
                                        valid_elements.append(opt)
                                        
                            if valid_elements:
                                driver.execute_script("arguments[0].click();", valid_elements[0])
                            else:
                                driver.execute_script("arguments[0].click();", listbox)
                            time.sleep(0.5)
                            
                            if options:
                                print(f"\n[MENU THẢ XUỐNG]")
                                config_template["answers"][question_text] = self._get_user_weights(question_text, options)
                                continue
                        except:
                            pass
                    
                    # XỬ LÝ 4: Ô ĐIỀN CHỮ
                    text_inputs = item.find_elements(By.XPATH, ".//input[@type='text'] | .//input[@type='email'] | .//input[@type='number'] | .//textarea")
                    if text_inputs:
                        print(f"\n" + "="*60)
                        print(f"❓ Câu hỏi (Điền chữ/số): {question_text}")
                        try:
                            user_text = input(" Nhập nội dung bạn muốn điền (Hoặc nhấn ENTER để dùng 'Văn bản mẫu'): ").strip()
                        except EOFError:
                            user_text = ""
                            
                        final_text = user_text if user_text else "Văn bản mẫu"
                        config_template["answers"][question_text] = final_text
                        
                        try:
                            driver.execute_script("arguments[0].value = arguments[1];", text_inputs[0], final_text)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", text_inputs[0])
                        except:
                            pass
                        continue

                # =========================================================
                # FIX BỆNH 2: TẠM DỪNG ĐỂ BẠN KIỂM SOÁT VIỆC CHUYỂN TRANG
                # =========================================================
                print("\n")
                try:
                    input("⏸️ ĐÃ QUÉT XONG TRANG NÀY.\n Hãy nhìn lên trình duyệt, nếu form có rẽ nhánh, bạn có thể TỰ TAY click đổi đáp án để điều hướng nhánh.\n👉 Xong xuôi, nhấn ENTER tại đây để Bot tự bấm sang trang tiếp theo... ")
                except: pass

                # --- XỬ LÝ CHUYỂN TRANG (TÌM NÚT TIẾP) ---
                try:
                    next_buttons = driver.find_elements(By.XPATH, "//div[@role='button'][.//span[contains(text(), 'Tiếp') or contains(text(), 'Next')]]")
                    found_next = False
                    
                    if next_buttons:
                        retry_click(next_buttons[0])
                        found_next = True
                    else:
                        buttons = driver.find_elements(By.XPATH, "//div[@role='button']")
                        for b in buttons:
                            text = unicodedata.normalize('NFC', str(b.text or "").strip())
                            if 'Tiếp' in text or 'Next' in text:
                                retry_click(b)
                                found_next = True
                                break
                                
                    if found_next:
                        logger.info(f" Đang tải trang {page_num + 1}...")
                        page_num += 1
                        time.sleep(2)
                        continue 
                    else:
                        logger.info(" Đã đến trang cuối cùng. Hoàn tất việc quét form! (Bot tự động không bấm Gửi để bảo vệ data)")
                        break
                        
                except Exception as e:
                    logger.error(f"Lỗi khi tìm nút chuyển trang: {e}")
                    break
                    
            with open("config_template.json", "w", encoding="utf-8") as f:
                json.dump(config_template, f, indent=4, ensure_ascii=False)
            logger.info("🎉 Đã tạo thành công config_template.json với toàn bộ dữ liệu!")
            
        except Exception as e:
            logger.error(f"Lỗi: {e}")
        finally:
            driver.quit()