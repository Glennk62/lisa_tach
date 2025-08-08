import streamlit as st
import pandas as pd
import numpy as np
import io

# ========================
# PAGE CONFIG
# ========================
st.set_page_config(
    page_title="LISA Cost Forecast Dashboard",
    layout="wide"
)

# ========================
# SIDEBAR – ASSUMPTIONS
# ========================
st.sidebar.title("Scale Assumptions")
start_year = st.sidebar.number_input("Start Year", min_value=2025, max_value=2100, value=2025, step=1)
end_year = st.sidebar.number_input("End Year", min_value=start_year+1, max_value=2100, value=2030, step=1)

customers_start = st.sidebar.number_input("Starting Customers", min_value=1, value=10, step=1, help="Number of customers at start")
customers_growth = st.sidebar.slider("Annual Customer Growth (%)", 0, 200, 50, step=5, help="Yearly percentage increase in customers")

vehicles_per_customer = st.sidebar.number_input("Vehicles per Customer", min_value=1, value=50, step=1, help="Average number of vehicles per customer")
riders_per_vehicle = st.sidebar.number_input("Riders per Vehicle", min_value=1, value=10, step=1, help="Average riders per vehicle")

st.sidebar.markdown("---")
st.sidebar.title("Cost Rates (€)")
# Base per-unit costs (placeholders)
cost_per_vehicle_compute = st.sidebar.number_input("Compute & Kubernetes per Vehicle", min_value=0, value=50, step=10)
cost_per_vehicle_db = st.sidebar.number_input("Transactional DB per Vehicle", min_value=0, value=15, step=5)
cost_per_vehicle_bigquery = st.sidebar.number_input("Analytics (BigQuery) per Vehicle", min_value=0, value=10, step=5)
cost_per_vehicle_streaming = st.sidebar.number_input("Streaming per Vehicle", min_value=0, value=8, step=2)
cost_per_vehicle_monitoring = st.sidebar.number_input("Monitoring per Vehicle", min_value=0, value=5, step=1)

cost_per_user_auth = st.sidebar.number_input("Authentication (Firebase) per User", min_value=0, value=1, step=1)
cost_per_user_support = st.sidebar.number_input("Support Tools (Intercom) per User", min_value=0, value=1, step=1)

staff_support_per_customer = st.sidebar.number_input("Support Staff per Customer (€)", min_value=0, value=1000, step=500)
staff_devops_per_customer = st.sidebar.number_input("DevOps/Infra Engineer per Customer (€)", min_value=0, value=2000, step=500)

st.sidebar.markdown("---")
st.sidebar.title("Annual Price Increase")
infra_increase = st.sidebar.slider("Infrastructure Inflation (%)", 0, 50, 5, step=1)
staff_increase = st.sidebar.slider("Staff Inflation (%)", 0, 50, 5, step=1)

# ========================
# DATA CALCULATION
# ========================
years = list(range(start_year, end_year + 1))
n_years = len(years)

customers = [customers_start]
for _ in range(1, n_years):
    customers.append(customers[-1] * (1 + customers_growth / 100))

customers = np.array(customers)
vehicles = customers * vehicles_per_customer
users = vehicles * riders_per_vehicle

# Annual cost calculations with inflation
def apply_inflation(base_cost, rate_percent, years_index):
    return base_cost * ((1 + rate_percent/100) ** years_index)

data = {
    "Year": years,
    "Customers": customers.astype(int),
    "Vehicles": vehicles.astype(int),
    "Users": users.astype(int),

    # Infrastructure costs (vehicle-based)
    "Compute & Kubernetes": apply_inflation(cost_per_vehicle_compute * vehicles, infra_increase, np.arange(n_years)),
    "Transactional DB": apply_inflation(cost_per_vehicle_db * vehicles, infra_increase, np.arange(n_years)),
    "Analytics (BigQuery)": apply_inflation(cost_per_vehicle_bigquery * vehicles, infra_increase, np.arange(n_years)),
    "Streaming": apply_inflation(cost_per_vehicle_streaming * vehicles, infra_increase, np.arange(n_years)),
    "Monitoring": apply_inflation(cost_per_vehicle_monitoring * vehicles, infra_increase, np.arange(n_years)),

    # Infrastructure costs (user-based)
    "Auth (Firebase)": apply_inflation(cost_per_user_auth * users, infra_increase, np.arange(n_years)),
    "Support Tools (Intercom)": apply_inflation(cost_per_user_support * users, infra_increase, np.arange(n_years)),

    # Staff costs (customer-based)
    "Support Staff": apply_inflation(staff_support_per_customer * customers, staff_increase, np.arange(n_years)),
    "DevOps/Infra Engineers": apply_inflation(staff_devops_per_customer * customers, staff_increase, np.arange(n_years))
}

df = pd.DataFrame(data)

# Totals
infra_cols = ["Compute & Kubernetes", "Transactional DB", "Analytics (BigQuery)",
              "Streaming", "Monitoring", "Auth (Firebase)", "Support Tools (Intercom)"]
staff_cols = ["Support Staff", "DevOps/Infra Engineers"]

df["Total Infrastructure"] = df[infra_cols].sum(axis=1)
df["Total Staff"] = df[staff_cols].sum(axis=1)
df["Grand Total"] = df["Total Infrastructure"] + df["Total Staff"]

# Per-unit metrics
df["€ per Vehicle"] = df["Grand Total"] / df["Vehicles"]
df["€ per User"] = df["Grand Total"] / df["Users"]
df["€ per Customer"] = df["Grand Total"] / df["Customers"]

# ========================
# MAIN PAGE
# ========================
st.title("LISA Cost Forecast Dashboard")
st.markdown("Forecast of technology and staffing costs as the company scales.")

# Tabs for charts
tab1, tab2 = st.tabs(["Total Cost Overview", "Individual Components"])

with tab1:
    st.subheader("Total Costs Over Time")
    st.area_chart(df.set_index("Year")[["Total Infrastructure", "Total Staff", "Grand Total"]])

with tab2:
    st.subheader("Cost Components Over Time")
    for col in infra_cols + staff_cols:
        st.line_chart(df.set_index("Year")[[col]])

st.markdown("### Forecast Table")
st.dataframe(df.style.format({
    "Customers": "{:,.0f}",
    "Vehicles": "{:,.0f}",
    "Users": "{:,.0f}",
    **{col: "{:,.0f}" for col in infra_cols + staff_cols + ["Total Infrastructure", "Total Staff", "Grand Total"]},
    "€ per Vehicle": "{:,.2f}",
    "€ per User": "{:,.2f}",
    "€ per Customer": "{:,.2f}"
}))

# ========================
# EXCEL EXPORT
# ========================
assumptions = {
    "Start Year": start_year,
    "End Year": end_year,
    "Starting Customers": customers_start,
    "Annual Customer Growth (%)": customers_growth,
    "Vehicles per Customer": vehicles_per_customer,
    "Riders per Vehicle": riders_per_vehicle,
    "Infrastructure Inflation (%)": infra_increase,
    "Staff Inflation (%)": staff_increase
}

assumptions_df = pd.DataFrame(list(assumptions.items()), columns=["Assumption", "Value"])

output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Forecast', index=False)
    assumptions_df.to_excel(writer, sheet_name='Assumptions', index=False)
excel_data = output.getvalue()

st.download_button(
    label="Download Forecast as Excel",
    data=excel_data,
    file_name="LISA_cost_forecast.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
