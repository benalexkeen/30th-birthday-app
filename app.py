import collections
import datetime
import functools
import json
import os

from flask import Flask, request, render_template, redirect, url_for, session
import pymongo

from admin import login
from send_email import send_invite_to_attendee

__here__ = os.path.dirname(__file__)
config_path = os.path.join(__here__, 'config.json')

with open(config_path, 'r') as f:
    config = json.load(f)

uri = "mongodb://{}:{}@{}.documents.azure.com:10255/?ssl=true&replicaSet=globaldb"
uri = uri.format(
    config['cosmos_username'],
    config['cosmos_password'],
    config['cosmos_db_name']
)
cosmosdb_client = pymongo.MongoClient(uri)

app = Flask(__name__)
app.secret_key = config['flask_key']


def get_attendee_col():
    """
    Retrieves the attendee collection
    from CosmosDB
    """
    app_db = cosmosdb_client['app_db']
    attendee_col = app_db['attendees']
    return attendee_col


def get_attendee_data(attendee_id):
    attendee_col = get_attendee_col()
    return attendee_col.find_one(attendee_id)


def delete_attendee(attendee_id):
    attendee_col = get_attendee_col()
    return attendee_col.delete_one({'_id': int(attendee_id)})


def get_group_data(group_id):
    attendee_col = get_attendee_col()
    group_data = [x for x in attendee_col.find({'group_id': group_id})]
    return group_data


def get_data_from_attendee_id(attendee_id):
    user_data = get_attendee_data(attendee_id)
    group_data = get_group_data(user_data['group_id'])
    return user_data, group_data


def create_attendee(details):
    expected_keys = (
        'email_address',
        'first_name',
        'last_name',
        'group_id'
    )
    for key in expected_keys:
        assert key in details, 'Missing key: {}'.format(key)
    attendee_col = get_attendee_col()
    max_id = attendee_col.find().sort([('_id', -1)]).limit(1)
    max_id = max_id.next().get('_id')
    if details['group_id'] is None:
        max_group_id = attendee_col.find().sort([('group_id', -1)]).limit(1)
        max_group_id = max_group_id.next().get('group_id')
        group_id = max_group_id + 1
    else:
        group_id = int(details['group_id'])
    data = {
        '_id': max_id + 1,
        'first_name': details['first_name'],
        'last_name': details['last_name'],
        'email_address': details['email_address'],
        'group_id': group_id,
        'rsvp': 0,
        'dietary_reqs': '',
        'invite_sent': '',
        'invited_by': 1
    }
    attendee_col.insert_one(data)


def get_attendee_id(email):
    attendee_col = get_attendee_col()
    attendee_data = attendee_col.find_one({'email_address': email})
    if attendee_data is None:
        if 'gmail' in email:
            email = email.replace('gmail', 'googlemail')
        if 'googlemail' in email:
            email = email.replace('googlemail', 'gmail')
        attendee_data = attendee_col.find_one({'email_address': email})
    if attendee_data is not None:
        return attendee_data['_id']
    else:
        return None


def update_rsvp(form_data):
    coll = get_attendee_col()
    for key in form_data.keys():
        if key.startswith('attendance'):
            attendee_id = int(key.replace('attendance-', ''))
            attendance = int(form_data[key])
            coll.update_one(
                {'_id': attendee_id},
                {'$set': {'rsvp': attendance}}
            )
        if key.startswith('dietary-reqs'):
            attendee_id = int(key.replace('dietary-reqs-', ''))
            dietary_reqs = str(form_data[key])
            coll.update_one(
                {'_id': attendee_id},
                {'$set': {'dietary_reqs': dietary_reqs}}
            )


def update_user(form_data):
    coll = get_attendee_col()
    for key in form_data.keys():
        if key.startswith('email'):
            attendee_id = int(key.replace('email-', ''))
            email = form_data[key].strip(' ')
            if not email:
                email = None
            coll.update_one(
                {'_id': attendee_id},
                {'$set': {'email_address': email}}
            )
        if key.startswith('attendance'):
            attendee_id = int(key.replace('attendance-', ''))
            attendance = int(form_data[key])
            coll.update_one(
                {'_id': attendee_id},
                {'$set': {'rsvp': attendance}}
            )


def update_db_with_sent_email(attendee_id):
    coll = get_attendee_col()
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    coll.update_one(
        {'_id': attendee_id},
        {'$set': {'invite_sent': date}}
    )


def get_all_attendee_data():
    attendee_col = get_attendee_col()
    attendee_data = attendee_col.find()
    attendee_data = [_ for _ in attendee_data]
    return attendee_data


