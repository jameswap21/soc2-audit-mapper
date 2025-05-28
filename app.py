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

    def list_evidence(self, audit_id):
        all_evidence = []
        base_url = f"https://api.vanta.com/v1/audits/{audit_id}/evidence"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        next_url = base_url

        while next_url:
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            all_evidence.extend(data.get("results", {}).get("data", []))

            page_info = data.get("results", {}).get("pageInfo", {})
            if page_info.get("hasNextPage"):
                cursor = page_info.get("endCursor")
                next_url = f"{base_url}?pageCursor={cursor}"
            else:
                next_url = None

        return all_evidence

    def download_evidence_files(self, audit_id):
        evidence = self.list_evidence(audit_id)
        file_links = [(e.get('id'), e.get('fileDownloadLink')) for e in evidence if e.get('fileDownloadLink') is not None]
        return file_links

st.title("SOC 2 Audit Evidence Mapper")

st.header("\U0001f510 Connect to Vanta Auditor API")
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

                # Fetch and display all evidence
                evidence = client.list_evidence(audit_id)
                evidence_df = pd.json_normalize(evidence)
                evidence_df["HasDownloadLink"] = evidence_df["fileDownloadLink"].notnull() if "fileDownloadLink" in evidence_df.columns else False
                st.subheader("\U0001f4ce Audit Evidence")
                st.dataframe(evidence_df)

                # Export all evidence to CSV
                csv = evidence_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="\U0001f4c5 Download Evidence as CSV",
                    data=csv,
                    file_name=f"{selected_audit.replace(' ', '_')}_evidence.csv",
                    mime="text/csv"
                )

                # Fetch and display downloadable evidence file links
                st.subheader("\U0001f4c4 Downloadable Evidence Files")
                evidence_files = client.download_evidence_files(audit_id)
                if evidence_files:
                    file_links_df = pd.DataFrame(evidence_files, columns=["Evidence ID", "Download Link"])
                    st.dataframe(file_links_df)
                    download_csv = file_links_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="\U0001f4c1 Download File Links as CSV",
                        data=download_csv,
                        file_name=f"{selected_audit.replace(' ', '_')}_file_links.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No downloadable evidence files found.")

            except Exception as e:
                st.error(f"Error: {e}")

st.header("\U0001f4c1 Manual Uploads (ZIP + CSV)")
uploaded_zip = st.file_uploader("Upload Evidence ZIP File", type="zip")
uploaded_csv = st.file_uploader("Upload soc2-evidence CSV File", type="csv")
uploaded_controls = st.file_uploader("Upload SOC 2 Controls Mapping CSV File", type="csv")
uploaded_workbook = st.file_uploader("Upload Audit Workbook (.xlsx)", type="xlsx")

upload_trigger = st.button("Run Evidence Mapping")
