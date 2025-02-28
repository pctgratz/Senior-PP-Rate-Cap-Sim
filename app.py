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

    pp_values = np.linspace(0, 4000, 400001)
    best_pp = None
    min_funding_gap = float("inf")

    for PP in pp_values:
        funding_per_center = np.minimum(base_funding + unincorporated_funding * y + PP * x, caps)
        total_funding_used = np.sum(funding_per_center)
        funding_gap = abs(total_funding - total_funding_used)

        if funding_gap < (min_funding_gap-.01): # Add a small buffer to avoid floating point errors
            min_funding_gap = funding_gap
            best_pp = round(PP,2)
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
            # Warning if Per Person Rate is set to the maximum value: $4,000
            if best_pp >= 3999.99:
                st.warning("The maximum allowable per person rate in this simulation is $4,000. The optimization may not be feasible with the given constraints.")

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

st.subheader("Understanding the Parameters")
st.write("""
1. **Total Funding ($)**:
   - This is the total amount of money available for distribution among all centers.
   - Ensure that this value is comparable to past funding if you are using historical data for comparison.

2. **Base Funding per Center ($)**:
   - This is the fixed amount of money each center will receive regardless of other factors.
   - Set this to 0 if there is no base funding.

3. **Unincorporated Center Additional Funding ($)**:
   - Additional funding provided to centers that are unincorporated.
   - Set this to 0 if there is no additional funding for unincorporated centers.

4. **Maximum Funding per Center ($)**:
   - This is the cap on the maximum amount of funding any single center can receive.
   - If you do not want to use a cap, set this value to 0.
""")

st.subheader("Preparing Your CSV File")
st.write("""
1. **Required Columns**:
   - The CSV file must contain the following columns:
     - `people_served`: Number of people served by each center.
     - `incentive`: Incentive value for each center.
   - Optional columns for additional features:
     - `program_name`: Name of the program or center.
     - `past_funding`: Historical funding received by each center.

2. **Data Integrity**:
   - Ensure there are no missing values in the CSV file.
   - All columns except `program_name` must contain numeric values.
""")

st.subheader("Important Considerations")
st.write("""
1. **Comparing Total Funding with Past Funding**:
   - The total funding parameter should be comparable to past funding only if the time scales are the same, that is, the time to spend the total funding is similar to the length of time for which past funding was spent
    - The per-center funding will be comparable to past per-center funding only if the total funding is similar, within a 10% margin, of the sum of past funding.
   - If the sum of the capped values is less than the total funds, all centers will receive their cap value.
    - If the tool is used for setting future rates, ensure that the number of people served in the data is representative of the future number of people served. For example, if the number of people served historically was derived from 6 months of service, but future applications are for 12 months of service, the per-person rate will not generalize to recreate the total funding. In this example, you cannot simply half the per-person rate. Similarly, if more Centers apply in the future than were used to generate the historical rate, then the per-person rate will likely be too high to recreate the total funding.

2. **Optimization Constraints**:
   - The optimization process aims to distribute the total funding while respecting the caps and other constraints.
   - If the best per-person rate is set to the maximum value (\$4,000), it indicates that the optimization may not be feasible with the given constraints.
""")

st.subheader("Example Scenario")
st.write("""
- If you have a total funding of \$100,000, a base funding of \$1,000 per center, and an additional funding of \$500 for unincorporated centers, with a cap of \$10,000 per center:
  - Each center will receive at least \$1,000.
  - Unincorporated centers will receive an additional \$500.
  - No center will receive more than \$10,000.
""")

st.subheader("Downloading Results")
st.write("""
- After running the optimization, you can download the optimized CSV file with the results.
- The file will contain the optimized funding distribution for each center, the per-person rate, and the initial parameters submitted.
""")

st.write("Refer to the following documentation for more details:")
with open("FundingFormulaWithCaps.pdf", "rb") as pdf_file:
    st.download_button(label="Download Documentation", data=pdf_file, file_name="FundingFormulaWithCaps.pdf", mime="application/pdf")
