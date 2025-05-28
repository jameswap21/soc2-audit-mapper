import streamlit as st
import zipfile
import os
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
import tempfile
import requests

class VantaAuditorClient:
    def __init__(self, client_id, client_secret):
        self.token = self._authenticate(client_id, client_secret)

    def _authenticate(self, client_id, client_secret):
        url = "https://api.vanta.com/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "auditor-api.audit:read"
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["access_token"]

    def list_audits_rest(self, page_size=100):
        url = f"https://api.vanta.com/v1/audits?pageSize={page_size}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()["results"]["data"]

    def list_tests(self):
        url = "https://api.vanta.com/v1/tests?pageSize=100"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def list_evidence(self, audit_id):
        url = f"https://api.vanta.com/v1/audits/{audit_id}/evidence"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

st.title("SOC 2 Audit Evidence Mapper")

st.header("🔐 Connect to Vanta Auditor API")
with st.expander("Step 1: Authenticate"):
    client_id = "vci_be6144a382f53d05ef0ec1639dbc76380b0d4f52d1ea07d3"
    client_secret = "vcs_a3ea4c_e1c82b79bcd177f388eb2506a65d9fcd9ffe666d87f0ad40a9597cf7eede3053"

    if st.button("List Available Audits"):
        try:
            client = VantaAuditorClient(client_id, client_secret)
            audits = client.list_audits_rest()
            if audits:
                audit_df = pd.DataFrame(audits)
                st.session_state["audit_df"] = audit_df
                st.dataframe(audit_df[["id", "customerDisplayName", "framework", "auditStartDate", "auditEndDate"]])
            else:
                st.warning("No audits found in your Vanta account.")
        except Exception as e:
            st.error(f"Error fetching audits: {e}")

    if "audit_df" in st.session_state:
        audit_df = st.session_state["audit_df"]
        selected_audit = st.selectbox("Select an Audit", audit_df["customerDisplayName"] + " (" + audit_df["framework"] + ")")
        audit_id = audit_df[audit_df["customerDisplayName"] + " (" + audit_df["framework"] + ")" == selected_audit]["id"].values[0]
    else:
        audit_id = st.text_input("Audit ID (manual entry if not listed)")

    if st.button("Fetch Evidence from Vanta"):
        if not audit_id:
            st.error("Please provide an Audit ID.")
        else:
            try:
                client = VantaAuditorClient(client_id, client_secret)
                st.success("Successfully authenticated with Vanta API!")

                # Fetch and display evidence
                evidence = client.list_evidence(audit_id)
                st.subheader("📎 Audit Evidence")
                st.json(evidence)

            except Exception as e:
                st.error(f"Error: {e}")

st.header("📁 Manual Uploads (ZIP + CSV)")
uploaded_zip = st.file_uploader("Upload Evidence ZIP File", type="zip")
uploaded_csv = st.file_uploader("Upload soc2-evidence CSV File", type="csv")
uploaded_controls = st.file_uploader("Upload SOC 2 Controls Mapping CSV File", type="csv")
uploaded_workbook = st.file_uploader("Upload Audit Workbook (.xlsx)", type="xlsx")

upload_trigger = st.button("Run Evidence Mapping")
