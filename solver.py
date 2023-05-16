from tensorflow.keras.models import load_model
import cv2
import numpy as np
import time
import os
import requests

from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MODEL_FILE = 'trained_model.h5'
IMAGE_SIZE = 100
DEMO_URL = 'https://accounts.hcaptcha.com/demo?sitekey=f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34'
CATEGORY_DIR = 'output'


class hCaptchaSolver:
    def __init__(self):
        self.model = load_model(MODEL_FILE)
        self.categories = os.listdir(CATEGORY_DIR)

    def create_driver(self):
        options = ChromeOptions()
        options.add_argument('--window-size=1000,1000')
        self.driver = Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def load_url(self, url=DEMO_URL):
        self.driver.get(url)
        time.sleep(5)

    def trigger_captcha(self):
        iframe = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*=".hcaptcha.com"][src*="frame=checkbox"]')))
        iframe.click()
        time.sleep(3)

    def locate_captcha_frame(self):
        iframe = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*=".hcaptcha.com"][src*="frame=challenge"]')))
        self.driver.switch_to.frame(iframe)

    def format_question(self, question):
        return question.replace('Please click each image containing an ', '').replace('Please click each image containing a ', '').replace('Please click each image containing ', '').replace(' ', '_').lower()

    def get_question(self):
        #input("Find the question and press enter to continue")
        parent_h2 = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'prompt-text')))
        question = parent_h2.text
        print("Question:", question)
        self.question = self.format_question(question)
        print("Formatted question:", self.question)
        if self.question not in self.categories:
            print("Category not found")
            return
        print("Category found")

    def extract_images(self):
        self.image_payload = []
        taskgrid = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'task-grid')))
        image_divs = taskgrid.find_elements(By.CLASS_NAME, 'task-image')
        for image_div in image_divs:
            # Get label property
            img_label = image_div.get_attribute('label')
            if img_label is None:
                img_label = image_div.get_attribute('aria-label')
            # Get image div
            img_div = image_div.find_element(By.CLASS_NAME, 'image')
            # Get image style
            img_style = img_div.get_attribute('style')
            img_uri = img_style.split('url("')[1].split('")')[0]
            self.image_payload.append({
                'se': image_div,
                'label': img_label,
                'uri': img_uri
            })
        [print(x) for x in self.image_payload]

    def download_image(self, uri, dont_rescale=False):
        r = requests.get(uri, stream=True).raw
        img = np.asarray(bytearray(r.read()), dtype="uint8")
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        if not dont_rescale:
            img = cv2.resize(img, (100, 100))
        return img

    def classify_image(self, image):
        image = cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE))
        image = np.array(image) / 255.0
        image = np.expand_dims(image, axis=0)

        prediction = self.model.predict(image)
        predicted_class = np.argmax(prediction)

        categories = os.listdir(CATEGORY_DIR)
        return categories[predicted_class]

    def process_images(self):
        for img_data in self.image_payload:
            img = self.download_image(img_data['uri'])
            img_res = self.classify_image(img)
            print(img_res, self.question)
            if img_res == self.question or self.question in img_res:
                img_data['se'].click()
                print("Clicked", img_data['label'])
                time.sleep(1)
            else:
                print("Not clicked", img_data['label'])
                time.sleep(1)

        time.sleep(4)
        self.driver.find_element(By.CLASS_NAME, 'button-submit').click()

    def main(self):
        self.create_driver()
        self.load_url()
        self.trigger_captcha()
        self.locate_captcha_frame()
        self.get_question()
        self.extract_images()
        self.process_images()


if __name__ == '__main__':
    solver = hCaptchaSolver()
    solver.main()

    input("Press enter to exit")
