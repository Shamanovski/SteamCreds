import json
import traceback
import time
import rsa
import string
import random
from urllib.parse import parse_qs, urlparse
from requests.exceptions import ProxyError

from steampy.client import SteamClient
from steampy.confirmation import ConfirmationExecutor
from steampy.guard import generate_one_time_code, load_steam_guard
from steampy.utils import fetch_email_token, steam_id_to_account_id

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome
import base64


def change_email(login, password, email, email_password, mafile, imap_host, confirmation_executor):
    driver = webdriver.Chrome()
    driver.get("https://help.steampowered.com/ru/wizard/HelpChangeEmail?redir=store/account/")
    driver.find_element_by_name("username").send_keys(login)
    driver.find_element_by_name("password").send_keys(password)
    driver.find_element_by_xpath("//button[@type='submit']").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "login_twofactorauth_buttonsets")))
    code = generate_one_time_code(mafile["shared_secret"], int(time.time()))
    WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, "twofactorcode_entry")))
    driver.find_element_by_id("twofactorcode_entry").send_keys(code)
    driver.find_element_by_id("login_twofactorauth_buttonset_entercode").find_elements_by_css_selector("div[data-modalstate='submit']")[0].click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[2].click()
    confirmation_executor.confirm_account_recovery()
    
    element = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[3].click()

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "verify_password"))).send_keys(password)
    driver.find_element_by_css_selector("#verify_password_submit input").click()

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_reset"))).send_keys(email)
    driver.find_element_by_css_selector("#change_email_area input").click()
    code = fetch_email_token(email, email_password, imap_host, "email")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_change_code"))).send_keys(code)
    driver.find_element_by_css_selector("#confirm_email_form > div.account_recovery_submit > input").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "main_content")))


def change_password(client, confirmation_executor):
    resp = client.session.get("https://help.steampowered.com/ru/wizard/HelpChangePassword?redir=store/account/")
    s = parse_qs(urlparse(resp.url).query)["s"][0]
    sessionid = client.session.cookies.get("sessionid", domain="help.steampowered.com")
    data = {
        "sessionid": sessionid,
        "wizard_ajax": 1,
        "s": s,
        "method": 8
    }
    resp = client.session.post("https://help.steampowered.com/ru/wizard/AjaxSendAccountRecoveryCode", data=data)

    confirmation_executor.confirm_account_recovery()
    data = {
        "sessionid": sessionid,
        "wizard_ajax": 1,
        "s": s,
        "account": steam_id_to_account_id(client.steamid),
        "reset": 1,
        "issueid": 406,
        "lost": 2
    }
    resp = client.session.post("https://help.steampowered.com/ru/wizard/AjaxAccountRecoveryGetNextStep", data=data).json()
    chars = string.ascii_lowercase + string.digits
    password = "".join(random.sample(chars, k=len(chars))[:12])
    data = {
        "sessionid": sessionid,
        "wizard_ajax": 1,
        "username": client.login_name
    }
    resp = client.session.post("https://help.steampowered.com/ru/login/getrsakey/", data=data).json()
    timestamp = resp["timestamp"]
    rsa_key = rsa.key.PublicKey(int(resp["publickey_mod"], 16), int(resp["publickey_exp"], 16))
    password_encrypted = base64.b64encode(rsa.pkcs1.encrypt(password.encode("utf-8"), rsa_key))
    account_id = steam_id_to_account_id(client.steamid)
    data = {
        "sessionid": sessionid,
        "wizard_ajax": 1,
        "s": s,
        "account": account_id,
        "password": password_encrypted,
        "rsatimestamp": timestamp
    }
    resp = client.session.post("https://help.steampowered.com/ru/wizard/AjaxAccountRecoveryChangePassword/", data=data).json()
    print(password)


with open("accounts.txt", "r") as f:
    accounts = [account.rstrip() for account in f.readlines()]

# with open("proxy.txt", "r") as f:
#     proxies = [proxy.rstrip() for proxy in f.readlines()]

proxy = None
for account in accounts:
    login, password = account.split(":")  # email, email_password, imap_host
    mafile = load_steam_guard("maFiles/%s.maFile" % login)
    client = SteamClient()
    client.login(login, password, mafile)
    confirmation_executor = ConfirmationExecutor('', mafile['identity_secret'],
                                                    str(mafile['Session']['SteamID']),
                                                    client._session)
    # change_email(login, password, email, email_password, mafile, imap_host, confirmation_executor)
    # proxy = proxies.pop()
    # ip, port, user, password = proxy.split(":")
    # proxies = {
    # 'http': f'http://{user}:{password}@{ip}:{port}',
    # 'https': f'http://{user}:{password}@{ip}:{port}',
    # }
    change_password(client, confirmation_executor)
    # while True:
    #     try:
    #         break
    #     except (ConnectionError, ProxyError, TimeoutError) as err:
    #         proxy = proxies.pop()