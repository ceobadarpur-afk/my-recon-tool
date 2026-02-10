import streamlit as st
import pandas as pd

st.set_page_config(page_title="Collection Recon Tool", layout="wide")

st.title("📑 Custom Reconciliation Portal")
st.info("This tool matches SDO Column H (Amount) with BillDesk Column Q (Amount) using Consumer and Bill IDs.")

# --- FILE UPLOADERS ---
col1, col2, col3 = st.columns(3)
with col1:
    sdo_files = st.file_uploader("Upload SDO Files (HeadWise)", accept_multiple_files=True)
with col2:
    bd_files = st.file_uploader("Upload BillDesk Reports", accept_multiple_files=True)
with col3:
    bank_file = st.file_uploader("Upload Bank Statement")

if sdo_files and bd_files and bank_file:
    try:
        # 1. PROCESS SDO FILES (Col B=Cons No, Col D=Bill No, Col H=Amount)
        sdo_list = []
        for f in sdo_files:
            # Reading Excel - Header usually starts at row 0
            df = pd.read_excel(f)
            # Using iloc to get columns by position: B=1, D=3, H=7
            sub_df = df.iloc[:, [1, 3, 7]].copy()
            sub_df.columns = ['Consumer_No', 'Bill_No', 'Amount']
            # Create SDO Code from first 3 digits of Consumer No
            sub_df['SDO_Code'] = sub_df['Consumer_No'].astype(str).str[:3]
            sdo_list.append(sub_df)
        
        master_sdo = pd.concat(sdo_list)
        # Summing by Consumer and Bill No as per your requirement
        sdo_grouped = master_sdo.groupby(['SDO_Code', 'Consumer_No', 'Bill_No'])['Amount'].sum().reset_index()

        # 2. PROCESS BILLDESK FILES (Col Q=Amount at index 16)
        bd_list = []
        for f in bd_files:
            df = pd.read_excel(f)
            # Assuming BillDesk uses similar identifiers in specific columns
            # Adjust indices if Consumer No/Circle Code are in different positions
            # Here we extract Amount from Column Q (index 16)
            bd_sub = df.copy()
            bd_sub['BD_Amount'] = bd_sub.iloc[:, 16] # Column Q
            # We assume Col 0 or 1 contains the Consumer/Circle identifier
            bd_sub = bd_sub.rename(columns={bd_sub.columns[0]: 'BD_Identifier'}) 
            bd_list.append(bd_sub)
        
        master_bd = pd.concat(bd_list)

        # 3. PROCESS BANK STATEMENT (INDIAIDEAS.COM)
        bank_df = pd.read_excel(bank_file)
        # Identify rows with INDIAIDEAS
        bank_mask = bank_df.apply(lambda row: row.astype(str).str.contains('INDIAIDEAS', case=False).any(), axis=1)
        bank_filtered = bank_df[bank_mask].copy()
        
        # --- RECONCILIATION DISPLAY ---
        st.header("Reconciliation Results")
        
        # Summary Totals
        total_sdo = master_sdo['Amount'].sum()
        total_bd = master_bd['BD_Amount'].sum()
        # Find the column that looks like 'Credit' in bank statement to sum
        bank_credit_total = bank_filtered.iloc[:, -1].sum() # Assumes last column is Amount

        m1, m2, m3 = st.columns(3)
        m1.metric("Total SDO Collection", f"₹{total_sdo:,.2f}")
        m2.metric("Total BillDesk Report", f"₹{total_bd:,.2f}")
        m3.metric("Bank Credit (INDIAIDEAS)", f"₹{bank_credit_total:,.2f}")

        # Show Discrepancies
        if total_sdo != total_bd:
            st.error(f"⚠️ Discrepancy Found! Difference: ₹{abs(total_sdo - total_bd):,.2f}")
        else:
            st.success("✅ SDO and BillDesk Totals Match!")

        st.subheader("SDO-wise Summary")
        sdo_summary = master_sdo.groupby('SDO_Code')['Amount'].sum().reset_index()
        st.table(sdo_summary)

    except Exception as e:
        st.error(f"Data Error: {e}. Check if the columns match the positions (B, D, H, Q).")
else:
    st.info("Please upload all files to generate the reconciliation report.")
