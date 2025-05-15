import streamlit as st
import zipfile
import os
import pandas as pd
import difflib
from pathlib import Path
from openpyxl import load_workbook
import tempfile

st.title("SOC 2 Audit Evidence Mapper")

# File upload widgets
uploaded_zip = st.file_uploader("Upload Evidence ZIP File", type="zip")
uploaded_csv = st.file_uploader("Upload soc2-evidence CSV File", type="csv")
project_folder = st.text_input("Enter path to client project folder (e.g. /Clients/ACME-SOC2-2025):")

upload_trigger = st.button("Run Evidence Mapping")

if upload_trigger and project_folder and uploaded_zip and uploaded_csv:
    root = Path(project_folder)
    evidence_folder = root / "Evidence"
    extract_dir = evidence_folder / "_unzipped"

    # Try matching any subfolder that ends with 'Reporting Deliverables'
    deliverables_folder = None
    for subdir in root.iterdir():
        if subdir.is_dir() and subdir.name.lower().strip().endswith("reporting deliverables"):
            deliverables_folder = subdir
            break

    if deliverables_folder is None:
        st.error("Could not find a 'Reporting Deliverables' subfolder in the project folder.")
    else:
        # Ensure folders exist
        evidence_folder.mkdir(parents=True, exist_ok=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded ZIP file to Evidence folder
        zip_path = evidence_folder / uploaded_zip.name
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.read())

        # Save uploaded CSV file and load into DataFrame
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
            tmp_csv.write(uploaded_csv.read())
            tmp_csv_path = tmp_csv.name
        vanta_df = pd.read_csv(tmp_csv_path)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Index extracted files
        evidence_index = []
        for root_dir, dirs, files in os.walk(extract_dir):
            for filename in files:
                full_path = os.path.join(root_dir, filename)
                relative_path = os.path.relpath(full_path, extract_dir)
                folder = os.path.basename(os.path.dirname(full_path))
                evidence_index.append({
                    "Filename": filename,
                    "Relative Path": relative_path,
                    "Folder": folder
                })

        index_df = pd.DataFrame(evidence_index)

        # Locate and load the workbook
        wb_files = list(deliverables_folder.glob("*.xlsx"))
        if not wb_files:
            st.error("No Excel workbook found in the Reporting Deliverables folder.")
        else:
            wb_path = wb_files[0]
            wb = load_workbook(wb_path)

            # Insert Vanta evidence CSV into all-evidence-vanta tab
            if "all-evidence-vanta" in wb.sheetnames:
                del wb["all-evidence-vanta"]
            all_ev_ws = wb.create_sheet("all-evidence-vanta")
            all_ev_ws.append(vanta_df.columns.tolist())
            for row in vanta_df.itertuples(index=False):
                all_ev_ws.append(list(row))

            # Load Tests tab and build mapping
            tests_ws = wb["Tests"]
            tests_data = list(tests_ws.values)
            headers = tests_data[0]
            rows = tests_data[1:]
            tests_df = pd.DataFrame(rows, columns=headers)

            base_df = tests_df[["Reference ID", "test id", "Test"]].copy()
            base_df.columns = ["Reference ID", "Test ID", "Test Description"]

            def match_folder(folder):
                matches = difflib.get_close_matches(folder.lower(), base_df['Test Description'].str.lower(), n=1, cutoff=0.4)
                if matches:
                    matched_row = base_df[base_df['Test Description'].str.lower() == matches[0]].iloc[0]
                    return pd.Series({
                        'Reference ID': matched_row['Reference ID'],
                        'Test ID': matched_row['Test ID'],
                        'Test Description': matched_row['Test Description']
                    })
                else:
                    return pd.Series({'Reference ID': None, 'Test ID': None, 'Test Description': None})

            mapped_df = index_df.join(index_df['Folder'].apply(match_folder))

            # Insert mapping into evidence-index tab
            if "evidence-index" in wb.sheetnames:
                del wb["evidence-index"]
            ev_map_ws = wb.create_sheet("evidence-index")
            ev_map_ws.append(mapped_df.columns.tolist())
            for row in mapped_df.itertuples(index=False):
                ev_map_ws.append(list(row))

            wb.save(wb_path)
            st.success(f"Workbook updated: {wb_path.name}")
            st.dataframe(mapped_df)
