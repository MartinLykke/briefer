# Kør dette script én gang lokalt for at få dit Google refresh token.
# Kræver: pip install google-auth-oauthlib

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\n--- Kopiér disse værdier til GitHub Secrets ---")
print(f"GOOGLE_REFRESH_TOKEN: {creds.refresh_token}")
print(f"GOOGLE_CLIENT_ID:     {creds.client_id}")
print(f"GOOGLE_CLIENT_SECRET: {creds.client_secret}")
