import json
import traceback
import logging
import os
import time
import threading

from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showwarning, askyesno, showinfo

from steampy.client import SteamClient
from steampy.confirmation import ConfirmationExecutor
from steampy.guard import generate_one_time_code, load_steam_guard
from steampy.utils import fetch_email_token

import pyqiwi
import cert_human

from enums import *
from sms_services import *
import process
from utils import extract_mafile, extract_re_value

cert_human.enable_urllib3_patch()


if not os.path.exists('accounts.txt'):
    with open('accounts.txt', 'w') as f:
        pass

if not os.path.exists("database/imap-hosts.json"):
    with open("database/imap-hosts.json", "w") as f:
        f.write("{}")


class MainWindow:

    def __init__(self, parent):
        self.parent = parent
        self.frame = Frame(self.parent)
        self.status_bar = StringVar()
        
        self.accounts = []
        self.email_boxes = []
        self.wallet_codes = []
        self.proxies = []
        self.mafiles = []
        self.accounts_path = StringVar()
        self.mafiles_path = StringVar()
        self.wallet_codes_path = StringVar()
        self.emails_path = StringVar()
        self.proxies_path = StringVar()
        self.onlinesim_api_key = StringVar()
        self.captcha_api_key = StringVar()
        self.qiwi_api_key = StringVar()
        self.captcha_host = StringVar()
        self.onlinesim_host = StringVar()

        self.sms_service = None
        self.country_code = StringVar()
        self.country_code.set('Россия')
        self.sms_service_type = IntVar()
        self.sms_service_type.set(int(SmsService.OnlineSim))

        self.money_to_add = IntVar()
        self.change_numbers = IntVar()
        self.delete_numbers = IntVar()
        self.change_email = IntVar()
        self.repeat = IntVar()

        self.find_hashtable = {}


        self.captcha_settings_bttn = Button(self.frame, text='Настроить капча сервис',
                                            command=self.deploy_captcha_window, bg='#CEC8C8', relief=GROOVE)
        self.onlinesim_settings_bttn = Button(self.frame, text='Настроить сервис онлайн номеров',
                                              command=self.deploy_onlinenum_window, bg='#CEC8C8', relief=GROOVE)                                  
        
        
        self.frame.grid(row=0, column=0, sticky=W)

        tools_frame = Frame(self.parent)
        self.tools_label = Label(tools_frame, text='Инструменты:')
        self.options_label = Label(tools_frame, text='Опции:')
        self.add_money_to_account_checkbutton = Checkbutton(tools_frame, text='Пополнять баланс на аккаунтах',
                                                            variable=process.add_money_to_account)
        self.change_numbers_checkbutton = Checkbutton(tools_frame, text='Менять номера на аккаунтах',
                                                      variable=process.change_numbers)
        self.delete_numbers_checkbutton = Checkbutton(tools_frame, text='Удалять номера на аккаунтах',
                                                      variable=process.delete_numbers)
        self.change_email_checkbutton = Checkbutton(tools_frame, text="Менять почту на аккаунтах",
                                                    variable=process.change_email)
        self.wallet_codes_checkbutton = Checkbutton(tools_frame, text="Применить Wallet Codes",
                                                    variable=process.activate_wallet_codes)
        self.start_button = Button(tools_frame, text='Начать', command=self.start_process,
                                   bg='#CEC8C8', relief=GROOVE, width=25)
        self.stop_button = Button(tools_frame, text='Остановить', command=self.stop_process,
                                  bg='#CEC8C8', relief=GROOVE, width=25)
        tools_frame.grid(row=1, column=0, sticky=W)
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
        self.load_menu.add_command(label="Мафайлы", command=self.mafiles_open)
        self.load_menu.add_command(label="Почты", command=self.email_boxes_open)
        self.load_menu.add_cascade(label="Wallet Codes", command=self.wallet_codes_open)
        self.load_menu.add_cascade(label="Прокси", command=self.proxy_open)

        self.onlinesim_settings_bttn.grid(row=0, column=0, padx=3, pady=5, sticky=W)
        self.captcha_settings_bttn.grid(row=1, column=0, padx=3, pady=5, sticky=W)

        self.tools_label.grid(row=1, column=0, pady=3, sticky=W)

        self.change_email_checkbutton.grid(row=2, column=0, pady=1)
        self.add_money_to_account_checkbutton.grid(row=3, column=0, pady=1, sticky=W)
        self.change_numbers_checkbutton.grid(row=4, column=1, pady=1)
        self.delete_numbers_checkbutton.grid(row=4, column=1, pady=1)
        self.wallet_codes_checkbutton.grid(row=5, column=0, pady=1)

        # self.options_label.grid(row=5, column=0, pady=3, sticky=W)
        self.start_button.grid(row=6, pady=10, column=0)
        self.stop_button.grid(row=6, pady=10, column=1)
        self.log_label.grid(row=0, column=0, pady=5, sticky=W)
        self.log_box.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)
        self.scrollbar_x.grid(row=2, column=0, sticky=EW)
        self.status_bar_label.grid(row=3, column=0, columnspan=2, sticky=W, pady=5)
        self.caption_label.grid(row=3, column=0, sticky=E)

    def start_process(self):
        onlinesim_api_key = self.onlinesim_api_key.get()
        sim_host = self.onlinesim_host.get()
        if self.sms_service_type.get() == SmsService.OnlineSim:
            self.sms_service = OnlineSimApi(onlinesim_api_key, sim_host)
        elif self.sms_service_type.get() == SmsService.SmsActivate:
            self.sms_service = SmsActivateApi(onlinesim_api_key, sim_host)
        
        self.check_and_run()

    def stop_process(self):
        pass
    
    def deploy_captcha_window(self):
        top = Toplevel(master=self.frame)
        top.title("Настройка капчи сервиса")
        top.iconbitmap('database/captcha.ico')

        Label(top, text='Сервис:').grid(row=0, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='RuCaptcha', variable=self.captcha_service_type, value=int(CaptchaService.RuCaptcha))\
            .grid(row=1, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='AntiCaptcha', variable=self.captcha_service_type, value=int(CaptchaService.AntiCaptcha))\
            .grid(row=1, column=1, pady=5, padx=5, sticky=W)

        Label(top, text='api key:').grid(row=2, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.captcha_api_key, width=33) \
            .grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Host:').grid(row=3, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.captcha_host, width=33) \
            .grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Button(top, command=top.destroy, text="Подтвердить").grid(column=0, columnspan=3, row=4, padx=5, pady=5)

    def check_captcha_key(self):
            balance = captcha_service.get_balance()
            self.captcha_balance_stat.set("Баланс CAPTCHA сервиса: %s" % balance)

    def deploy_onlinenum_window(self):
        def deploy_countries_list(event=True):
            self.sms_service.number_country.clear()
            self.set_countries()
            if event:
                self.country_code.set("Россия")

                if self.sms_service_type.get() == SmsService.OnlineSim:
                    self.onlinesim_host.set("onlinesim.ru")
                elif self.sms_service_type.get() == SmsService.SmsActivate:
                    self.onlinesim_host.set("sms-activate.ru")

            OptionMenu(top, self.country_code, *sorted(self.sms_service.number_country.keys())) \
                .grid(row=5, padx=5, pady=5, sticky=W)


        top = Toplevel(master=self.frame)
        top.title("Настройка сервиса онлайн номеров")
        top.iconbitmap('database/sim.ico')

        Label(top, text='Сервис:').grid(row=0, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='OnlineSim', variable=self.sms_service_type, value=int(SmsService.OnlineSim),
                    command=deploy_countries_list).grid(row=1, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='SMS Activate', variable=self.sms_service_type, value=int(SmsService.SmsActivate),
                    command=deploy_countries_list).grid(row=1, column=1, pady=5, padx=5, sticky=W)

        Label(top, text='api key:').grid(row=2, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_api_key, width=33)\
            .grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Host:').grid(row=3, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_host, width=33, )\
            .grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Страна номера:').grid(row=4, column=0, pady=3, sticky=W)
        deploy_countries_list(event=False)

        Button(top, command=top.destroy, text="Подтвердить").grid(column=0, columnspan=3, row=6, padx=5, pady=5)
            
    def check_and_run(self):
        if self.mafiles:
            self.mafiles = self.mafiles.reverse()

        if self.change_email.get():
            if not self.accounts.get():
                showwarning("Ошибка", "Не загружен текстовик с аккаунтами", parent=self.parent)
                return False
            self.iterate_emails()
            
        if self.add_money_to_account.get():
            if not self.money_to_add.get():
                showwarning("Ошибка", "Не указана сумма для пополнения баланса")
                return False

            if not self.qiwi_api_key.get():
                showwarning("Ошибка", "Не указан QIWI Api ключ")
                return False

            is_agree = askyesno("Пополнение баланса", "Вы уверены что хотите пополнять баланс на аккаунтах?",
                                icon='warning')
            if not is_agree:
                return False

        
        if self.change_numbers.get():
            if not self.onlinesim_api_key:
                showwarning("Ошибка", "Не указан api ключ для onlinesim.ru", parent=self.parent)
                return False

        
        if self.activate_wallet_codes.get():
            if not self.wallet_codes.get() or not self.account.get():
                 showwarning("Ошибка", "Не указаны коды либо логины", parent=self.parent)
                 return False

            threading.Thread(target=self.iterate_wallet_codes).start()
    
    def iterate_wallet_codes(self):
        p = self.find_hashtable["accounts"]
        p2 = self.find_hashtable["wallet_codes"]
        mafiles = self.mafiles
        accounts = self.accounts
        codes = self.wallet_codes
        for item in zip(accounts, mafiles, codes):
            account, mafile, code = item
            login = extract_re_value(p, account, "login") or extract_re_value(p2, account, "login")
            password = extract_re_value(p, account, "password") or extract_re_value(p2, account, "password")
            code = extract_re_value(p2, code, "wallet_code")
            with open(mafile, "r") as f:
                mafile = json.loads(f)
            process.activate_wallet_codes(code, login, password, mafile)
    
    def iterate_emails(self):
        p = self.find_hashtable["accounts"]
        p2 = self.find_hashtable["emails"]
        mafiles = self.mafiles
        accounts = self.accounts
        emails = self.email_boxes
        for item in zip(accounts, mafiles, emails):
            account, mafile, email = item
            login = extract_re_value(p, account, "login") or extract_re_value(p2, account, "login")
            password = extract_re_value(p, account, "password") or extract_re_value(p2, account, "password")
            email = extract_re_value(p2, account, "email") or extract_re_value(p2, email, "email")
            epassword = extract_re_value(p2, account, "epassword") or extract_re_value(p2, email, "epassword")
            imap_host = extract_re_value(p2, account, "imap") or extract_re_value(p2, email, "imap")
            process.change_email(login, password, email, epassword, imap_host, driver, mafile)
        
    def iterate_accounts_for_deposit(self):
        p = self.find_hashtable["accounts"]
        for account in self.accounts:
            login = extract_re_value(p, account, "login")
            process.add_money_to_account(self.qiwi_api_key, login, self.money_to_add.get())

    def iterate_accounts_for_number_deleting(self):
        p = self.find_hashtable["accounts"]
        for account, mafile in zip(self.accounts, self.mafiles):
            login = extract_re_value(p, account, "login")
            password = extract_re_value(p, account, "password")
            mafile = load_steam_guard(mafile)
            process.delete_numbers(login, password, mafile)      

    def iterate_accounts_for_number_changing(self):
        p = self.find_hashtable["accounts"]
        p2 = self.find_hashtable["emails"]
        used_codes = []
        country = self.country_code.get()
        repeat = False
        if self.repeat.get():
            repeat = True
        for account, mafile, email in zip(self.accounts, self.mafiles, self.email_boxes):
            if repeat:
                tzid, number = sms_service.get_number(country)
            login = extract_re_value(p, account, "login")
            password = extract_re_value(p, account, "password")
            mafile = load_steam_guard(mafile)
            email = extract_re_value(p2, email, "email")
            email_password = extract_re_value(p2, email, "epassword")
            imap_host = extract_re_value(p2, email, "imap")
            try:
                used_codes = process.change_numbers(login, password, self.sms_service,
                                                    country, mafile, used_codes,
                                                    email, email_password, imap_host,
                                                    number, tzid)
            except (OnlineSimError, SmsActivateError):
                tzid, number = sms_service.get_number(country)
                
                 


    def iterate_accounts_for_password_changing(self):
        pass

    def add_log(self, message):
        self.log_box.insert(END, message)
        if not self.log_frozen:
            self.log_box.yview(END)

    def freeze_log(self, *ignore):
        self.log_frozen = True

    def unfreeze_log(self, *ignore):
        self.log_frozen = False
    
    def deploy_onlinenum_window(self):
        def deploy_countries_list(event=True):
            self.sms_service.number_country.clear()
            if event:
                self.country_code.set("Россия")

                if self.sms_service_type.get() == SmsService.OnlineSim:
                    self.onlinesim_host.set("onlinesim.ru")
                elif self.sms_service_type.get() == SmsService.SmsActivate:
                    self.onlinesim_host.set("sms-activate.ru")


            OptionMenu(top, self.country_code, *sorted(self.sms_service.number_country.keys())) \
                .grid(row=5, padx=5, pady=5, sticky=W)

        top = Toplevel(master=self.frame)
        top.title("Настройка сервиса онлайн номеров")
        top.iconbitmap('database/sim.ico')

        Label(top, text='Сервис:').grid(row=0, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='OnlineSim', variable=self.sms_service_type, value=int(SmsService.OnlineSim),
                    command=deploy_countries_list).grid(row=1, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='SMS Activate', variable=self.sms_service_type, value=int(SmsService.SmsActivate),
                    command=deploy_countries_list).grid(row=1, column=1, pady=5, padx=5, sticky=W)

        Label(top, text='api key:').grid(row=2, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_api_key, width=33)\
            .grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Host:').grid(row=3, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_host, width=33, )\
            .grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Страна номера:').grid(row=4, column=0, pady=3, sticky=W)
        deploy_countries_list(event=False)

        Button(top, command=top.destroy, text="Подтвердить").grid(column=0, columnspan=3, row=6, padx=5, pady=5)
    
    def accounts_open(self):
        dir = (os.path.dirname(self.accounts_path)
               if self.accounts_path is not None else '.')
        self.accounts_path = askopenfilename(
                    title='логин:пасс аккаунтов',
                    initialdir=dir,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)
        self.find_hashtable["accounts"] = r"""
                                          (?P<account>.+?):(?P<password>.+?)
                                          (:(?P<email>[\d\w\-\.]+@[\d\w]+\.\w+):(?P<epassword>.+?))?(:(?P<imap>imap.+?))?\n
                                          """

        self.load_data(self.accounts_path, self.accounts, self.find_hashtable["accounts"])

    def mafiles_open(self):
        dir = (os.path.dirname(self.mafiles_path)
               if self.mafiles_path is not None else '.')
        self.mafiles_path = askopenfilename(
                    title='Директория где хранятся мафайлы',
                    initialdir=dir,
                    filetypes=[],
                    defaultextension='.txt', parent=self.parent)

        self.load_mafiles(self.mafiles_path)
        
    def proxy_open(self, window):
        dir_ = (os.path.dirname(self.proxy_path)
                if self.proxy_path is not None else '.')
                
        self.proxy_path = askopenfilename(
            title='Proxy',
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=window)

        self.load_data(self.proxy_path, self.proxies)

    def wallet_codes_open(self):
        dir_ = (os.path.dirname(self.wallet_codes_path)
                if self.wallet_codes_path is not None else '.')
        self.wallet_codes_path = askopenfilename(
                    title='Email адреса',
                    initialdir=dir_,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)
        self.find_hashtable["wallet_codes"] = r"((?P<account>.+?):(?P<password>.+?):)?(?P<wallet_code>\w{5}\-\w{5}\-\w{5})\n"
        self.load_data(self.wallet_codes_path, self.wallet_codes, self.find_hashtable["wallet_codes"])
    
    def email_boxes_open(self):
        dir_ = (os.path.dirname(self.email_boxes_path)
                if self.email_boxes_path is not None else '.')
        self.email_boxes_path = askopenfilename(
                    title='Email адреса',
                    initialdir=dir_,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)
        self.find_hashtable["email_boxes"] = r"(?P<email>[\d\w\-\.]+@[\d\w]+\.\w+):(?P<epassword>.+?)(:(?P<imap>imap.+?))?\n"
        self.load_data(self.email_boxes_path, self.email_boxes, self.find_hashtable["email_boxes"])
        
    def load_data(self, path, collection, regexr=None):
        if not path:
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for row, item in enumerate(f.readlines()):
                    if regexr and not re.match(regexr, item):
                        self.add_log("Недопустимое значение: {0} в строке {1}".format(item.strip(), row))
                        if not item.endswith("\n"):
                            self.add_log("Отсутствует новая строка (нажмите Enter в конце строки)")
                        continue
                    collection.append(item.strip())
        except (EnvironmentError, TypeError):
            return ''

        if collection:
            self.add_log("Файл загружен: %s" % os.path.basename(path))
        
    def load_mafiles(self, directory):
        for mafile in os.listdir(self.mafiles_path):
            self.mafiles.append(os.path.join(self.mafiles_path, mafile))
    
    def save_input(self):
        exceptions = ('status_bar', 'license', 'accounts_path')
        for field, value in self.__dict__.items():
            if list(filter(lambda exception: exception in field, exceptions)) or "status" in field:
                continue
            if issubclass(value.__class__, Variable) or 'path' in field or 'imap_hosts' in field:
                try:
                    value = value.get()
                except (AttributeError, TypeError):
                    pass
                self.userdata[field] = value

    def app_quit(self, *ignore):
        self.save_input()
        with open('database/userdata.txt', 'w') as f:
            json.dump(self.userdata, f)

        self.parent.destroy()


def launch():
    root = Tk()
    window = MainWindow(root)
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

launch()
