import sys
import os
import time
import unicodedata

# Thêm đường dẫn Src vào sys.path để import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Src')))
from utils import get_driver, logger, retry_click
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WebFormParser:
    def __init__(self, url, headless=True):
        self.url = url
        self.headless = headless

    def parse(self):
        logger.info(f"Đang khởi động Web Parser cho URL: {self.url}")
        driver = get_driver(headless=self.headless)
        form_structure = {
            "form_url": self.url,
            "questions": []
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
                    
                    # Tránh duplicate
                    if any(q['id'] == question_text for q in form_structure["questions"]):
                        continue

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
                        
                        rows = []
                        for val, aria in valid_choices:
                            row_name = aria.replace(val, "").strip(" ,:-")
                            if row_name.lower().startswith("hàng "): row_name = row_name[5:].strip(" ,:-")
                            if row_name and row_name not in rows:
                                rows.append(row_name)
                                
                        if rows and columns:
                            form_structure["questions"].append({
                                "id": question_text,
                                "text": question_text,
                                "type": "grid",
                                "rows": rows,
                                "columns": columns
                            })
                            for c in choices:
                                try: driver.execute_script("arguments[0].click();", c)
                                except: pass
                            continue

                    # XỬ LÝ 2: TRẮC NGHIỆM BÌNH THƯỜNG (Radio / Checkbox)
                    if len(set(data_values)) > 0:
                        options = list(dict.fromkeys(data_values))
                        q_type = "checkbox" if item.find_elements(By.XPATH, ".//div[@role='checkbox']") else "radio"
                        
                        form_structure["questions"].append({
                            "id": question_text,
                            "text": question_text,
                            "type": q_type,
                            "options": options
                        })
                        
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
                                form_structure["questions"].append({
                                    "id": question_text,
                                    "text": question_text,
                                    "type": "dropdown",
                                    "options": options
                                })
                                continue
                        except:
                            pass
                    
                    # XỬ LÝ 4: Ô ĐIỀN CHỮ
                    text_inputs = item.find_elements(By.XPATH, ".//input[@type='text'] | .//input[@type='email'] | .//input[@type='number'] | .//textarea")
                    if text_inputs:
                        form_structure["questions"].append({
                            "id": question_text,
                            "text": question_text,
                            "type": "text",
                            "default_text": "Văn bản mẫu"
                        })
                        
                        try:
                            driver.execute_script("arguments[0].value = arguments[1];", text_inputs[0], "Văn bản mẫu")
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", text_inputs[0])
                        except:
                            pass
                        continue

                # --- XỬ LÝ CHUYỂN TRANG TỰ ĐỘNG ---
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
                        logger.info(" Đã đến trang cuối. Hoàn tất quét form!")
                        break
                        
                except Exception as e:
                    logger.error(f"Lỗi khi tìm nút chuyển trang: {e}")
                    break
                    
            return form_structure
            
        except Exception as e:
            logger.error(f"Lỗi Parser chung: {e}")
            raise e
        finally:
            driver.quit()

if __name__ == "__main__":
    parser = WebFormParser("https://docs.google.com/forms/d/e/...", headless=True)
    res = parser.parse()
    print(res)
