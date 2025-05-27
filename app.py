import streamlit as st
import zipfile
import os
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
import tempfile
from vanta_auditor_client import VantaAuditorClient

st.title("SOC 2 Audit Evidence Mapper")

st.header("🔐 Connect to Vanta Auditor API")
with st.expander("Step 1: Authenticate"):
    client_id = "vci_be6144a382f53d05ef0ec1639dbc76380b0d4f52d1ea07d3"
    client_secret = "vcs_a3ea4c_e1c82b79bcd177f388eb2506a65d9fcd9ffe666d87f0ad40a9597cf7eede3053"
    org_slug = st.text_input("Org Slug (e.g., advantage-partners.com)")

    audit_options = []
    audit_map = {}
    selected_audit_id = ""

    if st.button("List Audits"):
        if not all([client_id, client_secret, org_slug]):
            st.error("Please fill in all fields.")
        else:
            try:
                client = VantaAuditorClient(client_id, client_secret)
                audits_response = client.list_audits(org_slug)
                if "results" in audits_response and "data" in audits_response["results"]:
                    audits = audits_response["results"]["data"]
                    audit_options = [f"{a['customerDisplayName']} ({a['framework']})" for a in audits]
                    audit_map = {f"{a['customerDisplayName']} ({a['framework']})": a['id'] for a in audits}
                    selected_label = st.selectbox("Select an Audit", audit_options)
                    selected_audit_id = audit_map.get(selected_label, "")

                    audit_df = pd.DataFrame(audits)
                    st.dataframe(audit_df[["id", "customerDisplayName", "framework", "auditStartDate", "auditEndDate"]])
                else:
                    st.warning("No audits found or invalid response format.")
            except Exception as e:
                st.error(f"Error fetching audits: {e}")

    if selected_audit_id:
        if st.button("Fetch Evidence from Vanta"):
            try:
                client = VantaAuditorClient(client_id, client_secret)
                test_data = client.list_tests(org_slug, selected_audit_id)
                evidence_data = client.list_evidence(org_slug, selected_audit_id)
                st.success("Data fetched from Vanta!")
                st.subheader("Tests")
                st.json(test_data)
                st.subheader("Evidence")
                st.json(evidence_data)
            except Exception as e:
                st.error(f"Error: {e}")

st.header("📁 Manual Uploads (ZIP + CSV)")
uploaded_zip = st.file_uploader("Upload Evidence ZIP File", type="zip")
uploaded_csv = st.file_uploader("Upload soc2-evidence CSV File", type="csv")
uploaded_controls = st.file_uploader("Upload SOC 2 Controls Mapping CSV File", type="csv")
uploaded_workbook = st.file_uploader("Upload Audit Workbook (.xlsx)", type="xlsx")

upload_trigger = st.button("Run Evidence Mapping")

# (keep all processing code as-is)
