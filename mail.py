#!/usr/bin/python

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
import os
import config

def mail(recv, subject, text):
    msg = MIMEMultipart()
    msg['From'] = config.email_smtp_user
    msg['To'] = recv
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    mail_server = smtplib.SMTP(config.email_smtp_address, config.email_smtp_port)
    mail_server.ehlo()
    mail_server.starttls()
    mail_server.ehlo()
    mail_server.login(config.email_smtp_user, config.email_smtp_password)
    mail_server.sendmail(config.email_smtp_user, recv, msg.as_string())
    mail_server.close()
