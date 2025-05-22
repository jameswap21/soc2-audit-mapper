
import requests
import time

class VantaAuditorClient:
    def __init__(self, client_id, client_secret):
        self.auth_url = "https://api.vanta.com/oauth/token"
        self.base_url = "https://api.vanta.com"
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.expires_at = 0

    def authenticate(self):
        if self.access_token and time.time() < self.expires_at - 60:
            return  # already valid

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "auditor-api.audit:read auditor-api.auditor:read"
        }

        resp = requests.post(self.auth_url, json=payload)
        if resp.status_code != 200:
            raise Exception(f"Authentication failed: {resp.status_code} {resp.text}")
        data = resp.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data["expires_in"]

    def get_headers(self):
        self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }

    def list_audits(self, org_slug):
        url = f"{self.base_url}/auditor/{org_slug}/audits"
        resp = requests.get(url, headers=self.get_headers())
        resp.raise_for_status()
        return resp.json()

    def list_tests(self, org_slug, audit_id):
        url = f"{self.base_url}/auditor/{org_slug}/audits/{audit_id}/tests"
        resp = requests.get(url, headers=self.get_headers())
        resp.raise_for_status()
        return resp.json()

    def list_evidence(self, org_slug, audit_id):
        url = f"{self.base_url}/auditor/{org_slug}/audits/{audit_id}/evidence"
        resp = requests.get(url, headers=self.get_headers())
        resp.raise_for_status()
        return resp.json()
