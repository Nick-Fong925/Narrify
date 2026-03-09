from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
]

flow = InstalledAppFlow.from_client_secrets_file(
    'backend/config/youtube_credentials.json',
    SCOPES
)
creds = flow.run_local_server(port=0)

with open('backend/config/youtube_token.json', 'wb') as f:
    pickle.dump(creds, f)

print('Token saved with scopes:', creds.scopes)
