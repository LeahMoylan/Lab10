import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.title("Contaminant Analysis App")

st.write("Upload the two Excel/CSV files used previously:")
station_file = st.file_uploader("Upload Station File (Excel/CSV)", type=["csv", "xlsx"])
narrow_file = st.file_uploader("Upload Measurement File (Excel/CSV)", type=["csv", "xlsx"])

if station_file and narrow_file:
    # Load station file
    if station_file.name.endswith('.csv'):
        df_station = pd.read_csv(station_file)
    else:
        df_station = pd.read_excel(station_file)
    
    # Load measurement (narrow) file
    if narrow_file.name.endswith('.csv'):
        df_narrow = pd.read_csv(narrow_file)
    else:
        df_narrow = pd.read_excel(narrow_file)
    
    st.success("Files successfully uploaded!")
    
    # Verify required columns in measurement file
    required_cols = ['CharacteristicName', 'ActivityStartTime/Time', 'ResultMeasureValue', 'OrganizationFormalName']
    missing_cols = [col for col in required_cols if col not in df_narrow.columns]
    if missing_cols:
        st.error(f"The measurement file is missing the following required columns: {', '.join(missing_cols)}")
    else:
        # Normalize the organization names in the measurement data
        df_narrow['org_norm'] = df_narrow['OrganizationFormalName'].astype(str).str.strip().str.lower()
        
        # Select contaminant from available values
        contaminants = df_narrow['CharacteristicName'].dropna().unique()
        contaminant = st.selectbox("Select a contaminant", contaminants)
        
        # Filter measurement data for the selected contaminant.
        df_contaminant = df_narrow[df_narrow['CharacteristicName'] == contaminant].copy()
        
        # Convert to appropriate data types
        df_contaminant['ActivityStartTime/Time'] = pd.to_datetime(df_contaminant['ActivityStartTime/Time'], errors='coerce')
        df_contaminant['ResultMeasureValue'] = pd.to_numeric(df_contaminant['ResultMeasureValue'], errors='coerce')
        df_contaminant.dropna(subset=['ActivityStartTime/Time', 'ResultMeasureValue'], inplace=True)
        
        # Determine date range for the selected contaminant
        if not df_contaminant['ActivityStartTime/Time'].empty:
            min_date = df_contaminant['ActivityStartTime/Time'].min().date()
            max_date = df_contaminant['ActivityStartTime/Time'].max().date()
            date_range = st.date_input("Select date range", [min_date, max_date])
        else:
            st.error("No valid dates found for the selected contaminant.")
            st.stop()
        
        # Update slider range based on measurement values for the selected contaminant.
        if not df_contaminant['ResultMeasureValue'].empty:
            min_val = float(df_contaminant['ResultMeasureValue'].min())
            max_val = float(df_contaminant['ResultMeasureValue'].max())
            value_range = st.slider("Select contaminant value range", min_value=min_val, max_value=max_val, value=(min_val, max_val))
        else:
            st.error("No valid measurement values found for the selected contaminant.")
            st.stop()
        
        # Filter the contaminant data based on the chosen date and value ranges.
        filtered_narrow = df_contaminant[
            (df_contaminant['ActivityStartTime/Time'].dt.date >= date_range[0]) &
            (df_contaminant['ActivityStartTime/Time'].dt.date <= date_range[1]) &
            (df_contaminant['ResultMeasureValue'] >= value_range[0]) &
            (df_contaminant['ResultMeasureValue'] <= value_range[1])
        ]
        
        st.write(f"Records after filtering: {len(filtered_narrow)}")
        
        # Process the station file:
        # Normalize the organization names in the station file for accurate matching.
        try:
            station_join_key = df_station.iloc[:, 1]  # Assuming 'OrganizationFormalName' is in the 2nd column
            station_lat = pd.to_numeric(df_station.iloc[:, 11], errors='coerce')  # 12th column
            station_lon = pd.to_numeric(df_station.iloc[:, 12], errors='coerce')  # 13th column
        except Exception as e:
            st.error("Error extracting required columns from the station file. Please ensure the file has the expected format.")
            st.stop()
        
        df_station = df_station.copy()
        df_station['OrganizationFormalName'] = station_join_key
        df_station['Latitude'] = station_lat
        df_station['Longitude'] = station_lon
        df_station['org_norm'] = df_station['OrganizationFormalName'].astype(str).str.strip().str.lower()
        
        # Identify stations present in the filtered measurement data.
        sites_norm = filtered_narrow['org_norm'].unique()
        filtered_station = df_station[df_station['org_norm'].isin(sites_norm)].drop_duplicates('org_norm')
        
        # Create a Folium map that updates based on the filtered data.
        if not filtered_station.empty:
            center_lat = filtered_station['Latitude'].mean()
            center_lon = filtered_station['Longitude'].mean()
        else:
            center_lat, center_lon = 0, 0
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        for idx, row in filtered_station.iterrows():
            if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=row['OrganizationFormalName']
                ).add_to(m)
        
        st.subheader("Map of Stations with Contaminant Data")
        st_folium(m, width=700)
        
        # Create a trend-over-time plot for the filtered measurement data.
        st.subheader("Contaminant Trend Over Time")
        plt.figure(figsize=(12, 7))
        for site, group in filtered_narrow.groupby('OrganizationFormalName'):
            group = group.sort_values('ActivityStartTime/Time')
            plt.plot(group['ActivityStartTime/Time'], group['ResultMeasureValue'], marker='o', label=site)
        plt.xlabel("Time")
        plt.ylabel("Result Measure Value")
        plt.title(f"Trend Over Time for {contaminant}")
        plt.legend(title="Site", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        plt.tight_layout()
        st.pyplot(plt.gcf())


