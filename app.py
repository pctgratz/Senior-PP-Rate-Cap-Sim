import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

# Set Streamlit page configuration
st.set_page_config(page_title="Senior Center Funding Calculator", page_icon="logo.png", layout="centered")

# Display the logo and title
st.image("logo.png", width=400)  # Enlarged by 2x
st.title("Senior Center Per Person Rate Calculator With Capped Funding")

# Function to perform optimization
def optimize_per_person_funding_enum(database, total_funding, base_funding, unincorporated_funding, cap):
    df = pd.DataFrame(database)
    x = df["people_served"].values
    y = df["incentive"].values
    
    # Implement Per Center Caps
    caps_i = df["per_center_cap"].values if "per_center_cap" in df.columns else np.zeros(len(df))
    caps_i = np.where(caps_i == 0, 1000000000000, caps_i)  # Replace NaN with a large number
    # If a user doesn't supply a cap, Streamlit sends a 0 value. We set it to a large number in this case.
    if cap == 0:
        cap = 1000000000000  # Set cap to a large number if 0

    # Take the minimum of a per_center_cap and the global cap
    caps = np.minimum(caps_i, cap)

    pp_values = np.linspace(0, 2000, 200001)
    best_pp = None
    min_funding_gap = float("inf")

    for PP in pp_values:
        funding_per_center = np.minimum(base_funding + unincorporated_funding * y + PP * x, caps)
        total_funding_used = np.sum(funding_per_center)
        funding_gap = abs(total_funding - total_funding_used)

        if funding_gap < min_funding_gap:
            min_funding_gap = funding_gap
            best_pp = PP
            best_funding_per_center = funding_per_center.copy()

    df["per_person_rate"] = best_pp
    df["per_center_funding"] = best_funding_per_center
    df['Total Funding Provided'] = total_funding
    df['Base Funding Provided'] = base_funding
    df['Unincorporated Center Additional Funding Provided'] = unincorporated_funding
    df['Global Maximum Funding per Center'] = cap

    return df, best_pp

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

total_funding = st.number_input("Total Funding ($)", min_value=0.0, format="%.2f")
base_funding = st.number_input("Base Funding per Center ($)", min_value=0.0, format="%.2f")
unincorporated_funding = st.number_input("Unincorporated Center Additional Funding ($)", min_value=0.0, format="%.2f")
cap = st.number_input("Maximum Funding per Center ($)", min_value=0.0, format="%.2f")

if st.button("Run Optimization"):
    if uploaded_file is None:
        st.error("Please upload a CSV file.")
    elif total_funding <= 0 or base_funding < 0 or unincorporated_funding < 0 or cap < 0:
        st.error("Invalid input: Ensure Total Funding > 0, Base Funding >= 0, Unincorporated Funding >= 0, and Cap >= 0.")
    else:
        df = pd.read_csv(uploaded_file)

        if not all(col in df.columns for col in ["people_served", "incentive"]):
            st.error("CSV must contain 'people_served' and 'incentive' columns.")
        else:
            optimized_df, best_pp = optimize_per_person_funding_enum(df.to_dict(orient="records"), total_funding, base_funding, unincorporated_funding, cap)
            st.success(f"Optimization successful! Best per-person rate: ${best_pp:.2f}")
            st.write(f"**Best Per Person Rate:** ${best_pp:.2f}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"optimized_{timestamp}.csv"
            optimized_df.to_csv(output_filename, index=False)

            with open(output_filename, "rb") as file:
                st.download_button(label="Download Optimized CSV", data=file, file_name=output_filename, mime="text/csv")

            # Warning if total_funding differs significantly from sum of past_funding
            if "past_funding" in df.columns and not df["past_funding"].isnull().all():
                total_past_funding = df["past_funding"].sum()
                if abs(total_funding - total_past_funding) / total_past_funding > 0.1:
                    st.warning("Past and future funding are not comparable because the total amount of funds to optimize for is significantly different from the total amount of past funding.")

            # Visualization if columns exist
            if "past_funding" in df.columns and "program_name" in df.columns and not df[["past_funding", "program_name"]].isnull().all().all():
                st.subheader("Funding Comparison")
                fig, ax = plt.subplots(figsize=(8, 5))
                df_sorted = optimized_df.sort_values("past_funding")
                
                ax.hlines(df_sorted["program_name"], df_sorted["past_funding"], df_sorted["per_center_funding"], color='gray', linewidth=2)
                ax.scatter(df_sorted["past_funding"], df_sorted["program_name"], color='blue', label='Past Funding')
                ax.scatter(df_sorted["per_center_funding"], df_sorted["program_name"], color='green', label='Proposed Funding')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.set_xlabel("Amount ($)")
                ax.set_title("Difference between past and proposed funding")
                ax.legend()
                
                st.pyplot(fig)

# Documentation Section
st.header("Documentation")
st.write("Refer to the following documentation for more details:")
st.write("Funding Formula With Caps:")
st.write("- The CSV must have columns: 'people_served' and 'incentive'.")
st.write("- To enable charting, 'program_name' and 'past_funding' columns must be provided.")
st.write("- All columns except 'program_name' must be numeric.")
st.write("If you do not want to use a cap, either global or per center, set the cap to 0.")
st.write("The CSV cannot have missing values")
st.write("Refer to the following documentation for more details:")
with open("FundingFormulaWithCaps.pdf", "rb") as pdf_file:
    st.download_button(label="Download Documentation", data=pdf_file, file_name="FundingFormulaWithCaps.pdf", mime="application/pdf")
