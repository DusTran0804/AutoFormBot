import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.core.os_manager import ChromeType

def setup_logger():
    logger = logging.getLogger('AutoFormBot')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

logger = setup_logger()

def get_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    import os
    try:
        brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        
        if os.path.exists(brave_path):
            logger.info("Đã tìm thấy Brave! Đang để Selenium tự xử lý driver...")
            options.binary_location = brave_path
            
        # Gọi trực tiếp Chrome, KHÔNG DÙNG Service() hay ChromeDriverManager() nữa
        # Selenium Manager sẽ tự động làm nhiệm vụ tải driver ngầm.
        driver = webdriver.Chrome(options=options)
        return driver
        
    except Exception as e:
        logger.warning(f"Không thể khởi chạy Brave, thử chuyển sang Safari... Lỗi: {e}")
        try:
            # Phương án dự phòng: Gọi Safari (Trình duyệt mặc định có sẵn trên mọi máy Mac)
            driver = webdriver.Safari()
            logger.info("Đã khởi tạo thành công bằng Safari!")
            return driver
        except Exception as e2:
            logger.error(f"Cả Brave và Safari đều lỗi: {e2}")
            raise
    
    import os
    try:
        brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        if os.path.exists(brave_path) and not os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            logger.info("Found Brave Browser! Using Brave engine to allow multiple parallel windows.")
            options.binary_location = brave_path
            
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        logger.warning(f"Chrome/Brave init failed, trying Safari fallback... Error: {e}")
        try:
            driver = webdriver.Safari()
            if headless:
                logger.warning("Note: Safari does not fully support classic headless mode arguments via Selenium.")
            return driver
        except Exception as e2:
            logger.error(f"Both Chrome and Safari init failed: {e2}")
            raise

def retry_click(element, retries=3, delay=1):
    for i in range(retries):
        try:
            # Add scroll into view for Safari compatibility
            try:
                element.parent.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(0.5)
            except:
                pass
                
            try:
                element.click()
            except Exception as click_err:
                # If Safari overlay blocks the click, force use javascript click 
                element.parent.execute_script("arguments[0].click();", element)
                
            return True
        except Exception as e:
            if i == retries - 1:
                logger.error(f"Failed to click element after {retries} retries: {e}")
                raise
            time.sleep(delay)

def find_element_with_retry(driver, by, value, timeout=10, retries=3):
    for i in range(retries):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            if i == retries - 1:
                logger.error(f"Element '{value}' not found after {retries} retries.")
                raise
            time.sleep(1)
