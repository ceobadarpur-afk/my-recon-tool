import streamlit as st
import pandas as pd

st.set_page_config(page_title="Reconciliation Tool", layout="wide")
st.title("🏦 Online Collection Reconciliation Tool")

# --- 1. UPLOADER SECTION ---
st.header("1. Upload Files")
col1, col2, col3 = st.columns(3)

with col1:
    sdo_files = st.file_uploader("Upload SDO Collection Files", accept_multiple_files=True, type=['csv', 'xlsx'])
with col2:
    bank_file = st.file_uploader("Upload Bank Statement", type=['csv', 'xlsx'])
with col3:
    billdesk_file = st.file_uploader("Upload BillDesk Report", type=['csv', 'xlsx'])

if sdo_files and bank_file and billdesk_file:
    # --- 2. PROCESSING SDO FILES ---
    all_sdo_data = []
    for f in sdo_files:
        df = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
        # Ensure column names match your file (adjust as needed)
        df['SDO_Code'] = df['Consumer_ID'].astype(str).str[:3]
        all_sdo_data.append(df)
    
    sdo_df = pd.concat(all_sdo_data)
    sdo_df['Date'] = pd.to_datetime(sdo_df['Collection_Date']).dt.date
    sdo_summary = sdo_df.groupby(['Date', 'SDO_Code'])['Amount'].sum().reset_index()

    # --- 3. PROCESSING BANK STATEMENT ---
    bank_df = pd.read_excel(bank_file) if bank_file.name.endswith('xlsx') else pd.read_csv(bank_file)
    # Filter for BillDesk transactions
    bank_df = bank_df[bank_df['Description'].str.contains("INDIAIDEAS.COM", case=False, na=False)]
    bank_df['Date'] = pd.to_datetime(bank_df['Transaction_Date']).dt.date
    bank_summary = bank_df.groupby('Date')['Credit_Amount'].sum().reset_index()

    # --- 4. PROCESSING BILLDESK REPORT ---
    bd_df = pd.read_excel(billdesk_file) if billdesk_file.name.endswith('xlsx') else pd.read_csv(billdesk_file)
    bd_df['Date'] = pd.to_datetime(bd_df['Settlement_Date']).dt.date
    bd_summary = bd_df.groupby('Date')['Settled_Amount'].sum().reset_index()

    # --- 5. RECONCILIATION LOGIC ---
    # Merge SDO totals with BillDesk and Bank by Date
    daily_sdo_total = sdo_summary.groupby('Date')['Amount'].sum().reset_index().rename(columns={'Amount': 'Total_SDO_Collection'})
    
    recon = daily_sdo_total.merge(bd_summary, on='Date', how='outer')
    recon = recon.merge(bank_summary, on='Date', how='outer')
    
    recon['Diff_SDO_vs_Bank'] = recon['Total_SDO_Collection'] - recon['Credit_Amount']
    
    # --- 6. DISPLAY RESULTS ---
    st.header("2. Reconciliation Summary")
    st.dataframe(recon.style.highlight_max(axis=0, color='lightgreen'))

    # Detail View by SDO
    st.subheader("SDO-wise Breakdown")
    st.write(sdo_summary)

    # Download Button
    csv = recon.to_csv(index=False).encode('utf-8')
    st.download_button("Download Recon Report", csv, "recon_report.csv", "text/csv")
else:
    st.info("Please upload all files to begin reconciliation.")