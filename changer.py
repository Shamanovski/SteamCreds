import json
import traceback
import logging
import os
import time

from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showwarning, askyesno, showinfo

from steampy.client import SteamClient
from steampy.confirmation import ConfirmationExecutor
from steampy.guard import generate_one_time_code, load_steam_guard
from steampy.utils import fetch_email_code

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Chrome


# if not os.path.exists('accounts.txt'):
#     with open('accounts.txt', 'w') as f:
#         pass

# if not os.path.exists("database/imap-hosts.json"):
#     with open("database/imap-hosts.json", "w") as f:
#         f.write("{}")


class MainWindow:

    def __init__(self, parent):
        self.parent = parent
        self.frame = Frame(self.parent)
        
        self.accounts = []
        self.email_boxes = []
        self.onlinesim_api_key = StringVar()
        self.captcha_api_key = StringVar()
        self.qiwi_api_key = StringVar()
        self.captcha_host = StringVar()
        self.onlinesim_host = StringVar()

        self.money_to_add = IntVar()
        self.change_numbers = IntVar()
        self.delete_numbers = IntVar()
        self.change_email = IntVar()

        self.captcha_settings_bttn = Button(self.frame, text='Настроить капча сервис',
                                            command=self.deploy_captcha_window, bg='#CEC8C8', relief=GROOVE)
        self.onlinesim_settings_bttn = Button(self.frame, text='Настроить сервис онлайн номеров',
                                              command=self.deploy_onlinenum_window, bg='#CEC8C8', relief=GROOVE)                                  
        self.start_button = Button(tools_frame, text='Начать', command=self.start_process,
                                   bg='#CEC8C8', relief=GROOVE, width=25)
        self.stop_button = Button(tools_frame, text='Остановить', command=self.stop_process,
                                  bg='#CEC8C8', relief=GROOVE, width=25)
        
        
        self.frame.grid(row=0, column=0, sticky=W)

        tools_frame = Frame(self.parent)
        self.tools_label = Label(tools_frame, text='Инструменты:')
        self.options_label = Label(tools_frame, text='Опции:')
        self.add_money_to_account_checkbutton = Checkbutton(tools_frame, text='Пополнять баланс на аккаунтах',
                                                            variable=self.add_money_to_account)
        self.change_numbers_checkbutton = Checkbutton(tools_frame, text='Менять номера на аккаунтах',
                                                      variable=self.change_numbers)
        self.delete_numbers_checkbutton = Checkbutton(tools_frame, text='Удалять номера на аккаунтах',
                                                      variable=self.delete_numbers)
        self.change_email_checkbutton = Checkbutton(tools_frame, text="Менять почту на аккаунтах",
                                                    variable=self.change_email)
        self.tools_frame.grid(row=1, column=0, sticky=W)
                                  
        log_frame = Frame(self.parent)
        self.log_label = Label(log_frame, text='Логи:')
        self.scrollbar = Scrollbar(log_frame, orient=VERTICAL)
        self.scrollbar_x = Scrollbar(log_frame, orient=HORIZONTAL)
        self.log_box = Listbox(log_frame, yscrollcommand=self.scrollbar.set, xscrollcommand=self.scrollbar_x.set)
        self.log_box.bind('<Enter>', self.freeze_log)
        self.log_box.bind('<Leave>', self.unfreeze_log)
        self.log_frozen = False
        self.scrollbar["command"] = self.log_box.yview
        self.scrollbar.bind('<Enter>', self.freeze_log)
        self.scrollbar.bind('<Leave>', self.unfreeze_log)
        self.scrollbar_x["command"] = self.log_box.xview
        self.scrollbar_x.bind('<Enter>', self.freeze_log)
        self.scrollbar_x.bind('<Leave>', self.unfreeze_log)
        log_frame.columnconfigure(0, weight=999)
        log_frame.columnconfigure(1, weight=1)
        log_frame.grid(row=2, column=0, sticky=NSEW)


        self.status_bar_label = Label(log_frame, anchor=W, text='Готов...', textvariable=self.status_bar)
        self.caption_label = Label(log_frame, text='by Shamanovsky')

        self.pack_widgets()
    
    def pack_widgets(self):
        self.load_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Загрузить...", menu=self.load_menu)
        self.load_menu.add_command(label="Аккаунты", command=self.accounts_open)
        self.load_menu.add_command(label="Почты", command=self.email_boxes_open)
        self.load_menu.add_command(label="SDA Manifest", command=self.manifest_open)

        self.menubar.add_cascade(label="Настроить прокси", command=self.deploy_proxy_widget)
        self.menubar.add_cascade(label="Загрузить Wallet Codes", command=self.deploy_proxy_widget)
        self.menubar.add_cascade(label="Открыть статистику", command=self.deploy_stats_window)

        self.onlinesim_settings_bttn.grid(row=0, column=0, padx=3, pady=5, sticky=W)
        self.captcha_settings_bttn.grid(row=1, column=0, padx=3, pady=5, sticky=W)

        self.tools_label.grid(row=1, column=0, pady=3, sticky=W)

        self.change_email_checkbutton.grid(row=2, column=0, pady=1)
        self.add_money_to_account_checkbutton.grid(row=3, column=0, pady=1, sticky=W)
        self.change_numbers_checkbutton.grid(row=4, column=1, pady=1)
        self.delete_numbers_checkbutton.grid(row=4, column=1, pady=1)

        self.options_label.grid(row=5, column=0, pady=3, sticky=W)
        self.start_button.grid(row=6, pady=10, column=0)
        self.stop_button.grid(row=6, pady=10, column=1)
        self.log_label.grid(row=0, column=0, pady=5, sticky=W)
        self.log_box.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)
        self.scrollbar_x.grid(row=2, column=0, sticky=EW)
        self.status_bar_label.grid(row=3, column=0, columnspan=2, sticky=W, pady=5)
        self.caption_label.grid(row=3, column=0, sticky=E)
    
    def add_money(self, login):
        wallet = pyqiwi.Wallet(token=self.client.qiwi_api_key.get())
        wallet.send(pid="25549", recipient=login, amount=int(self.client.money_to_add.get()))
    
    def check_input(self):
        pass
    
    def add_log(self, message):
        self.log_box.insert(END, message)
        if not self.log_frozen:
            self.log_box.yview(END)

    def freeze_log(self, *ignore):
        self.log_frozen = True

    def unfreeze_log(self, *ignore):
        self.log_frozen = False
    
    async def produce_proxies(self):
        pass

    def deploy_proxy_widget(self):
        pass

    def deploy_captcha_window(self):
        pass

    def accounts_open(self):
        pass

    def email_boxes_open(self):
        dir_ = (os.path.dirname(self.email_boxes_path)
                if self.email_boxes_path is not None else '.')
        email_boxes_path = askopenfilename(
                    title='Email адреса',
                    initialdir=dir_,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)

        self.email_boxes_path = self.load_file(email_boxes_path, self.email_boxes_data, r"[\d\w\-\.]+@[\d\w]+\.\w+:.+\n")

    def manifest_open(self):
        dir_ = (os.path.dirname(self.manifest_path)
                if self.manifest_path is not None else '.')
        manifest_path = askopenfilename(
                    title='SDA manifest',
                    initialdir=dir_,
                    filetypes=[('manifest', '*.json')],
                    defaultextension='.json', parent=self.parent)
        if manifest_path:
            return self.load_manifest(manifest_path)

    def load_manifest(self, manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                self.manifest_data = json.load(f)
            self.manifest_path = manifest_path
        except (EnvironmentError, TypeError, json.JSONDecodeError):
            return

        self.status_bar.set("Файл загружен: %s" % os.path.basename(manifest_path))
    
    def proxy_open(self, window):
        dir_ = (os.path.dirname(self.proxy_path)
                if self.proxy_path is not None else '.')
        proxy_path = askopenfilename(
            title='Proxy',
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=window)

        self.proxy_path = self.load_file(proxy_path, self.proxy_data)
        window.destroy()
    

    def app_quit(self, *ignore):
        self.save_input()
        with open('database/userdata.txt', 'w') as f:
            json.dump(self.userdata, f)

        steamreg.counters_db.sync()
        steamreg.counters_db.close()

        if self.remove_emails_from_file.get():
            with open(self.email_boxes_path, "w") as f:
                for email in self.email_boxes_data:
                    f.write(email + "\n")

        with open("accounts.txt", "w") as f:
            for account in self.accounts_unbinded:
                login_passwd = account.split(":")[:2]
                login_passwd = ":".join(login_passwd)
                if login_passwd not in self.accounts_binded:
                    f.write(account + "\n")

        self.parent.destroy()



def change_email(login, password, email, email_password, mafile, imap_host, driver):
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
    # driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[2].click()

    mobile_client = SteamClient()
    mobile_client.mobile_login(login, password, mafile)
    confirmation_executor = ConfirmationExecutor('', mafile['identity_secret'],
                                                    str(mafile['Session']['SteamID']),
                                                    mobile_client._session)
    # confirmation_executor.confirm_account_recovery_confirmation()
    
    # element = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    # driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[3].click()

    # WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "verify_password"))).send_keys(password)
    # driver.find_element_by_css_selector("#verify_password_submit input").click()

    # WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_reset"))).send_keys(email)
    # driver.find_element_by_css_selector("#change_email_area input").click()
    # code = fetch_email_code(email, email_password, imap_host)
    # WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "email_change_code"))).send_keys(code)
    # driver.find_element_by_css_selector("#confirm_email_form > div.account_recovery_submit > input").click()
    # WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "main_content")))
    driver.get("https://store.steampowered.com/phone/manage")
    driver.find_elements_by_class_name("phone_button_remove")[2].find_element_by_tag_name("span").click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[2].click()
    time.sleep(3)
    confirmation_executor.confirm_account_recovery_confirmation()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "help_page_title")))
    driver.find_element_by_id("wizard_contents").find_elements_by_tag_name("a")[3].click()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "account_recovery_box")))
    driver.find_element_by_name("password").send_keys(password)
    driver.find_element_by_id("verify_password_submit").find_element_by_tag_name("input").click()
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//form[@id='reset_phonenumber_form']")))
    element.find_element_by_tag_name("input").click()
    # driver.find_element_by_id("verify_password_submit").find_element_by_tag_name("input").click()
    # action = ActionChains(driver)
    # action.move_to_element(element).permorm()
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "main_phone_box")))

def launch():
    root = Tk()
    window = MainWindow(root)
    global steamreg
    steamreg = SteamRegger(window)
    root.iconbitmap('database/icon.ico')
    root.title('SteamCreds 1.0')
    root.protocol("WM_DELETE_WINDOW", window.app_quit)
    root.mainloop()

if __name__ == '__main__':
    logging.getLogger("requests").setLevel(logging.ERROR)
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler = logging.FileHandler('database/logs.txt', 'w', encoding='utf-8')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
