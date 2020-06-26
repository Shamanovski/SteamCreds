import json
import traceback
import logging
import os
import time

from steampy.client import SteamClient
from steampy.confirmation import ConfirmationExecutor
from steampy.guard import generate_one_time_code, load_steam_guard
from steampy.utils import fetch_email_token

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome


def change_email(login, password, email, email_password, mafile, imap_host):
    driver = webdriver.Chrome()
    driver.get("https://help.steampowered.com/ru/wizard/HelpChangeEmail?redir=store/account/")
    driver.find_element_by_name("username").send_keys(login)
    driver.find_element_by_name("password").send_keys(password)
    driver.find_element_by_xpath("//button[@type='submit']").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "login_twofactorauth_buttonsets")))
    mafile = load_steam_guard(mafile)
    code = generate_one_time_code(mafile["shared_secret"], int(time.time()))
    WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, "twofactorcode_entry")))
    driver.find_element_by_id("twofactorcode_entry").send_keys(code)
    driver.find_element_by_id("login_twofactorauth_buttonset_entercode").find_elements_by_css_selector("div[data-modalstate='submit']")[0].click()
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[2].click()

    mobile_client = SteamClient()
    mobile_client.mobile_login(login, password, mafile)
    confirmation_executor = ConfirmationExecutor('', mafile['identity_secret'],
                                                    str(mafile['Session']['SteamID']),
                                                    mobile_client._session)
    confirmation_executor.confirm_account_recovery()
    
    element = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[3].click()

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "verify_password"))).send_keys(password)
    driver.find_element_by_css_selector("#verify_password_submit input").click()

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_reset"))).send_keys(email)
    driver.find_element_by_css_selector("#change_email_area input").click()
    code = fetch_email_token(email, email_password, imap_host, "guard")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_change_code"))).send_keys(code)
    driver.find_element_by_css_selector("#confirm_email_form > div.account_recovery_submit > input").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "main_content")))
    driver.get("https://store.steampowered.com/phone/manage")
    driver.find_elements_by_class_name("phone_button_remove")[2].find_element_by_tag_name("span").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[2].click()
    time.sleep(3)
    confirmation_executor.confirm_account_recovery()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[3].click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "account_recovery_box")))
    driver.find_element_by_name("password").send_keys(password)
    driver.find_element_by_id("verify_password_submit").find_element_by_tag_name("input").click()
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//form[@id='reset_phonenumber_form']")))
    element.find_element_by_tag_name("input").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "main_phone_box")))

with open("accounts.txt", "r") as f:
    accounts = [account.rstrip() for account in f.readlines()]
for account in accounts:
    login, password, email, email_password, imap_host = account.split(":")
    change_email(login, password, email, email_password, "maFiles/%s.maFile" % login, imap_host)