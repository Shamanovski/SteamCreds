import re
import time

import pyqiwi

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome

from steampy.client import SteamClient
from steampy.confirmation import ConfirmationExecutor
from steampy.utils import fetch_email_token
from steampy.guard import generate_one_time_code, load_steam_guard

from sms_services import OnlineSimError, SmsActivateError

def add_money_to_account(self, api_key, login, money):
    wallet = pyqiwi.Wallet(token=api_key)
    wallet.send(pid="25549", recipient=login, amount=int(money))

def change_email(self, login, password, email, email_password, imap_host, mafile=None):
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
    code = fetch_email_token(email, email_password, imap_host, "code")
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

def activate_wallet_codes(self, wallet_code, login, password, mafile=None):
    steam_client = SteamClient()
    steam_client.login(login, password, mafile)
    data = {
        'wallet_code': wallet_code,
        'CreateFromAddress': '1',
        'Address': 'Russia',
        'City': 'Russia',
        'Country': 'RU',
        'State': '',
        'PostCode': '0001'
    }
    steam_client.session.post('https://store.steampowered.com/account/validatewalletcode/',
                                data={'wallet_code': wallet_code})
    steam_client.session.post('https://store.steampowered.com/account/createwalletandcheckfunds/',
                                data=data)
    steam_client.session.post('https://store.steampowered.com/account/confirmredeemwalletcode/',
                                data={'wallet_code': wallet_code})


def change_password(self, login, password, mafile=None):
    steam_client = SteamClient()
    steam_client.login(login, password, mafile)

def delete_numbers(self, login, password, mafile=None):
    steam_client = SteamClient()
    steam_client.login(login, password, mafile)

def change_numbers(self, login, password, sms_service,
                   country, mafile, used_codes,
                   email, email_password, imap_host, number, tzid):
    steam_client = SteamClient()
    steam_client.login(login, password, mafile)
    resp = steam_client.session.get("https://store.steampowered.com/phone/remove_confirm_mobileconf")
    sessionid = steam_client.session.cookies.get("sessionid", domain="store.steampowered.com")
    gid = re.search(r'g_gidPoll = "(\d+?)"', resp.text).group()
    confirmation_executor = ConfirmationExecutor('', mafile['identity_secret'],
                                                     str(mafile['Session']['SteamID']),
                                                     steam_client._session)

    confirmation_executor.confirm_number_change()
    resp = steam_client.session.get("https://store.steampowered.com/phone/remove_confirm_mobileconf_done", params={"gid": gid})
    token = re.search(r"g_tokenID = (\d+?);", resp.text).group()

    tzid, number = sms_service.get_number(country)
    data = {
        "op": "get_phone_number",
        "input": number,
        "sessionID": sessionid,
        "confirmed": "1",
        "checkfortos": "1",
        "bisediting": "1",
        "token": token
    }
    resp = steam_client.session.post("https://store.steampowered.com/phone/add_ajaxop", data=data)

    data = {
        "op": "email_verification"
        "input"": ",
        "sessionID": sessionid,
        "confirmed": "1",
        "checkfortos": "1",
        "bisediting": "1",
        "token": token,
    }
    resp = steam_client.session.post("https://store.steampowered.com/phone/add_ajaxop", data=data)
    link = fetch_email_token(email, email_password, imap_host, "link")
    steam_client.session.get(link)

    sms_code, time_left = _get_sms_code(tzid, used_codes, sms_service)
    if time_left == 0 or sms_code is None:
        raise OnlineSimError("Time for using this number is up.")

    data = {
        "op": "get_sms_code",
        "input": sms_code,
        "sessionID": sessionid,
        "confirmed": 1,
        "checkfortos": 1,
        "bisediting": 1,
        "token": token
    }
    resp = steam_client.session.post("https://store.steampowered.com/phone/add_ajaxop", data=data)
    
    return used_codes
    
            
def _get_sms_code(tzid, used_codes, sms_service):
    attempts = 0
    while attempts < 20:
        try:
            sms_code, time_left = sms_service.get_sms_code(tzid)
            if sms_code and sms_code not in used_codes:
                used_codes.append(sms_code)
                return sms_code, time_left
            time.sleep(3)
            attempts += 1
        except (OnlineSimError, SmsActivateError):
            break

    return None, 0
