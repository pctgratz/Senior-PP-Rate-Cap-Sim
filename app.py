
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="Senior Center Funding Calculator", page_icon="logo.png", layout="centered")

# Display the logo and title
st.image("logo.png", width=100)
st.title("Senior Center Per Person Rate Calculator With Capped Funding")

# Function to perform optimization
def optimize_per_person_funding_enum(database, total_funding, base_funding, unincorporated_funding, cap):
    df = pd.DataFrame(database)
    x = df["people_served"].values
    y = df["incentive"].values

    pp_values = np.linspace(0, 2000, 200001)
    best_pp = None
    min_funding_gap = float("inf")

    for PP in pp_values:
        funding_per_center = np.minimum(base_funding + unincorporated_funding * y + PP * x, cap)
        total_funding_used = np.sum(funding_per_center)
        funding_gap = abs(total_funding - total_funding_used)

        if funding_gap < min_funding_gap:
            min_funding_gap = funding_gap
            best_pp = PP
            best_funding_per_center = funding_per_center.copy()

    df["per_person_rate"] = best_pp
    df["per_center_funding"] = best_funding_per_center

    return df, best_pp

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# User input fields
total_funding = st.number_input("Total Funding ($)", min_value=0.0, format="%.2f")
base_funding = st.number_input("Base Funding per Center ($)", min_value=0.0, format="%.2f")
unincorporated_funding = st.number_input("Unincorporated Center Additional Funding ($)", min_value=0.0, format="%.2f")
cap = st.number_input("Maximum Funding per Center ($)", min_value=0.0, format="%.2f")

# Error message placeholder
error_message = st.empty()

if st.button("Run Optimization"):
    if uploaded_file is None:
        st.error("Please upload a CSV file.")
    elif total_funding <= 0 or base_funding < 0 or unincorporated_funding < 0 or cap < 0:
        st.error("Invalid input: Ensure Total Funding > 0, Base Funding >= 0, Unincorporated Funding >= 0, and Cap >= 0.")
    else:
        # Read uploaded CSV
        df = pd.read_csv(uploaded_file)

        # Check if required columns exist
        if not all(col in df.columns for col in ["people_served", "incentive"]):
            st.error("CSV must contain 'people_served' and 'incentive' columns.")
        else:
            # Run optimization
            optimized_df, best_pp = optimize_per_person_funding_enum(df.to_dict(orient="records"), total_funding, base_funding, unincorporated_funding, cap)

            # Check for invalid PP solution
            if best_pp >= 1999.95:
                st.error("Optimization failed: The computed per-person rate is too high (≥ 1999.95).")
            else:
                # Save optimized CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"optimized_{timestamp}.csv"
                optimized_df.to_csv(output_filename, index=False)

                # Provide download link
                st.success("Optimization successful! Download your optimized file below.")
                with open(output_filename, "rb") as file:
                    st.download_button(label="Download Optimized CSV", data=file, file_name=output_filename, mime="text/csv")