@app.route('/admin', methods=['GET', 'POST'])
def login_page():
    if session.get('logged_in'):
        redirect(url_for('admin_page'))
    error = None
    if request.method == 'POST':
        username = request.form['admin_user']
        password = request.form['admin_password']
        if not login(username, password):
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('admin_page'))
    return render_template('login.html', error=error)


@app.route('/logout', methods=['GET'])
def logout():
    session['logged_in'] = False
    return render_template('login.html')


def validate_request(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('logged_in'):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login_page'))
    return wrapper


def render_admin_page(message=None):
    attendee_data = get_all_attendee_data()
    attendees_by_group_id = collections.defaultdict(list)
    for d in attendee_data:
        attendees_by_group_id[d['group_id']].append(d)
    group_ids = set([x.get('group_id') for x in attendee_data])
    attendees = list(attendees_by_group_id.values())
    data = {
        'invited': len(attendee_data),
        'no_reply': len([x for x in attendee_data if x['rsvp'] == 0]),
        'attending': len([x for x in attendee_data if x['rsvp'] == 1]),
        'not_attending': len([x for x in attendee_data if x['rsvp'] == 2]),
        'attendees': attendees,
        'message': '',
        'group_ids': group_ids,
    }
    if message is not None:
        data['success'] = message['success']
        data['message'] = message['message']
    return render_template('admin.html', data=data)


@app.route('/admin_page', methods=['GET', 'POST'])
@validate_request
def admin_page():
    """
    message is a dict of {'success': bool, 'message': msg}
    """
    if request.method == 'POST':
        update_user(request.form)
        message = {'success': True, 'message': 'Update successful'}
    else:
        message = None
    return render_admin_page(message)


@app.route('/send_email/<attendee_id>', methods=['GET'])
@validate_request
def send_invite(attendee_id):
    attendee_id = int(attendee_id)
    attendee_data = get_attendee_data(attendee_id)
    if not attendee_data:
        msg = 'No user found for ID {}'.format(attendee_id)
        return admin_page(
            message={'success': False, 'message': msg}
        )
    if not attendee_data['email_address']:
        msg = 'No email found for {} {}'.format(
            attendee_data['first_name'],
            attendee_data['last_name'],)
        return admin_page(
            message={'success': False, 'message': msg}
        )
    send_invite_to_attendee(attendee_data)
    update_db_with_sent_email(attendee_id)
    msg = 'Email sent to {} {} at {}'.format(
        attendee_data['first_name'],
        attendee_data['last_name'],
        attendee_data['email_address'],
    )
    return render_admin_page(
        message={'success': True, 'message': msg}
    )


@app.route('/new_attendee', methods=['GET', 'POST'])
@validate_request
def new_attendee():
    email_address = request.form.get('email_address').strip(' ')
    if not email_address:
        email_address = None
    group_id = request.form.get('group_id')
    if not group_id or group_id == 'new':
        group_id = None
    else:
        group_id = int(group_id)
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name', '')
    details = {
        'first_name': first_name,
        'last_name': last_name,
        'group_id': group_id,
        'email_address': email_address
    }
    create_attendee(details)
    msg = "{} {} successfully added".format(first_name, last_name)
    return render_admin_page(
        message={'success': True, 'message': msg}
    )


@app.route('/delete/<attendee_id>', methods=['GET', 'POST'])
@validate_request
def delete(attendee_id):
    delete_attendee(attendee_id)
    msg = "Attendee successfully deleted"
    return render_admin_page(
        message={'success': True, 'message': msg}
    )


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        data = {
            'email_not_found': False,
            'email_attempted': ''
        }
        return render_template('index.html', data=data)
    else:
        email = str(request.form.get('email'))
        attendee_id = get_attendee_id(email)
        if attendee_id:
            session['attendee_id'] = attendee_id
            return redirect(url_for('rsvp'))
        else:
            data = {
                'email_not_found': True,
                'email_attempted': email
            }
            return render_template('index.html', data=data)


@app.route('/rsvp', methods=['GET', 'POST'])
def rsvp():
    attendee_id = session.get('attendee_id')
    if attendee_id is None:
        return redirect(url_for('home'))
    if request.method == 'POST':
        updated = True
        form_data = request.form
        update_rsvp(form_data)
    else:
        updated = False
    user_data, group_data = get_data_from_attendee_id(attendee_id)
    data = {
        'updated': updated,
        'user_data': user_data,
        'group_data': group_data,
        'google_maps_key': config['google_maps_key']
    }
    return render_template('rsvp.html', data=data)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
