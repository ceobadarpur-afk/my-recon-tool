import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="SDO vs BillDesk Recon", layout="wide")

st.title("⚖️ SDO vs BillDesk Detailed Reconciliation")

# --- 1. UPLOADERS ---
col1, col2 = st.columns(2)
with col1:
    sdo_files = st.file_uploader("Upload SDO HeadWise Files", accept_multiple_files=True)
with col2:
    bd_files = st.file_uploader("Upload BillDesk Report Files", accept_multiple_files=True)

# Sidebar for Column Settings (In case BillDesk format changes)
st.sidebar.header("BillDesk Column Settings")
bd_cons_col = st.sidebar.number_input("BillDesk: Consumer No Column Index (A=0, B=1...)", value=0)
bd_circle_col = st.sidebar.number_input("BillDesk: Circle Code Column Index", value=1)

if sdo_files and bd_files:
    try:
        # --- 2. PROCESS SDO DATA ---
        sdo_list = []
        for f in sdo_files:
            df = pd.read_excel(f)
            # Col B=1 (Cons No), D=3 (Bill No), H=7 (Amount)
            sub = df.iloc[:, [1, 3, 7]].copy()
            sub.columns = ['Consumer_No', 'Bill_No', 'SDO_Amount']
            sub['SDO_Code'] = sub['Consumer_No'].astype(str).str[:3]
            sdo_list.append(sub)
        
        df_sdo = pd.concat(sdo_list).groupby(['Consumer_No', 'Bill_No', 'SDO_Code'])['SDO_Amount'].sum().reset_index()
        df_sdo['Key'] = df_sdo['Consumer_No'].astype(str) + "_" + df_sdo['Bill_No'].astype(str)

        # --- 3. PROCESS BILLDESK DATA ---
        bd_list = []
        for f in bd_files:
            df = pd.read_excel(f)
            # Col Q = Index 16 (Amount)
            # Use sidebar inputs for Consumer No and Circle Code
            sub = df.copy()
            sub['BD_Amount'] = sub.iloc[:, 16] 
            sub['BD_Cons'] = sub.iloc[:, bd_cons_col]
            sub['BD_Circle'] = sub.iloc[:, bd_circle_col]
            bd_list.append(sub[['BD_Cons', 'BD_Circle', 'BD_Amount']])
        
        df_bd = pd.concat(bd_list).groupby(['BD_Cons', 'BD_Circle'])['BD_Amount'].sum().reset_index()
        df_bd['Key'] = df_bd['BD_Cons'].astype(str) + "_" + df_bd['BD_Circle'].astype(str)

        # --- 4. RECONCILIATION (OUTER JOIN) ---
        recon = pd.merge(df_sdo, df_bd, on='Key', how='outer')

        # Create Status Column
        def check_status(row):
            if pd.isna(row['SDO_Amount']): return "Missing in SDO"
            if pd.isna(row['BD_Amount']): return "Missing in BillDesk"
            if row['SDO_Amount'] == row['BD_Amount']: return "Matched"
            return "Amount Mismatch"

        recon['Status'] = recon.apply(check_status, axis=1)
        recon['Difference'] = recon['SDO_Amount'].fillna(0) - recon['BD_Amount'].fillna(0)
        # --- 5. RESULTS DISPLAY ---
        st.header("Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total SDO ₹", f"{df_sdo['SDO_Amount'].sum():,.2f}")
        m2.metric("Total BillDesk ₹", f"{df_bd['BD_Amount'].sum():,.2f}")
        m3.metric("Matched Records", len(recon[recon['Status'] == "Matched"]))
        m4.metric("Discrepancies", len(recon[recon['Status'] != "Matched"]))

        # Detailed Tables
        st.subheader("Detailed Report")
        status_filter = st.selectbox("Filter by Status:", ["All", "Matched", "Amount Mismatch", "Missing in BillDesk", "Missing in SDO"])
        
        display_df = recon.copy()
        if status_filter != "All":
            display_df = display_df[display_df['Status'] == status_filter]
        
        st.dataframe(display_df[['SDO_Code', 'Consumer_No', 'Bill_No', 'SDO_Amount', 'BD_Amount', 'Status', 'Difference']], use_container_width=True)

        # Download Report
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            recon.to_excel(writer, index=False, sheet_name='Recon_Report')
        st.download_button("📥 Download Full Recon Report (Excel)", output.getvalue(), "Detailed_Recon.xlsx")

    except Exception as e:
        st.error(f"Error: {e}. Please check your column indices.")



