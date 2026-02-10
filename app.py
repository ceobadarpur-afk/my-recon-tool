import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Recon Portal", layout="wide")

st.title("🏦 Automated Reconciliation Portal")

# --- SECTION 1: TEMPLATE DOWNLOADS ---
st.header("1. Download Templates")
st.info("Download these templates first. Fill them with data, then upload them in Section 2.")

col_t1, col_t2, col_t3 = st.columns(3)

def create_template(columns):
    output = io.BytesIO()
    df = pd.DataFrame(columns=columns)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

with col_t1:
    sdo_template = create_template(['Consumer_ID', 'Collection_Date', 'Amount'])
    st.download_button("Download SDO Template", sdo_template, "SDO_Template.xlsx")

with col_t2:
    bank_template = create_template(['Transaction_Date', 'Description', 'Credit_Amount'])
    st.download_button("Download Bank Template", bank_template, "Bank_Template.xlsx")

with col_t3:
    bd_template = create_template(['Settlement_Date', 'Settled_Amount'])
    st.download_button("Download BillDesk Template", bd_template, "BillDesk_Template.xlsx")

st.divider()

# --- SECTION 2: UPLOADS ---
st.header("2. Upload Completed Files")
col1, col2, col3 = st.columns(3)

with col1:
    sdo_files = st.file_uploader("Upload SDO Files", accept_multiple_files=True)
with col2:
    bank_file = st.file_uploader("Upload Bank Statement")
with col3:
    bd_file = st.file_uploader("Upload BillDesk Report")

# --- SECTION 3: PROCESSING ---
if sdo_files and bank_file and bd_file:
    try:
        # 1. Process SDO Data
        all_sdo = []
        for f in sdo_files:
            df = pd.read_excel(f)
            # Create SDO ID from first 3 digits of Consumer_ID
            df['SDO_ID'] = df['Consumer_ID'].astype(str).str[:3]
            all_sdo.append(df)
        
        sdo_df = pd.concat(all_sdo)
        sdo_df['Date'] = pd.to_datetime(sdo_df['Collection_Date']).dt.date
        sdo_summary = sdo_df.groupby(['Date', 'SDO_ID'])['Amount'].sum().reset_index()

        # 2. Process Bank Data
        bank_df = pd.read_excel(bank_file)
        # Filter for INDIAIDEAS
        bank_df = bank_df[bank_df['Description'].str.contains("INDIAIDEAS.COM", case=False, na=False)]
        bank_df['Date'] = pd.to_datetime(bank_df['Transaction_Date']).dt.date
        bank_summary = bank_df.groupby('Date')['Credit_Amount'].sum().reset_index()

        # 3. Process BillDesk Data
        bd_df = pd.read_excel(bd_file)
        bd_df['Date'] = pd.to_datetime(bd_df['Settlement_Date']).dt.date
        bd_summary = bd_df.groupby('Date')['Settled_Amount'].sum().reset_index()

        # 4. Final Comparison
        recon = sdo_summary.groupby('Date')['Amount'].sum().reset_index().rename(columns={'Amount': 'Total_SDO'})
        recon = recon.merge(bd_summary, on='Date', how='outer')
        recon = recon.merge(bank_summary, on='Date', how='outer')
        
        st.header("3. Reconciliation Results")
        st.dataframe(recon, use_container_width=True)
        
        st.subheader("SDO-wise Detailed Breakdown")
        st.write(sdo_summary)

    except Exception as e:
        st.error(f"Error processing files: {e}. Please ensure you used the templates provided above.")
else:
    st.warning("Please upload all files to see the results.")
