import os
import re
from datetime import datetime
import pytz
import csv
import smtplib
from email.message import EmailMessage
from typing import List
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import urllib.request
import boto3

load_dotenv()


def lambda_handler(event, context):
    class Daily:
        all = []
        dict_pdf_filename_download_url = {}
        mail_list = []

        client = boto3.resource('dynamodb')
        table = client.Table('yours-daily-mail-list')
        mail_list = [item['email'] for item in table.scan()['Items']]

        def __init__(self, data_url: str, limit: int, newspaper_title: str) -> None:
            Daily.all = []
            self.DATA_URL = data_url
            self.LIMIT = limit
            self.NEWSPAPER_TITLE = newspaper_title

            Daily.all.append(self)

        def get_links(self, soup, limit) -> List:
            links = []
            for link in soup.find_all('a', attrs={'href': re.compile("^https://vk")}, limit=limit):
                redirect_url = link.get('href')
                links.append(redirect_url)
                self.get_pdf_link(redirect_url)
            return links

        def get_pdf_link(self, redirect_url) -> None:
            sub_soup = BeautifulSoup(requests.get(redirect_url).content, 'lxml')
            pdf_title = sub_soup.find('title').get_text()
            if pdf_title != "त्रुटि | वीके":
                download_pdf_url = sub_soup.find('iframe', attrs={'src': re.compile("^https://")}).get('src')
                print(pdf_title, download_pdf_url)

                self.dict_pdf_filename_download_url[pdf_title] = download_pdf_url
            else:
                print('CopyRight Issues')

        def send_mail(self, pdf_filename, pdf_download_url) -> Exception:
            print('sending email')
            IST = pytz.timezone('Asia/Kolkata')
            today_date = (datetime.now(IST).strftime('%d-%m-%Y'))
            email_subject = 'Yours Daily ' + self.NEWSPAPER_TITLE + ' : ' + today_date
            email_from = 'Yours Daily'
            msg = EmailMessage()
            msg['Subject'] = email_subject
            msg['From'] = email_from
            msg['Bcc'] = Daily.mail_list

            file = urllib.request.urlopen(pdf_download_url)
            file_size = file.length / (1024 * 1024)
            print(file_size, 'mb')

            if file_size > 25:
                msg.set_content(f"""File size exceeds limit\nBut here is your direct download link {pdf_download_url}\nHave a good day ahead!""")
            else:
                msg.set_content("""Here is your today's newspaper\nHave a good day ahead!""")
                msg.add_attachment(file.read(), maintype='application', subtype='octet-stream',
                                   filename=pdf_filename)
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(os.getenv('EMAIL'), os.getenv('EMAIL_PASSWORD'))
                    server.send_message(msg)
            except smtplib.SMTPException as stmp_e:
                return stmp_e
            except Exception as e:
                return e

        def make_dict_from_scrapper(self) -> None:
            req = requests.get(self.DATA_URL)
            print(req)
            soup_data = BeautifulSoup(req.content, 'lxml')
            self.get_links(soup_data, self.LIMIT)

        def kickstart(self) -> None:
            self.make_dict_from_scrapper()
            for pdf_filename, pdf_download_url in self.dict_pdf_filename_download_url.items():
                self.send_mail(pdf_filename, pdf_download_url)

        def __repr__(self):
            return f"Daily( {self.NEWSPAPER_TITLE}, {self.DATA_URL}, {self.LIMIT}, {Daily.mail_list})"

    def scheduler() -> None:
        with open('the-hindu.csv', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data_url = row['url']
                newspaper_title = row['title']
                limit = 1
                obj = Daily(data_url, limit, newspaper_title)
                print(obj.all)
                obj.kickstart()

    print('Automation Started')
    try:
        scheduler()
        print('Automation Completed')
    except Exception as e:
        print(type(e))
        return e
