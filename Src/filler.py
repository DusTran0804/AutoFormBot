import json
import random
import time
import unicodedata
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from utils import get_driver, logger, retry_click

class FormFiller:
    def __init__(self, config_file="config.json", headless=False, random_mode=False):
        self.config_file = config_file
        self.headless = headless
        self.random_mode = random_mode
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            self.url = self.config.get("form_url")
            self.answers = self.config.get("answers", {})
            logger.info(f"Loaded config from {self.config_file}")
            
            self.cleaned_answers = {}
            for k, v in self.answers.items():
                clean_k = "".join(e for e in k if e.isalnum()).lower()
                self.cleaned_answers[clean_k] = (k, v)
        except FileNotFoundError:
            logger.error(f"Configuration file '{self.config_file}' not found.")
            raise

    def fill(self, num_submissions=1, max_workers=1):
        import concurrent.futures
        logger.info(f"🚀 Bắt đầu điền form tự động: {self.url} (Headless: {self.headless}, Random: {self.random_mode})")
        
        submissions_per_worker = [num_submissions // max_workers + (1 if x < num_submissions % max_workers else 0) for x in range(max_workers)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, count in enumerate(submissions_per_worker):
                if count > 0:
                    futures.append(executor.submit(self._fill_worker_task, i + 1, count))
            for future in concurrent.futures.as_completed(futures):
                try: future.result()
                except Exception as e: logger.error(f"Worker thread error: {e}")

    def _fill_worker_task(self, worker_id, num_submissions):
        driver = get_driver(headless=self.headless)
        try:
            for submission in range(1, num_submissions + 1):
                logger.info(f"[Worker {worker_id}] --- Đang xử lý form {submission}/{num_submissions} ---")
                if submission == 1:
                    driver.get(self.url)
                
                self._fill_single_form(driver)
                
                if submission < num_submissions:
                    try:
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'viewform')]")))
                        another_link = driver.find_elements(By.XPATH, "//a[contains(., 'Submit another response') or contains(., 'Gửi') or contains(@href, 'viewform')]")
                        if another_link:
                            driver.execute_script("arguments[0].click();", another_link[-1])
                        else:
                            driver.get(self.url)
                    except:
                        driver.get(self.url)
                    time.sleep(0.5) 
        except Exception as e:
            logger.error(f"[Worker {worker_id}] Lỗi: {e}")
        finally:
            try: driver.quit()
            except: pass

    def _fill_single_form(self, driver):
        try:
            driver.implicitly_wait(0)
            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.find_elements(By.XPATH, "//div[@role='listitem']") or d.find_elements(By.XPATH, "//div[@role='button']")
                    )
                except: pass
                time.sleep(0.5)
                
                items = driver.find_elements(By.XPATH, "//div[@role='listitem']")
                
                if items:
                    logger.info(f"Đã tìm thấy {len(items)} câu hỏi trên trang này.")
                    for i in range(len(items)):
                        # VÒNG LẶP BẢO VỆ CHỐNG LỖI STALE ELEMENT
                        attempts = 0
                        while attempts < 3:
                            try:
                                item = driver.find_elements(By.XPATH, "//div[@role='listitem']")[i]
                                heading = item.find_element(By.XPATH, ".//div[@role='heading']")
                                question_text = heading.text.strip()
                                if question_text.endswith(" *"): question_text = question_text[:-2]
                                elif question_text.endswith("*"): question_text = question_text[:-1]
                                
                                cleaned_qt = "".join(e for e in question_text if e.isalnum()).lower()
                                matched_key = None
                                answer_data = None
                                
                                for clean_k, (orig_k, data) in self.cleaned_answers.items():
                                    if clean_k in cleaned_qt or cleaned_qt == clean_k or cleaned_qt.startswith(clean_k):
                                        matched_key = orig_k
                                        answer_data = data
                                        break
                                        
                                if not matched_key: 
                                    break # Không trùng khớp -> Bỏ qua câu hỏi, thoát vòng lặp bảo vệ
                                
                                # 1. Bảng Matrix (Grid)
                                if isinstance(answer_data, dict) and any(isinstance(v, dict) for v in answer_data.values()):
                                    for row_key, row_weights in answer_data.items():
                                        target_col = random.choices(list(row_weights.keys()), weights=list(row_weights.values()), k=1)[0]
                                        for r in item.find_elements(By.XPATH, ".//div[@role='radio'] | .//div[@role='checkbox']"):
                                            if r.get_attribute("aria-disabled") == "true" or r.get_attribute("aria-hidden") == "true": continue
                                            aria_label = r.get_attribute("aria-label") or ""
                                            data_value = r.get_attribute("data-value") or r.get_attribute("data-answer-value") or ""
                                            cl_row = "".join(e for e in row_key if e.isalnum()).lower()
                                            cl_aria = "".join(e for e in aria_label if e.isalnum()).lower()
                                            if target_col == data_value and cl_row in cl_aria:
                                                retry_click(r)
                                                break
                                    break # Điền xong -> thoát vòng lặp bảo vệ
                                
                                # 2. Trắc nghiệm Radio
                                radios = item.find_elements(By.XPATH, ".//div[@role='radio']")
                                if radios:
                                    options = [r.get_attribute("data-value") or r.get_attribute("data-answer-value") for r in radios if (r.get_attribute("data-value") or r.get_attribute("data-answer-value")) is not None and r.get_attribute("aria-disabled") != "true"]
                                    if self.random_mode and options: target_val = random.choice(options)
                                    elif isinstance(answer_data, dict) and answer_data:
                                        choices, weights = list(answer_data.keys()), list(answer_data.values())
                                        target_val = random.choices(choices, weights=weights, k=1)[0]
                                    else: target_val = answer_data[0] if isinstance(answer_data, list) and answer_data else answer_data
                                    
                                    self._interact_radio_or_checkbox(driver, radios, target_val, question_text, "radio")
                                    break # Điền xong -> thoát vòng lặp bảo vệ
                                    
                                # 3. Dropdown (Menu thả xuống)
                                listboxes = item.find_elements(By.XPATH, ".//div[@role='listbox']")
                                if listboxes:
                                    listbox = listboxes[0]
                                    if isinstance(answer_data, dict) and answer_data:
                                        choices, weights = list(answer_data.keys()), list(answer_data.values())
                                        target_val = random.choices(choices, weights=weights, k=1)[0]
                                    else: target_val = answer_data[0] if isinstance(answer_data, list) and answer_data else answer_data
                                        
                                    retry_click(listbox)
                                    time.sleep(0.3)
                                    
                                    options = driver.find_elements(By.XPATH, f"//div[@role='option'][@data-value='{target_val}'] | //div[@role='option']//span[text()='{target_val}'] | //div[@role='option'][contains(., '{target_val}')]")
                                    
                                    if options:
                                        for opt in reversed(options):
                                            try:
                                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", opt)
                                                driver.execute_script("arguments[0].click();", opt)
                                                break
                                            except: pass
                                    time.sleep(0.1)
                                    break # Điền xong -> thoát vòng lặp bảo vệ

                                # 4. Checkbox nhiều lựa chọn
                                checkboxes = item.find_elements(By.XPATH, ".//div[@role='checkbox']")
                                if checkboxes:
                                    options = [c.get_attribute("data-value") or c.get_attribute("data-answer-value") for c in checkboxes if (c.get_attribute("data-value") or c.get_attribute("data-answer-value")) is not None and c.get_attribute("aria-disabled") != "true"]
                                    if self.random_mode and options:
                                        target_vals = random.sample(options, random.randint(1, len(options)))
                                    elif isinstance(answer_data, dict) and answer_data:
                                        target_vals = [choice for choice, prob in answer_data.items() if random.random() < (prob / 100.0 if float(prob) > 1 else float(prob))]
                                        if not target_vals and answer_data:
                                            target_vals.append(random.choices(list(answer_data.keys()), weights=list(answer_data.values()), k=1)[0])
                                    else: target_vals = answer_data if isinstance(answer_data, list) else [answer_data]
                                    
                                    for target_val in target_vals:
                                        if target_val:
                                           item = driver.find_elements(By.XPATH, "//div[@role='listitem']")[i]
                                           self._interact_radio_or_checkbox(driver, item.find_elements(By.XPATH, ".//div[@role='checkbox']"), target_val, question_text, "checkbox")
                                    break # Điền xong -> thoát vòng lặp bảo vệ
                                
                                # 5. Text (Điền chữ)
                                inputs = item.find_elements(By.XPATH, ".//input[@type='text'] | .//input[@type='email'] | .//input[@type='number'] | .//textarea")
                                if inputs:
                                    val = "Random Test " + str(random.randint(1000, 9999)) if self.random_mode else str(answer_data)
                                    input_field = inputs[0]
                                    try:
                                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", input_field)
                                        driver.execute_script("arguments[0].value = '';", input_field)
                                        driver.execute_script("arguments[0].value = arguments[1];", input_field, val)
                                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_field)
                                    except:
                                        input_field.clear()
                                        input_field.send_keys(val)
                                    break # Điền xong -> thoát vòng lặp bảo vệ
                                    
                                break # Dự phòng không lọt vào loại nào
                                
                            except StaleElementReferenceException:
                                attempts += 1
                                logger.warning(f"Giao diện bị làm mới ngầm (Stale Element). Đang tự động thử lại câu {i+1} (lần {attempts})...")
                                time.sleep(0.5)
                            except Exception as e:
                                # Bỏ qua các lỗi khác để không làm sập tiến trình
                                break
                
                # CHUYỂN TRANG HOẶC HOÀN TẤT
                action = self._submit_or_next(driver)
                if action == 'submit':
                    break
                    
        except Exception as e:
            logger.error(f"Lỗi khi điền form: {e}")

    def _interact_radio_or_checkbox(self, driver, elements, target_val, question_text, input_type):
        for el in elements:
            if el.get_attribute("aria-disabled") == "true" or el.get_attribute("aria-hidden") == "true": continue
            val = el.get_attribute("data-value") or el.get_attribute("data-answer-value") or ""
            if val == target_val or el.get_attribute("aria-label") == target_val or target_val in (el.get_attribute("aria-label") or ""):
                # Bảo vệ chống Uncheck đối với Checkbox nếu click thử lại
                if input_type == "checkbox" and el.get_attribute("aria-checked") == "true":
                    pass
                else:
                    retry_click(el)
                break

    def _submit_or_next(self, driver):
        try:
            buttons = driver.find_elements(By.XPATH, "//div[@role='button']")
            for b in buttons:
                try:
                    raw_text = getattr(b, 'text', '').strip()
                    if not raw_text:
                        raw_text = str(b.get_attribute("innerText") or "").strip()
                    if not raw_text:
                        raw_text = str(b.get_attribute("textContent") or "").strip()
                        
                    text = unicodedata.normalize('NFC', raw_text).lower()
                    
                    if 'tiếp' in text or 'next' in text:
                        retry_click(b)
                        logger.info(" Đã bấm nút 'Tiếp'. Đang tải trang sau...")
                        time.sleep(1)
                        return 'next'
                    if 'gửi' in text or 'submit' in text or 'send' in text:
                        retry_click(b)
                        logger.info("✅ Đã bấm nút 'Gửi'. Hoàn thành form!")
                        time.sleep(1)
                        return 'submit'
                except Exception:
                    continue
                    
            if buttons:
                logger.info("⚠️ Không nhận diện được chữ trên nút, đang tiến hành bấm mù nút cuối trang...")
                retry_click(buttons[-1])
                time.sleep(1)
                return 'submit'
                
            logger.warning("Không tìm thấy nút Tiếp hoặc Gửi nào. Buộc dừng.")
            return 'submit'
        except Exception as e:
            logger.error(f"Lỗi khi xử lý nút bấm cuối trang: {e}")
            return 'submit'
