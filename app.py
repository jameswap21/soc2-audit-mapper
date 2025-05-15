import streamlit as st
import zipfile
import os
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
import tempfile

st.title("SOC 2 Audit Evidence Mapper")

# File upload widgets
uploaded_zip = st.file_uploader("Upload Evidence ZIP File", type="zip")
uploaded_csv = st.file_uploader("Upload soc2-evidence CSV File", type="csv")
uploaded_controls = st.file_uploader("Upload SOC 2 Controls Mapping CSV File", type="csv")
uploaded_workbook = st.file_uploader("Upload Audit Workbook (.xlsx)", type="xlsx")

upload_trigger = st.button("Run Evidence Mapping")

if upload_trigger and uploaded_zip and uploaded_csv and uploaded_controls and uploaded_workbook:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        evidence_folder = tmp_path / "Evidence"
        extract_dir = evidence_folder / "_unzipped"
        evidence_folder.mkdir(parents=True, exist_ok=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded files
        zip_path = evidence_folder / uploaded_zip.name
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.read())

        csv_path = tmp_path / "soc2-evidence.csv"
        with open(csv_path, "wb") as f:
            f.write(uploaded_csv.read())
        vanta_df = pd.read_csv(str(csv_path))

        controls_path = tmp_path / "controls.csv"
        with open(controls_path, "wb") as f:
            f.write(uploaded_controls.read())
        controls_df = pd.read_csv(str(controls_path))

        wb_path = tmp_path / uploaded_workbook.name
        with open(wb_path, "wb") as f:
            f.write(uploaded_workbook.read())
        wb = load_workbook(wb_path)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Index evidence files
        evidence_index = []
        for root_dir, dirs, files in os.walk(extract_dir):
            for filename in files:
                full_path = os.path.join(root_dir, filename)
                relative_path = os.path.relpath(full_path, extract_dir)
                folder = os.path.basename(os.path.dirname(full_path))
                evidence_index.append({
                    "Filename": filename,
                    "Relative Path": relative_path,
                    "Control Folder": folder
                })
        index_df = pd.DataFrame(evidence_index)

        # Clean and join controls
        controls_df.columns = controls_df.columns.str.strip()
        controls_df = controls_df.dropna(subset=["ID", "Test name"])
        controls_df["ID"] = controls_df["ID"].astype(str).str.strip()
        controls_df["Test name"] = controls_df["Test name"].astype(str).str.strip()
        index_df["Control Folder"] = index_df["Control Folder"].astype(str).str.strip()

        mapped_df = index_df.merge(
            controls_df,
            how="left",
            left_on="Control Folder",
            right_on="ID"
        )

        # Load Tests sheet and use Reference ID as test ID (e.g., T01, T78)
        if "Tests" in wb.sheetnames:
            tests_ws = wb["Tests"]
            tests_data = list(tests_ws.values)
            tests_headers = tests_data[0]
            tests_rows = tests_data[1:]
            tests_df = pd.DataFrame(tests_rows, columns=tests_headers)

            tests_df["Test"] = tests_df["Test"].astype(str).str.strip()
            tests_df["Reference ID"] = tests_df["Reference ID"].astype(str).str.strip()
            test_map_df = tests_df[["Test", "Reference ID"]].dropna()
            test_map_df.columns = ["Test name", "Test ID"]

            test_map_df["Test name"] = test_map_df["Test name"].astype(str).str.strip()
            mapped_df = mapped_df.merge(
                test_map_df,
                how="left",
                on="Test name"
            )

        # Insert Vanta evidence CSV
        if "all-evidence-vanta" in wb.sheetnames:
            del wb["all-evidence-vanta"]
        all_ev_ws = wb.create_sheet("all-evidence-vanta")
        all_ev_ws.append(vanta_df.columns.tolist())
        for row in vanta_df.itertuples(index=False):
            all_ev_ws.append(list(row))

        # Insert mapping into evidence-index
        if "evidence-index" in wb.sheetnames:
            del wb["evidence-index"]
        ev_map_ws = wb.create_sheet("evidence-index")
        ev_map_ws.append(mapped_df.columns.tolist())
        for row in mapped_df.itertuples(index=False):
            ev_map_ws.append(list(row))

        # Save and offer for download
        updated_path = tmp_path / f"updated_{uploaded_workbook.name}"
        wb.save(updated_path)
        st.success("Workbook successfully updated!")
        st.download_button(
            label="Download Updated Workbook",
            data=updated_path.read_bytes(),
            file_name=updated_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(mapped_df.head(50))
