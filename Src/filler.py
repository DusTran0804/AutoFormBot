import json
import random
import time
import requests
import re
import concurrent.futures
from utils import logger

class FormFiller:
    def __init__(self, config_file="config.json", headless=False, random_mode=False):
        self.config_file = config_file
        # Headless parameter is kept for backward compatibility with `main.py` but unused natively
        self.random_mode = random_mode
        self.load_config()
        self.form_schema = self._extract_form_mapping(self.url)

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            url_raw = self.config.get("form_url", "")
            if "/edit" in url_raw:
                url_raw = url_raw.split("/edit")[0] + "/viewform"
            self.url = url_raw
            self.answers = self.config.get("answers", {})
            logger.info(f"Loaded config from {self.config_file}")
            
            # Khởi tạo bản đồ answers làm sạch string để dễ so khớp
            self.cleaned_answers = {}
            for k, v in self.answers.items():
                clean_k = "".join(e for e in k if e.isalnum()).lower()
                self.cleaned_answers[clean_k] = (k, v)
        except Exception as e:
            logger.error(f"Error loading configuration '{self.config_file}': {e}")
            raise

    def _extract_form_mapping(self, url):
        """
        Quét cấu trúc form 1 lần duy nhất trước khi vòng lặp bắt đầu để lấy entry headers
        """
        logger.info(f"Đang phân tích cấu trúc Entry IDs của Form: {url}")
        schema = []
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            data = None
            for script in soup.find_all('script'):
                if script.string and 'FB_PUBLIC_LOAD_DATA_' in script.string:
                    raw = script.string.split('var FB_PUBLIC_LOAD_DATA_ = ')[1]
                    raw = raw.strip()
                    if raw.endswith(';'):
                        raw = raw[:-1]
                    data = json.loads(raw)
                    break
            
            if not data:
                logger.error("Không trích xuất được FB_PUBLIC_LOAD_DATA_. Link có thể yêu cầu đăng nhập.")
                raise Exception("Cannot parse form data.")

            items = data[1][1]
            
            for item in items:
                if len(item) < 5 or not item[4]: continue
                q_text = item[1].strip() if item[1] else ""
                if not q_text: continue
                
                cl_qt = "".join(e for e in q_text if e.isalnum()).lower()
                
                # Check type
                q_type = item[3]
                if q_type == 7: # Grid
                    row_ids = {}
                    for row_data in item[4]:
                        row_id = str(row_data[0]) if len(row_data) > 0 else ""
                        row_name = row_data[3][0] if len(row_data) > 3 and row_data[3] else ""
                        if row_name and row_id:
                            cl_rn = "".join(e for e in row_name if e.isalnum()).lower()
                            row_ids[cl_rn] = f"entry.{row_id}"
                            
                    schema.append({
                        "clean_title": cl_qt,
                        "type": "grid",
                        "row_ids": row_ids
                    })
                else: # Thường (Radio, Checkbox, Text, Dropdown)
                    entry_id = str(item[4][0][0]) if len(item[4][0]) > 0 else ""
                    options = []
                    if len(item[4][0]) > 1 and item[4][0][1]:
                         options = [str(opt[0]) for opt in item[4][0][1] if opt and len(opt)>0]
                         
                    schema.append({
                        "clean_title": cl_qt,
                        "type": "checkbox" if q_type == 4 else "normal",
                        "entry_id": f"entry.{entry_id}",
                        "options": options
                    })
            return schema
            
        except Exception as e:
            logger.error(f"Lỗi khi quét cấu trúc Form Mappings: {e}")
            raise e

    def fill(self, num_submissions=1, max_workers=1):
        logger.info(f"🚀 Bắt đầu điền API tự động: {self.url} | Số lượng: {num_submissions}")
        
        # Endpoint post data
        post_url = self.url.replace("/viewform", "/formResponse")
        
        success_count = 0
        error_count = 0
        
        submissions_per_worker = [num_submissions // max_workers + (1 if x < num_submissions % max_workers else 0) for x in range(max_workers)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, count in enumerate(submissions_per_worker):
                if count > 0:
                    futures.append(executor.submit(self._fill_worker_task, i + 1, count, post_url))
                    
            for future in concurrent.futures.as_completed(futures):
                try: 
                    sc, ec = future.result()
                    success_count += sc
                    error_count += ec
                except Exception as e: 
                    logger.error(f"Worker thread error: {e}")
                    
        logger.info(f"--- HOÀN TẤT --- Thành công: {success_count} | Lỗi: {error_count}")

    def _fill_worker_task(self, worker_id, num_submissions, post_url):
        sc = 0
        ec = 0
        try:
            for submission in range(1, num_submissions + 1):
                logger.info(f"[Worker {worker_id}] Đang push data {submission}/{num_submissions}...")
                
                payload = self._generate_payload()
                headers = {
                    "Referer": self.url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                try:
                    res = requests.post(post_url, data=payload, headers=headers, timeout=10)
                    if res.status_code == 200:
                        sc += 1
                        logger.info(f"[Worker {worker_id}] ✅ Nộp thành công ({submission}/{num_submissions})")
                    else:
                        ec += 1
                        logger.error(f"[Worker {worker_id}] ❌ Thất bại - HTTP {res.status_code}")
                except Exception as e:
                    ec += 1
                    logger.error(f"[Worker {worker_id}] ❌ Request Error: {e}")
                
                # Delay nhỏ mô phỏng người thực để an toàn (1 - 2 giây)
                if submission < num_submissions:
                     time.sleep(random.uniform(1.0, 1.5))
                     
        except Exception as e:
            logger.error(f"[Worker {worker_id}] Lỗi nghiêm trọng: {e}")
            
        return sc, ec

    def _generate_payload(self):
        """
        Sinh ra 1 mảng dictionary payload { 'entry.12345': 'Đáp án' } dựa vào tỷ lệ JSON random
        """
        payload = {
            "pageHistory": "0" # Mặc định google form cần param này
        }
        
        for q_schema in self.form_schema:
            cl_qt = q_schema["clean_title"]
            
            # Tìm config ứng với question này
            matched_key = None
            answer_data = None
            
            for clean_k, (orig_k, data) in self.cleaned_answers.items():
                if clean_k in cl_qt or cl_qt == clean_k or cl_qt.startswith(clean_k):
                    matched_key = orig_k
                    answer_data = data
                    break
                    
            if not matched_key:
                continue
                
            q_type = q_schema["type"]
            options = q_schema.get("options", [])
            
            if q_type == "grid":
                # answer_data format: {"Hàng 1": {"Cột A": 50, "Cột B": 50}}
                if isinstance(answer_data, dict):
                    row_ids = q_schema.get("row_ids", {})
                    for row_key, row_weights in answer_data.items():
                        cl_rk = "".join(e for e in row_key if e.isalnum()).lower()
                        # Tìm id của row
                        target_entry = None
                        for r_name, r_id in row_ids.items():
                            cl_r_name = "".join(e for e in r_name if e.isalnum()).lower()
                            if cl_rk in cl_r_name or cl_r_name in cl_rk:
                                target_entry = r_id
                                break
                        if target_entry:
                            target_col = random.choices(list(row_weights.keys()), weights=list(row_weights.values()), k=1)[0]
                            payload[target_entry] = target_col
                            
            elif q_type == "checkbox":
                 # answer_data: có thể là dict tỷ lệ hoặc array
                 target_vals = []
                 if self.random_mode and options:
                     target_vals = random.sample(options, random.randint(1, len(options)))
                 elif isinstance(answer_data, dict) and answer_data:
                     # Checkbox nhiều tùy chọn, tính xác suất TỪNG option
                     target_vals = [choice for choice, prob in answer_data.items() if random.random() < (prob / 100.0 if float(prob) > 1 else float(prob))]
                     if not target_vals:
                         target_vals.append(random.choices(list(answer_data.keys()), weights=list(answer_data.values()), k=1)[0])
                 else:
                     target_vals = answer_data if isinstance(answer_data, list) else [answer_data]
                 
                 # Request post mảng -> requests post cần truyền cùng key nhiều lần, hoặc list
                 # payload={'entry.123': ['A', 'B']} sẽ tự map thành `entry.123=A&entry.123=B`
                 payload[q_schema["entry_id"]] = target_vals
                 
            else: # normal (radio, dropdown, text)
                 target_val = ""
                 if self.random_mode:
                     if options: target_val = random.choice(options)
                     else: target_val = "Random Text " + str(random.randint(100,999))
                 else:
                     if isinstance(answer_data, dict) and answer_data:
                         choices, weights = list(answer_data.keys()), list(answer_data.values())
                         target_val = random.choices(choices, weights=weights, k=1)[0]
                     else:
                         target_val = answer_data[0] if isinstance(answer_data, list) and answer_data else answer_data
                         
                 payload[q_schema["entry_id"]] = str(target_val)
                 
        return payload
