from __future__ import print_function

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete token.json
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None

    # token.json stores user access tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(
            'token.json',
            SCOPES
        )

    # Login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    return service


def create_event():
    service = get_calendar_service()

    event = {
        'summary': 'Dog Grooming Appointment',
        'location': 'Lahore',
        'description': 'Golden Retriever grooming session',

        'start': {
            'dateTime': '2026-05-20T15:00:00',
            'timeZone': 'Asia/Karachi',
        },

        'end': {
            'dateTime': '2026-05-20T16:00:00',
            'timeZone': 'Asia/Karachi',
        },

        'attendees': [
            {'email': 'customer@example.com'},
        ],

        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event
    ).execute()

    print('Event created:')
    print(created_event.get('htmlLink'))


if __name__ == '__main__':
    create_event()