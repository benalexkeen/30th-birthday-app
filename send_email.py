import json
import os
from string import Template

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

__here__ = os.path.dirname(__file__)
config_path = os.path.join(__here__, 'config.json')

with open(config_path, 'r') as f:
    config = json.load(f)

sendgrid_api_key = config['sendgrid_api_key']
from_email = config['from_email']


def send_invite_to_attendee(attendee_data):
    with open(os.path.join(__here__, 'templates', 'invite_email.html'), 'r') as f:
        msg = f.read()
    msg = Template(msg).safe_substitute(invitee_name=attendee_data['first_name'])
    message = Mail(
        from_email=from_email,
        to_emails=attendee_data['email_address'],
        subject="You're Invited to Ben's 30th Birthday",
        html_content=msg
    )
    sg = SendGridAPIClient(sendgrid_api_key)
    try:
        response = sg.send(message)
        success = True
        msg = f"Successfully sent invite to {email_address}"
        return success, msg
    except Exception as e:
        success = False
        msg = e
        return success, e
