import sys
import os
import requests
import json
import re
import logging

logger = logging.getLogger(__name__)

class WebFormParser:
    def __init__(self, url, headless=True):
        self.url = self._clean_url(url)
        self.headless = headless

    def _clean_url(self, url):
        # Đảm bảo dùng link viewform thay vì edit để parse chính xác
        if "/edit" in url:
            url = url.split("/edit")[0] + "/viewform"
        return url

    def parse(self):
        logger.info(f"Đang khởi động Web Parser (HTTP GET) cho URL: {self.url}")
        form_structure = {
            "form_url": self.url,
            "questions": []
        }
        
        try:
            resp = requests.get(self.url, timeout=10)
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
                logger.error("Không tìm thấy dữ liệu form. Có thể link form yêu cầu đăng nhập hoặc không tồn tại.")
                raise Exception("Cannot parse form data.")

            items = data[1][1] # Danh sách các câu hỏi
            
            for item in items:
                # Nếu không có thẻ cấu trúc nhập liệu (ví dụ ảnh, video, text mô tả) -> bỏ qua
                if len(item) < 5 or not item[4]:
                    continue
                    
                question_text = item[1].strip() if item[1] else ""
                if not question_text:
                    continue
                
                # Biến định vị trùng lặp
                if any(q['id'] == question_text for q in form_structure["questions"]):
                    continue
                    
                question_type_id = item[3]
                
                # XỬ LÝ THEO LOẠI CÂU HỎI
                # Grid / Matrix (Type = 7: Radio grid, Type = 11: Checkbox grid)
                if question_type_id in [7, 11]:
                    rows = []
                    row_ids = {} # { "Hàng 1": "123456" }
                    
                    for row_data in item[4]:
                        row_id = str(row_data[0]) if len(row_data) > 0 else ""
                        row_name = row_data[3][0] if len(row_data) > 3 and row_data[3] else f"Row {row_id}"
                        rows.append(row_name)
                        row_ids[row_name] = row_id
                        
                    columns = []
                    if len(item[4][0]) > 1 and item[4][0][1]:
                        columns = [opt[0] for opt in item[4][0][1]]
                        
                    if rows and columns:
                        form_structure["questions"].append({
                            "id": question_text,
                            "text": question_text,
                            "type": "grid",
                            "rows": rows,
                            "columns": columns,
                            "entry_ids": row_ids # Dùng để backend dễ trích xuất
                        })
                    continue
                
                q_type_str = "text"
                if question_type_id == 2: q_type_str = "radio"
                elif question_type_id == 3: q_type_str = "dropdown"
                elif question_type_id == 4: q_type_str = "checkbox"
                elif question_type_id == 5: q_type_str = "radio" # Scale
                elif question_type_id in [0, 1]: q_type_str = "text"
                else: q_type_str = "text" # Mặc định
                
                entry_id = str(item[4][0][0]) if len(item[4][0]) > 0 else ""
                options = []
                
                if len(item[4][0]) > 1 and item[4][0][1]:
                    for opt in item[4][0][1]:
                        if opt and hasattr(opt, '__getitem__') and len(opt) > 0:
                            options.append(str(opt[0]))
                
                q_data = {
                    "id": question_text,
                    "text": question_text,
                    "type": q_type_str,
                    "entry_id": f"entry.{entry_id}"
                }
                
                if options:
                    q_data["options"] = options
                elif q_type_str == "text":
                    q_data["default_text"] = "Văn bản mẫu"
                    
                form_structure["questions"].append(q_data)
                
            logger.info("Hoàn tất quét form (Sử dụng HTTP POST architecture)!")
            return form_structure
            
        except Exception as e:
            logger.error(f"Lỗi Parser: {e}")
            raise e

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://docs.google.com/forms/d/e/1FAIpQLScP_Z-t4xW6hDclJ1tPcd2y09XQibN9Bv0HHTm-G3H4B2FzLw/viewform"
    parser = WebFormParser(url)
    print(json.dumps(parser.parse(), indent=2, ensure_ascii=False))
