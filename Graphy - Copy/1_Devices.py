import os
import streamlit as st
import oracledb
import pandas as pd
import plotly.graph_objects as go
import streamlit_toggle as tog
import plotly.express as px
from branca.element import Figure
import folium
from folium import Figure, Marker, Icon
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from auth import check_authentication,logout,display_sidebar_logo,check_feature_access
from streamlit_tags import st_tags
import math
import pygwalker as pyg
from data_utils import refresh_data

st.set_page_config(page_title="Devices Dashboard", layout="wide")

# Function to reset filters
def reset_filters():
    st.session_state['reset_filters'] = True

CONFIG_FILE = "config.txt"
DEFAULT_DIRECTORY = "./data"

# Function to get the stored directory
def get_stored_directory():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            directory = f.read().strip()
            if os.path.isdir(directory):  # Validate directory
                return directory
    return DEFAULT_DIRECTORY  # Default if invalid


@st.cache_data(ttl=50, show_spinner=True)
def fetch_data():
    directory = get_stored_directory()
    
    if not os.path.exists(directory):
        st.error("❌ No directory exists! Please select the correct directory from settings.")
        return pd.DataFrame()

    file_path = os.path.join(directory, "devices.csv")

    try:
        data = pd.read_csv(file_path, dtype=str)  # Read as string

        # Remove commas from LOCATION_NUMBER and convert to integer
        if "LOCATION_NUMBER" in data.columns:
            data["LOCATION_NUMBER"] = data["LOCATION_NUMBER"].str.replace(",", "", regex=True).astype(int)

        # Apply formatting to all large numerical columns
        numeric_columns = ["TOTAL_TRANS", "DEVICE_COUNT"]
        for col in numeric_columns:
            if col in data.columns:
                data[col] = data[col].astype(float).apply(lambda x: f"{x:,.0f}")

        # Remove 'UNKNOWN' rows from CAMPUS
        data = data[data["CAMPUS"].str.upper() != "UNKNOWN"]

        return data

    except Exception as error:
        st.error(f"❌ Error reading CSV file: {error}")
        return pd.DataFrame()
    
# ----- Original Filters For Devices Tab -----

def create_sidebar_filters(df):
    # Custom CSS for styling the Reset Filters button
    custom_css = """
    <style>
        .reset-button-container {
            padding-top: 25px;  /* Adjust this value to move the button lower */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    # Default values for session state
    default_values = {
        'building_selection': ['All'],
        'device_type_selection': ['All'],
        'tps_status_selection': 'All',
        'reader_status_selection': "All",
        'installation_year_selection': ['All'],
        'term_type_selection': ['All'],
        'campus_selection': 'All'  # Ensure single selection
    }

    # Initialize session state with default values if not set
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Reset filters if needed
    if st.session_state.get('reset_filters', False):
        for key, value in default_values.items():
            st.session_state[key] = value
        st.session_state['reset_filters'] = False

    def clean_selection(key):
        if "All" in st.session_state[key] and len(st.session_state[key]) > 1:
            st.session_state[key].remove("All")

    # First row of filters (Campus, Reader Status, Device Type, Installation Year)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        campus_options = ['All', 'CG', 'RSMAES', 'CSTARS']
        campus_selection = st.pills(
            "Select Campus:",
            options=campus_options,
            default=st.session_state.get('campus_selection', 'All'),
            key='campus_selection',
            selection_mode="single"  # Single selection mode
        )
    
    with col2:
        reader_status_options = sorted(
            [status for status in df['NODE_STATUS'].dropna().unique() if str(status).upper() != "UNKNOWN"]
        )

        reader_status_selection = st.pills(
            "Select Reader Status:",
            options=["All"] + reader_status_options,
            default="All",
            key='reader_status_selection',
            selection_mode="single"  # Single selection mode
        )
        
    with col3:
        device_options = ['All'] + sorted(df['DEVICE_TYPE'].dropna().unique())
        
        # Filter device options if campus is selected
        if campus_selection not in [None, 'All']:
            device_options = ['All'] + sorted(df[df['CAMPUS'] == campus_selection]['DEVICE_TYPE'].dropna().unique())

        device_type_selection = st.multiselect(
            "Select Device Type:",
            options=device_options,
            default=st.session_state['device_type_selection'],
            key='device_type_selection',
            on_change=clean_selection,
            args=('device_type_selection',)
        )
        
    with col4:
        df_years = pd.to_datetime(df['LOCAL_DATE_CREATED'], errors='coerce').dt.year.dropna().astype(int).unique()
        year_options = ['All'] + sorted(df_years)

        installation_year_selection = st.multiselect(
            "Select Installation Year:",
            options=year_options,
            default=st.session_state['installation_year_selection'],
            key='installation_year_selection',
            on_change=clean_selection,
            args=('installation_year_selection',)
        )

    # Second row of filters (Reset Filters, TPS Status, Term Type, Building Name)
    col5, col6, col7, col8, col9 = st.columns(5)
    
    with col5:
        # Add reset filters button with custom styling
        st.markdown('<div class="reset-button-container">', unsafe_allow_html=True)
        if st.button("Reset Filters", key="reset_filters_main"):
            st.session_state['reset_filters'] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
            
    with col6:
        tps_status_options = ['All'] + sorted(df['TPS_STATUS'].dropna().unique())
        
        tps_status_selection = st.pills(
            "Select TPS Status:",
            options=tps_status_options,
            default=st.session_state.get('tps_status_selection', 'All'),
            key='tps_status_selection',
            selection_mode="single"  # Single selection mode
        )
        
    with col7:
        term_options = ['All'] + sorted(df['TERM_TYPE_SID'].dropna().astype(str).unique())

        term_type_selection = st.multiselect(
            "Select Term Type:",
            options=term_options,
            default=st.session_state['term_type_selection'],
            key='term_type_selection',
            on_change=clean_selection,
            args=('term_type_selection',)
        )
        
    with col8:
        building_options = ['All'] + sorted(df['BUILDING_NAME'].dropna().unique())

        # Filter building options based on campus selection
        if campus_selection not in [None, 'All']:
            building_options = ['All'] + sorted(df[df['CAMPUS'] == campus_selection]['BUILDING_NAME'].dropna().unique())

        building_selection = st.multiselect(
            "Select Building Name:",
            options=building_options,
            default=st.session_state['building_selection'],
            key='building_selection',
            on_change=clean_selection,
            args=('building_selection',)
        )

    return (
        campus_selection,
        building_selection,
        device_type_selection,
        tps_status_selection,
        reader_status_selection,
        installation_year_selection,
        term_type_selection
    )
# def create_sidebar_filters(df):
#     # Default values for session state
#     default_values = {
#         'building_selection': ['All'],
#         'device_type_selection': ['All'],
#         'tps_status_selection': 'All',
#         'reader_status_selection': "All",
#         'installation_year_selection': ['All'],
#         'term_type_selection': ['All'],
#         'campus_selection': 'All'  # Ensure single selection
#     }

#     # Initialize session state with default values if not set
#     for key, value in default_values.items():
#         if key not in st.session_state:
#             st.session_state[key] = value

#     # Reset filters if needed
#     if st.session_state.get('reset_filters', False):
#         for key, value in default_values.items():
#             st.session_state[key] = value
#         st.session_state['reset_filters'] = False

#     def clean_selection(key):
#         if "All" in st.session_state[key] and len(st.session_state[key]) > 1:
#             st.session_state[key].remove("All")

#     # First row of filters (Building Name, Device Type, Term Type, Installation Year)
#     col1, col2, col3, col4, col5 = st.columns(5)
#     with col1:
#         building_options = ['All'] + sorted(df['BUILDING_NAME'].dropna().unique())

#         if st.session_state['campus_selection']==None or "All" not in st.session_state['campus_selection']:
#             building_options = ['All'] + sorted(df[df['CAMPUS'].isin([st.session_state['campus_selection']])]['BUILDING_NAME'].dropna().unique())

#         building_selection = st.multiselect(
#             "Select Building Name:",
#             options=building_options,
#             default=st.session_state['building_selection'],
#             key='building_selection',
#             on_change=clean_selection,
#             args=('building_selection',)
#         )

#     with col2:
#         device_options = ['All'] + sorted(df['DEVICE_TYPE'].dropna().unique())
        
#         if "All" not in building_selection:
#             device_options = ['All'] + sorted(df[df['BUILDING_NAME'].isin(building_selection)]['DEVICE_TYPE'].dropna().unique())

#         device_type_selection = st.multiselect(
#             "Select Device Type:",
#             options=device_options,
#             default=st.session_state['device_type_selection'],
#             key='device_type_selection',
#             on_change=clean_selection,
#             args=('device_type_selection',)
#         )

#     with col3:
#         term_options = ['All'] + sorted(df['TERM_TYPE_SID'].dropna().astype(str).unique())

#         term_type_selection = st.multiselect(
#             "Select Term Type:",
#             options=term_options,
#             default=st.session_state['term_type_selection'],
#             key='term_type_selection',
#             on_change=clean_selection,
#             args=('term_type_selection',)
#         )

#     with col4:
#         df_years = pd.to_datetime(df['LOCAL_DATE_CREATED'], errors='coerce').dt.year.dropna().astype(int).unique()
#         year_options = ['All'] + sorted(df_years)

#         installation_year_selection = st.multiselect(
#             "Select Installation Year:",
#             options=year_options,
#             default=st.session_state['installation_year_selection'],
#             key='installation_year_selection',
#             on_change=clean_selection,
#             args=('installation_year_selection',)
#         )
        

#     with col5:
#         tps_status_options = ['All'] + sorted(df['TPS_STATUS'].dropna().unique())
#         index = tps_status_options.index(st.session_state['tps_status_selection']) if st.session_state['tps_status_selection'] in tps_status_options else 0

#         tps_status_selection = st.selectbox(
#             "Select TPS Status:",
#             options=tps_status_options,
#             index=index,
#             key='tps_status_selection'
#         )

#     col6, col7 = st.columns(2)

#     with col6:
#         campus_options = ['All','CG', 'RSMAES', 'CSTARS']
#         campus_selection = st.pills(
#             "Select Campus:",
#             options=campus_options,
#             default=st.session_state.get('campus_selection', 'CG'),
#             key='campus_selection',
#             selection_mode="single"  # Single selection mode
#         )

#     with col7:
#         reader_status_options = sorted(
#             [status for status in df['NODE_STATUS'].dropna().unique() if str(status).upper() != "UNKNOWN"]
#         )

#         reader_status_selection = st.pills(
#             "Select Reader Status:",
#             options=["All"] + reader_status_options,
#             default= "All",
#             key='reader_status_selection',
#             selection_mode="single"  # Single selection mode
#         )

#     return (
#         campus_selection,
#         building_selection,
#         device_type_selection,
#         tps_status_selection,
#         reader_status_selection,
#         installation_year_selection,
#         term_type_selection
#     )


def display_totals_per_item(df_filtered):
    # st.subheader("Device Summary")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Device Summary")
    test.write("This area offers a breakdown of the access control infrastructure by device type, presented through both bar and pie charts. It provides a clear visual representation of how different device categories contribute to the overall system, helping users quickly grasp the distribution and scale of deployed hardware.")
    show_totals_per_item = st.toggle(label="Hide/View", key="toggle_switch_totals_per_item", value=True)

    if show_totals_per_item:
        item_column = 'DEVICE_TYPE'
        totals_per_item = df_filtered[item_column].value_counts().reset_index()
        totals_per_item = totals_per_item.sort_values(by=item_column, ascending=True)

        totals_per_item.columns = [item_column, 'Total']
        
        # Format the 'Total' column for display with commas
        totals_per_item['Total_formatted'] = totals_per_item['Total'].apply(lambda x: f"{x:,}")

        # Create columns
        col1, col2 = st.columns([1, 1])

        with col1:
            fig_bar = px.bar(totals_per_item, x=item_column, y='Total', text='Total_formatted')
            fig_bar.update_traces(texttemplate='%{text}', textposition='outside')
            fig_bar.update_layout(
                uniformtext_minsize=8, 
                uniformtext_mode='hide', 
                xaxis_title="Device Type", 
                yaxis_title="Total Count", 
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            fig_pie = px.pie(
                totals_per_item, 
                names=item_column, 
                values='Total', 
                hole=0.6
            )
            fig_pie.update_traces(textinfo='percent+label')

            

            # Adjust layout to prevent label cutoff
            fig_pie.update_layout(
                uniformtext_minsize=8, 
                uniformtext_mode='hide',
                height=560,  
                margin=dict(l=10, r=10, t=160, b=90)  
            )

            fig_pie.update_traces(sort=False)

            st.plotly_chart(fig_pie, use_container_width=True)

def display_raw_data(df_filtered):
    # Apply custom CSS for a wider scrollbar
    st.markdown(
        """
        <style>
        /* Increase scrollbar width */
        ::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        /* Change scrollbar thumb */
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 6px;
        }
        /* Change scrollbar track */
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.subheader("Detailed Data:")
    show_data = st.toggle(label="Hide/View", key="toggle_switch", value=True)
    
    if show_data:
        df_filtered = df_filtered.reset_index(drop=True)
        df_filtered.index += 1
        st.dataframe(df_filtered)

def display_total_devices_per_building(df_filtered):
    # st.subheader("Locations per Building")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Locations per Building")
    test.write("This stacked bar chart provides a breakdown of location counts by device type for each building, complemented by a color-coded legend for clarity. A flexible slider tool below the graph allows users to easily navigate through the list of buildings, with adjustable sizing for a more tailored viewing experience.")
    
    if st.toggle("Hide/View", key="toggle_switch_device_summary", value=True):
        buildings = sorted(df_filtered['BUILDING_NAME'].unique())
        n = len(buildings)
        if n == 0:
            st.write("No building data available")
            return
        
        total_counts = df_filtered.groupby('BUILDING_NAME').size().to_dict()
        fig = go.Figure()
        
        for device_type in sorted(df_filtered['DEVICE_TYPE'].unique()):
            df_subset = df_filtered[df_filtered['DEVICE_TYPE'] == device_type]
            counts = df_subset['BUILDING_NAME'].value_counts().to_dict()
            # make the 1000 in 1,000 instead of 1000
            formatted_counts = {b: f"{count:,}" if count >= 1000 else str(count) for b, count in counts.items()}
            filtered_counts = {b: counts[b] for b in buildings if b in counts}
            
            fig.add_trace(go.Bar(
                x=list(filtered_counts.keys()),
                y=list(filtered_counts.values()),
                name=device_type
            ))
        
        fig.add_trace(go.Scatter(
            x=list(total_counts.keys()),
            y=list(total_counts.values()),
            mode='text',
            text=[f"{v:,}" for v in total_counts.values()],
            textposition='top center',
            showlegend=False
        ))
        
        fig.update_layout(
            barmode='stack',
            xaxis_title="Building Names",
            yaxis_title="Device Counts",
            xaxis=dict(
                categoryorder='array', 
                categoryarray=buildings,
                rangeslider=dict(visible=True),
                range=[len(buildings)//4, 3*len(buildings)//4] 
            ),
            height=1200,
            width=1500,
            legend=dict(traceorder='normal')
        )
        
        st.plotly_chart(fig, use_container_width=True)


def display_devices_by_year(df_filtered):
    # st.subheader("Installations per Year")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Installations per Year")
    test.write("This section illustrates the historical growth of the access control system, showing the number of new locations added each year by device type. Presented in stacked bar format, users can toggle between Calendar Year and Fiscal Year views to analyze trends based on their preferred reporting structure.")

    show_devices_by_year = st.toggle(label="Hide/View", key="toggle_switch_device_per_year", value=True)

    if show_devices_by_year:
        df_filtered['LOCAL_DATE_CREATED'] = pd.to_datetime(df_filtered['LOCAL_DATE_CREATED'], errors='coerce')
        df_filtered = df_filtered.dropna(subset=['LOCAL_DATE_CREATED'])

        if df_filtered.empty:
            st.write("No valid data after filtering dates.")
            return

        # Toggle to switch between Calendar Year and Fiscal Year with clear labels
        view_mode = st.toggle("Calendar / Fiscal", key="toggle_fiscal_year", value=True, 
                             help="Toggle between Calendar Year (Jan 1-Dec 31) and Fiscal Year (Jun 1-May 31)")
        


        # Apply fiscal or calendar year transformation
        if view_mode:  # Fiscal Year calculation
            # For fiscal year, if month is June or later (>=6), use current year, otherwise prior year
            df_filtered['Year'] = df_filtered.apply(
                lambda row: row['LOCAL_DATE_CREATED'].year + 1 if row['LOCAL_DATE_CREATED'].month >= 6 else row['LOCAL_DATE_CREATED'].year, 
                axis=1
            )
            year_title = "Fiscal Year"
        else:  # Calendar Year calculation
            df_filtered['Year'] = df_filtered['LOCAL_DATE_CREATED'].dt.year
            year_title = "Calendar Year"

        # Group data
        year_device_counts = df_filtered.groupby(['Year', 'DEVICE_TYPE']).size().unstack(fill_value=0)
        
        if year_device_counts.empty:
            st.write("No installation data available for the selected year type.")
            return

        sorted_device_types = sorted(year_device_counts.columns)  # Sorting in ascending order

        # Create the plot
        fig = go.Figure()
        for device_type in sorted_device_types:
            fig.add_trace(go.Bar(x=year_device_counts.index, y=year_device_counts[device_type], name=device_type))

        # Add total installations per year as annotations
        year_totals = year_device_counts.sum(axis=1)
        fig.add_trace(go.Scatter(
            x=year_totals.index,
            y=year_totals.values,
            mode='text',
            text=[f"{x:,}" for x in year_totals.values],
            textposition='top center',
            showlegend=False
        ))

        # Update layout for better visualization
        fig.update_layout(
            barmode='stack',
            xaxis_title=f'Installation {year_title}',
            yaxis_title='Device Count',
            xaxis=dict(tickmode='linear'),
            width=1200,
            height=700,
            legend=dict(traceorder='normal'),
            title=f"Device Installations by {year_title}"
        )

        st.plotly_chart(fig, use_container_width=True)
                
        # Step 1: Pivot table
        pivot = df_filtered.pivot_table(
            index=['Year', 'BUILDING_NAME'],
            columns='DEVICE_TYPE',
            aggfunc='size',
            fill_value=0
        )

        # Step 2: Reset index to make 'Year' and 'BUILDING_NAME' columns
        pivot = pivot.reset_index()

        # Step 3: Calculate 'Total Locations'
        device_columns = pivot.columns[2:]  # all device type columns
        pivot['Total Locations'] = pivot[device_columns].sum(axis=1)

        # Step 4: Sort as required
        pivot = pivot.sort_values(
            by=['Year', 'BUILDING_NAME'],
            ascending=[False, True]  # Year descending, Building Name ascending
        )

        # Step 5: Reorder columns: Year, Building Name, (devices alphabetically), Total Locations
        final_columns = ['Year', 'BUILDING_NAME'] + sorted(device_columns) + ['Total Locations']
        pivot = pivot[final_columns]
        pivot = pivot.reset_index().drop('index', axis=1)
        
        # Rename the Year column to include the year type
        pivot = pivot.rename(columns={'Year': year_title})
        
        st.subheader("Detailed Data:")
        if st.toggle(label="Hide/View", key="toggle_switch_integrations_data", value=True):
            # # Add a caption to explain the date range being displayed
            # if view_mode:
            #     st.caption(f"Note: Each fiscal year (e.g., '2025') represents data from June 1, 2024 through May 31, 2025")
            # else:
            #     st.caption(f"Note: Each calendar year represents data from January 1 through December 31 of that year")
            st.dataframe(pivot)


def display_overview_metrics(df):
    """
    Displays summary metrics for campuses, buildings, infrastructure devices, reader devices, and locations.
    """
    # st.markdown("### Overview Metrics")

    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Overview Metrics")
    test.write("This section provides a high-level summary of key indicators across all locations within the access control infrastructure. The displayed totals update dynamically based on user-applied filters, ensuring that the metrics remain relevant to the selected subset of data. These filters also influence all other visualizations on the page, enabling a fully synchronized analytical experience.")

    # Ensure TERM_TYPE_SID is numeric
    df['TERM_TYPE_SID'] = pd.to_numeric(df['TERM_TYPE_SID'], errors='coerce')

    # Filter out unknown campuses
    known_campuses = df[df['CAMPUS'].str.lower() != 'unknown']

    # Calculate unique counts
    total_campuses = known_campuses['CAMPUS'].nunique()
    total_buildings = df['BUILDING_NAME'].nunique()
    total_locations = df['LOCATION_NUMBER'].nunique()

    # Define TERM_TYPE_SID values that qualify as readers.
    reader_term_types = {2112, 2114, 2119, 2213}
    total_readers = df.loc[df['TERM_TYPE_SID'].isin(reader_term_types), 'LOCATION_NUMBER'].nunique()

    # Define TERM_TYPE_SID values that qualify as infrastructure devices.
    infrastructure_term_types = {2210, 2211, 2212, 2110, 2111, 2113, 2118}
    total_infra_devices = df.loc[df['TERM_TYPE_SID'].isin(infrastructure_term_types), 'LOCATION_NUMBER'].nunique()

    # Apply custom CSS styles
    st.markdown("""
        <style>
            .metric-box {
                border: 3px solid #4B0082;  /* Purple border only */
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                background-color: transparent;  /* No fill, transparent background */
                color: white;  /* White text for dark theme */
                margin: 10px;
                box-shadow: 4px 4px 10px rgba(0,0,0,0.1); /* Soft shadow */
            }
            .metric-label {
                font-weight: bold;
                font-size: 22px;  /* Increased label font size */
                color: white;
            }
            .metric-value {
                font-size: 30px;  /* Increased value font size */
                font-weight: bold;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

    # Display metrics in columns with custom styling
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-label">🏫 Campuses</div><div class="metric-value">{total_campuses:,}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-label">🌆 Buildings</div><div class="metric-value">{total_buildings:,}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-label">🔩 Infrastructure</div><div class="metric-value">{total_infra_devices:,}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="metric-label">📱 Readers</div><div class="metric-value">{total_readers:,}</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="metric-box"><div class="metric-label">📍 Locations</div><div class="metric-value">{total_locations:,}</div></div>', unsafe_allow_html=True)

#------ Campus Explorer Section ------
def initialize_session_state(df):
    if 'CAMPUS_C' not in st.session_state:
        # st.session_state.CAMPUS_C = "All"
        st.session_state.CAMPUS_C = "CG"
    if 'BUILDING_NAME_C' not in st.session_state:
        st.session_state.BUILDING_NAME_C = "All"
    if 'TECHNOLOGY_C' not in st.session_state:
        st.session_state.TECHNOLOGY_C = df["TECH"].unique().tolist()
    if 'MAP_CENTER' not in st.session_state:
        st.session_state.MAP_CENTER = (25.7175, -80.2786)
    if 'ZOOM_LEVEL' not in st.session_state:
        st.session_state.ZOOM_LEVEL = 15

def plot_building_tech_per_campus(filtered_df):
    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    # st.subheader("Building Tech per Campus")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Building Tech per Campus")
    test.write("This section provides a campus-level overview of building technologies in use. It summarizes how many buildings within each campus utilize VertX, Mercury, or a combination of both systems, offering insight into the technological footprint and standardization across locations.")
    show_chart = st.toggle(label="Hide/View", key="toggle_stacked_bar_chart", value=True)

    if show_chart:
        # Remove buildings with UNKNOWN campus
        filtered_df = filtered_df[filtered_df['CAMPUS'] != "UNKNOWN"]

        # Apply logic to label buildings with both "VertX" and "Mercury" as "VertX/Mercury"
        filtered_df["TECH_LABEL"] = filtered_df.groupby("BUILDING_NAME")["TECH"].transform(
            lambda x: "VertX/Mercury" if {"VertX", "Mercury"}.issubset(set(x)) else x.iloc[0]
        )

        # Aggregate building count per campus and technology
        agg_df = filtered_df.groupby(['CAMPUS', 'TECH_LABEL'])['BUILDING_NAME'].nunique().reset_index(name='COUNT')

        # Compute total buildings per campus
        campus_totals = agg_df.groupby('CAMPUS')['COUNT'].sum().reset_index()
        campus_totals.rename(columns={'COUNT': 'TOTAL_COUNT'}, inplace=True)

        # Merge totals with aggregated data
        agg_df = agg_df.merge(campus_totals, on='CAMPUS')

        # Create stacked bar chart
        fig = px.bar(
            agg_df, 
            x='CAMPUS', 
            y='COUNT', 
            color='TECH_LABEL',
            labels={'COUNT': 'Building Count', 'CAMPUS': 'Campuses'},
            text=None  # Ensure section-wise values are not displayed
        )

        # Add total count labels on top of bars
        for campus, total in zip(campus_totals['CAMPUS'], campus_totals['TOTAL_COUNT']):
            fig.add_annotation(
                x=campus, 
                y=total, 
                text=f"{total:,}", 
                showarrow=False,
                font=dict(size=14), 
                yshift=15
            )

        # Update layout for better visualization
        fig.update_layout(
            barmode='stack', 
            xaxis={'categoryorder': 'total descending'}
        )

        st.plotly_chart(fig, use_container_width=True)

def filter_search_dataframe(df: pd.DataFrame, search_query: list) -> pd.DataFrame:
    if not search_query:  # If empty, return full DataFrame
        return df  

    search_terms = [term.strip().lower() for term in search_query if term.strip()]  # Ensure list is clean

    return df[df.apply(
        lambda row: all(
            any(term in str(cell).lower() for cell in row) for term in search_terms
        ),
        axis=1
    )]


def filter_dataframe(df):
    campus = st.session_state.CAMPUS_C
    building_name = st.session_state.BUILDING_NAME_C
    technology = st.session_state.TECHNOLOGY_C

    filtered_df = df.copy()
    
    if campus != "All":
        filtered_df = filtered_df[filtered_df["CAMPUS"] == campus]
    
    if building_name != "All":
        filtered_df = filtered_df[
            filtered_df["BUILDING_NAME"].str.contains(building_name, case=False, na=False)
        ]
    
    if technology:
        filtered_df = filtered_df[filtered_df["TECH"].isin(technology)]
    
    return filtered_df

@st.cache_data
def get_filtered_dataframe(df, campus, building_name, technology):
    """Cache the filtered data for graphs (full dataset)."""
    filtered_df = df.copy()

    if campus != "All":
        filtered_df = filtered_df[filtered_df["CAMPUS"] == campus]

    if building_name != "All":
        filtered_df = filtered_df[
            filtered_df["BUILDING_NAME"].str.contains(building_name, case=False, na=False)
        ]

    if technology:
        filtered_df = filtered_df[filtered_df["TECH"].isin(technology)]

    return filtered_df  # Full dataset for graphs


@st.cache_data
def get_map_dataframe(df):
    """Create a separate cached dataframe for the map with only necessary columns."""
    return df[["LOCATION_LATITUDE", "LOCATION_LONGITUDE", "BUILDING_NAME", "TECH"]].dropna()

def reset_filters(df):
    # Reset only session state variables that are not tied to widgets
    # st.session_state.CAMPUS_C = "All"
    st.session_state.CAMPUS_C = "CG"
    st.session_state.BUILDING_NAME_C = "All"
    st.session_state.TECHNOLOGY_C = df["TECH"].unique().tolist()
    st.session_state.MAP_CENTER = (25.7175, -80.2786)
    st.session_state.ZOOM_LEVEL = 15
    
    st.rerun()

@st.cache_data()
def get_map_dataframe(filtered_df):
    filtered_df["LOCATION_LATITUDE"] = pd.to_numeric(filtered_df["LOCATION_LATITUDE"], errors="coerce")
    filtered_df["LOCATION_LONGITUDE"] = pd.to_numeric(filtered_df["LOCATION_LONGITUDE"], errors="coerce")

    filtered_df["TECH_LABEL"] = filtered_df.groupby("BUILDING_NAME")["TECH"].transform(
        lambda x: "VertX/Mercury" if {"VertX", "Mercury"}.issubset(set(x)) else x.iloc[0]
    )

    print(filtered_df["TECH_LABEL"].unique())

    # Group and aggregate the data
    map_df = (
        filtered_df.groupby(["BUILDING_NAME", "TECH_LABEL"])
        .agg({"LOCATION_LATITUDE": "first", "LOCATION_LONGITUDE": "first"})
        .reset_index()
    )
    
    # Filter out rows with NaN coordinates to prevent map errors
    map_df = map_df.dropna(subset=["LOCATION_LATITUDE", "LOCATION_LONGITUDE"])
    
    return map_df

def create_map(filtered_map_df):

    if st.session_state["CAMPUS_C"] == 'CG':
        st.session_state["ZOOM_LEVEL"] = 15
    
    if st.session_state["CAMPUS_C"] == 'RSMAES':
        st.session_state["ZOOM_LEVEL"] = 18

    if st.session_state["CAMPUS_C"] == 'CSTARS':
        st.session_state["ZOOM_LEVEL"] = 19

    # Check if we have valid data to display
    if filtered_map_df.empty:
        st.warning("No location data available with valid coordinates for the selected filters.")
        return

    fig = Figure(width=800, height=600)
    mymap = folium.Map(
        location=st.session_state.get("MAP_CENTER", [25.7175, -80.2786]),
        zoom_start=st.session_state.get("ZOOM_LEVEL", 15)
    )
    fig.add_child(mymap)
    
    # Additional safety check: verify coordinates are not NaN before creating markers
    for _, row in filtered_map_df.iterrows():
        lat = row["LOCATION_LATITUDE"]
        lon = row["LOCATION_LONGITUDE"]
        
        # Skip this row if coordinates are NaN or invalid
        if pd.isna(lat) or pd.isna(lon):
            continue
            
        color = {"VertX": "red", "Mercury": "green", "VertX/Mercury": "orange"}.get(row["TECH_LABEL"], "gray")
        Marker(
            location=(float(lat), float(lon)),
            popup=f"{row['BUILDING_NAME']} ({row['TECH_LABEL']})",
            icon=Icon(color=color, icon='info-sign')
        ).add_to(mymap)
    folium_static(mymap, width=1370, height=600)

def display_campus_details(filtered_df):
    """Display campus details below the map showing relevant statistics."""
    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return

    # Group by campus, building ID, building name, and technology, then count locations
    summary_df = (
        filtered_df.groupby(["CAMPUS", "BUILDING_ID", "BUILDING_NAME", "TECH"])
        .size()
        .reset_index(name="Total_Location_Count")
    )

    st.dataframe(summary_df, use_container_width=True)


def campus_map_filters(df):
    # st.subheader("Map of Building Locations")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Map of Building Locations")
    test.write("This interactive map offers a campus-level view of all buildings with access control integrations, displaying their precise locations along with the associated technologies in use—VertX, Mercury, or a combination of both. Users can filter the map by campus, technology type, and building name for a tailored exploration. An accompanying data sheet summarizes the number of locations per building under each technology, providing a quick reference for infrastructure distribution.")
    show_map = st.toggle(label="Hide/View", key="toggle_map_display", value=True)
    
    if show_map:
        # st.subheader("Filters")
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            # campus_options = ["All"] + list(df["CAMPUS"].unique())
            campus_options = list(df["CAMPUS"].unique())
            # campus = st.session_state["CAMPUS_C"] = st.pills("By Campus", options=campus_options, key="CAMPUS_SELECT", selection_mode="single", default="All")
            campus = st.session_state["CAMPUS_C"] = st.pills("By Campus:", options=campus_options, key="CAMPUS_SELECT", selection_mode="single", default="CG")        
        with col2:
            df["TECH_LABEL"] = df.groupby("BUILDING_NAME")["TECH"].transform(
                lambda x: "VertX/Mercury" if set(x) == {"VertX", "Mercury"} else x.iloc[0]
            )
            technology_options = ["All"] + list(df["TECH_LABEL"].unique())
            technology = st.pills("By Technology:", options=technology_options, key="TECHNOLOGY_SELECT", selection_mode="single", default = "All")
        
        # with col3:

        #     filtered_buildings = df[df["CAMPUS"] == campus]["BUILDING_NAME"].unique()
            
        #     building_name_options = ["All"] + sorted(list(filtered_buildings))
        #     building_name = st.selectbox("By Building Name:", options=building_name_options, index=0, key="BUILDING_NAME_SELECT")

        st.write(" ")
        col4, col5, col6 = st.columns([2, 2, 3])
        with col4:
            def reset_filters_for_map():
                st.session_state["CAMPUS_SELECT"] = "CG"
                st.session_state["BUILDING_NAME_SELECT"] = "All"
                st.session_state["TECHNOLOGY_SELECT"] = "All"
                st.session_state["MAP_CENTER"] = [25.7175, -80.2786]
                st.session_state["ZOOM_LEVEL"] = 15
            # Add custom CSS to add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(4) {
                padding-top: 5px;
            }
            </style>
            """, unsafe_allow_html=True)
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(4) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            st.button("Reset Filters", key="reset_filters_button_campus", on_click=reset_filters_for_map)
        with col5:
            filtered_buildings = df[df["CAMPUS"] == campus]["BUILDING_NAME"].unique()
            building_name_options = ["All"] + sorted(list(filtered_buildings))
            building_name = st.selectbox("By Building Name:", options=building_name_options, index=0, key="BUILDING_NAME_SELECT")
        
        # FIXED CAMPUS FILTER LOGIC
        filtered_df = df if campus == "All" else df[df["CAMPUS"] == campus]

        if technology:
            if technology == "All":
                filtered_df = filtered_df[filtered_df["TECH_LABEL"].isin(list(df["TECH_LABEL"].unique()))]
            else:
                filtered_df = filtered_df[filtered_df["TECH_LABEL"]==technology]

        if building_name != "All":
            filtered_df = filtered_df[filtered_df["BUILDING_NAME"] == building_name]
        
        if not filtered_df.empty:
            filtered_df["LOCATION_LATITUDE"] = pd.to_numeric(filtered_df["LOCATION_LATITUDE"], errors="coerce")
            filtered_df["LOCATION_LONGITUDE"] = pd.to_numeric(filtered_df["LOCATION_LONGITUDE"], errors="coerce")
            
            if building_name != "All":
                lat = float(filtered_df["LOCATION_LATITUDE"].iloc[0])
                lon = float(filtered_df["LOCATION_LONGITUDE"].iloc[0])
                st.session_state["MAP_CENTER"] = [lat, lon]
                st.session_state["ZOOM_LEVEL"] = 18
            else:
                mean_lat = float(filtered_df["LOCATION_LATITUDE"].mean())
                mean_lon = float(filtered_df["LOCATION_LONGITUDE"].mean())
                st.session_state["MAP_CENTER"] = [mean_lat, mean_lon]
                st.session_state["ZOOM_LEVEL"] = 16

        map_df = get_map_dataframe(filtered_df)
        st.markdown("""
        <style>
        div[data-testid="column"]:nth-of-type(4) {
            padding-top: 25px;
        }
        </style>
        """, unsafe_allow_html=True)
        create_map(map_df)

        st.subheader("Detailed Data:")
        show_data = st.toggle(label="Hide/View", key="toggle_map_data", value=True)
        if show_data:        
            display_campus_details(filtered_df)

    for key in ["selected_campus_voltage", "selected_building_voltage", "selected_device_voltage"]:
        if key in st.session_state and isinstance(st.session_state[key], str):
            parts = st.session_state[key].rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                new_value = int(parts[1]) + 1
                st.session_state[key] = f"{parts[0]}_{new_value}"




def display_online_integrations_per_campus(df_filtered):
    # st.subheader("Locations per Campus")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Locations per Campus")
    test.write("This stacked bar chart illustrates the distribution of device types across each campus by showing the total number of locations per device type. A color-coded legend enhances readability, making it easy to compare infrastructure composition across different campuses at a glance.")
    show_campus_summary = st.toggle(label="Hide/View", key="toggle_switch_campus_summary", value=True)

    if show_campus_summary:
        fig = go.Figure()
        df_filtered = df_filtered[df_filtered['CAMPUS'] != "UNKNOWN"]
        campus_counts = df_filtered['CAMPUS'].value_counts().to_dict()
        totals = {campus: 0 for campus in campus_counts}

        # Sort DEVICE_TYPE alphabetically and reverse it to control legend order
        device_types_sorted = sorted(df_filtered['DEVICE_TYPE'].unique(), reverse=True)

        for device_type in device_types_sorted:  # Reverse order to make legend go top to bottom
            df_subset = df_filtered[df_filtered['DEVICE_TYPE'] == device_type]
            if not df_subset.empty:
                counts = df_subset['CAMPUS'].value_counts().to_dict()
                for campus, count in counts.items():
                    totals[campus] += count
                fig.add_trace(go.Bar(x=list(counts.keys()), y=list(counts.values()), name=device_type))

        # Display total values on top of bars
        totals_formatted = {campus: f"{count:,}" for campus, count in totals.items()}
        fig.add_trace(go.Scatter(x=list(totals.keys()), y=list(totals.values()), mode='text',
                                 text=list(totals_formatted.values()), textposition='top center'))

        fig.update_layout(barmode='stack', xaxis={'categoryorder': 'total descending'}, 
                          width=1450, height=800, xaxis_title="Campuses", yaxis_title="Location Count")

        st.plotly_chart(fig)

@st.cache_data(ttl=3600)
def fetch_transaction_data():
    directory = get_stored_directory()
    
    if not os.path.exists(directory):
        st.error("❌ No directory exists! Please select the correct directory from settings.")
        return pd.DataFrame()

    file_path = os.path.join(directory, "transactions.csv")

    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        
        # Convert TRANSACTION_DATE to datetime
        df['TRANSACTION_DATE'] = pd.to_datetime(df['TRANSACTION_DATE'], errors='coerce')
        
        # Extract date
        df['DATE'] = df['TRANSACTION_DATE'].dt.date
        
        # Convert TRANSACTION_HOUR to numeric
        df['HOUR'] = pd.to_numeric(df['TRANSACTION_HOUR'], errors='coerce')

        # Load the campus mapping DataFrame
        campus_df = fetch_data()  # Assuming fetch_data() provides campus-building mapping

        # Ensure column names match (adjust if necessary)
        campus_df = campus_df[['BUILDING_NAME', 'CAMPUS']].drop_duplicates()

        # Merge transaction data with campus information
        df = df.merge(campus_df, on='BUILDING_NAME', how='left')

        return df

    except Exception as error:
        st.error(f"❌ Error reading CSV file: {error}")
        return pd.DataFrame()

def display_txn_details(filtered_df):
    if filtered_df.empty:
        st.write("No transaction data available for the selected criteria.")
        return
    
    st.dataframe(filtered_df.sort_values(by="TOTAL_TRANS", ascending=False))


def process_transaction_data(df, start_date, end_date, selected_hour, selected_campus, device_exclusion):
    # Filter by date range
    filtered_df = df[(df['DATE'] >= start_date) & (df['DATE'] <= end_date)].copy()
    
    # Filter by campus selection

    if not selected_campus:
        selected_campus=[None]
    if selected_campus == ["All"]:
        selected_campus_all = filtered_df['CAMPUS'].dropna().unique().tolist()
    else:
        filtered_df = filtered_df[filtered_df['CAMPUS'].isin(selected_campus)]
    # Convert selected hour
    if selected_hour == "11:59 PM":
        hour_value = 23
    else:
        hour_value = int(selected_hour.split(' ')[0]) % 12 + (12 if 'PM' in selected_hour else 0)

    if device_exclusion is not None:
        filtered_df = filtered_df[~filtered_df['DEVICE_TYPE'].isin(device_exclusion)]

    # Filter by hour
    filtered_df = filtered_df[filtered_df['HOUR'] <= hour_value]
    
    # Aggregate transactions per building
    aggregated_df = filtered_df.groupby(['CAMPUS', 'BUILDING_NAME'], as_index=False)['TOTAL_TRANS'].sum()
    
    return aggregated_df

# def plot_transaction_volume(transactional_df):
#     # st.subheader("Transaction Volume per Campus")

#     test = st.expander("Click to view or hide description", expanded=True)
#     test.title("Transaction Volume per Campus")
#     test.write("This treemap visualizes the total number of transactions per building, illustrating each building's contribution to the overall transaction volume. Users can filter the data by campus, custom date ranges, and hour of the day. Hourly totals are aggregated and displayed at the end of each hour, offering detailed insights into peak usage patterns and activity distribution.")
    
#     device_data = fetch_data()

#     merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')

#     merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
#     merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)

#     # Clean DEVICE_TYPE
#     merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")

#     # Show Map Toggle
#     show_map = st.toggle(label="Hide/View", key="toggle_map_display_transactions", value=True)

#     if show_map:
#         # Campus Selection with st.pills (No default selection, selecting none means all campuses)
#         campuses = merged_df['CAMPUS'].dropna().unique().tolist()
#         # campuses = ["All"] + [campus for campus in campuses if campus.lower() != "unknown"]
#         campuses = [campus for campus in campuses if campus.lower() != "unknown"]
#         # Get min/max dates
#         min_date = merged_df['DATE'].min()
#         max_date = merged_df['DATE'].max()

#         # Initialize session state variables
#         if "start_date" not in st.session_state:
#             st.session_state["start_date"] = min_date
#         if "end_date" not in st.session_state:
#             st.session_state["end_date"] = max_date
#         if "selected_hour" not in st.session_state:
#             st.session_state["selected_hour"] = "11:59 PM"
#         if "selected_campus" not in st.session_state:
#             st.session_state["selected_campus"] = ["CG"]
#         if "selected_device_type_exclusion" not in st.session_state:
#             st.session_state["selected_device_type_exclusion"] = ["None"]  # Initialize as a list
#         if "pills_key" not in st.session_state:
#             st.session_state["pills_key"] = 0

#         col1, col2, col3, col4 = st.columns(4)
#         with col2:
#             start_date = st.date_input("Start Date:", value=st.session_state["start_date"], min_value=min_date, max_value=max_date)
#         with col3:
#             end_date = st.date_input("End Date:", value=st.session_state["end_date"], min_value=min_date, max_value=max_date)

#         # Ensure the user can pick the same date
#         if start_date > end_date:
#             st.warning("End date cannot be before start date. Please adjust.")
#             st.stop()

#         with col4:
#             hours = [f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)] + ["11:59 PM"]
#             selected_hour = st.select_slider("Hour of Day:", options=hours, value=st.session_state["selected_hour"])

#         # Convert hour properly (including 11:59 PM handling)
#         if selected_hour == "11:59 PM":
#             hour_value = 23.99  # Slightly below midnight
#         else:
#             hour_value = int(selected_hour.split(' ')[0]) % 12 + (12 if 'PM' in selected_hour else 0)

#         with col1:

#             selected_campus = st.pills("Select Campus:", campuses, selection_mode="single",
#                            default=st.session_state["selected_campus"], key=f"pills_{st.session_state['pills_key']}")

#             # Ensure selected_campus is always a list
#             if isinstance(selected_campus, str):
#                 selected_campus = [selected_campus]

#         # Define the callback function for device type selection
#         def handle_device_exclusion_selection():
#             # Get the current selection from the widget
#             selected = st.session_state["device_type_widget"]
            
#             # Handle selection logic
#             if "None" in selected:
#                 # If "All" is among the selections
#                 other_selections = [d for d in selected if d != "None"]
#                 if other_selections:
#                     # If there are other selections besides "All", remove "All"
#                     st.session_state["selected_device_type_exclusion"] = other_selections
#                 else:
#                     # Only "All" is selected
#                     st.session_state["selected_device_type_exclusion"] = ["None"]
#             elif not selected:
#                 # If nothing is selected, default to "All"
#                 st.session_state["selected_device_type_exclusion"] = ["None"]
#             else:
#                 # Normal case: specific devices selected (no "All")
#                 st.session_state["selected_device_type_exclusion"] = selected

#         # Filter device options based on selected campus
#         # Create boolean masks
#         mask_campus = merged_df["CAMPUS"].isin(selected_campus)
#         mask_device = merged_df["DEVICE_TYPE"].notna()

#         # Combine masks using bitwise AND
#         combined_mask = mask_campus & mask_device

#         # Filter and extract unique device types
#         device_options = merged_df[combined_mask]['DEVICE_TYPE'].unique().tolist()

#         col1, col2 = st.columns([1, 4])
#         with col1:
#             # Determine which options to show based on current selection
#             current_selection = st.session_state["selected_device_type_exclusion"]
            
#             # If specific options are selected, don't show "All" in the dropdown
#             if current_selection and current_selection != ["None"]:
#                 display_options = [d for d in device_options if d != "None"]
#             else:
#                 # When "All" or nothing is selected, show all options including "All"
#                 display_options = device_options.copy()
#                 if "None" not in display_options:
#                     display_options.append("None")
            
#             # Use the current session state as the default
#             device_multiselect = st.multiselect(
#                 "Device Type Exclusions:",
#                 options=display_options,
#                 default=current_selection,
#                 key="device_type_widget",  # Different key than session state
#                 on_change=handle_device_exclusion_selection
#             )
            
#             # Update device_type_exclusion from session state for use in filtering
#             device_type_exclusion = st.session_state["selected_device_type_exclusion"]
#         if device_type_exclusion == ['None']:
#             device_type_exclusion = None

#         # Reset filters button
#         if st.button("Reset Filters"):
#             st.session_state["start_date"] = min_date
#             st.session_state["end_date"] = max_date
#             st.session_state["selected_hour"] = "11:59 PM"
#             st.session_state["selected_campus"] = ["CG"]  # Reset campus selection explicitly
#             st.session_state["selected_device_type_exclusion"] = ["None"]  # List, not string
#             st.session_state["pills_key"] += 1  # Update key to force UI refresh
#             st.rerun()

#         # Store updates in session state
#         st.session_state["start_date"] = start_date
#         st.session_state["end_date"] = end_date
#         st.session_state["selected_hour"] = selected_hour
#         st.session_state["selected_campus"] = selected_campus

#         # Process and display data
#         # Pass device_type_exclusion to process_transaction_data without applying filter here
#         cumulative_df = process_transaction_data(merged_df, start_date, end_date, selected_hour, selected_campus, device_type_exclusion)
        
#         if not cumulative_df.empty:
#             fig = px.treemap(
#                 cumulative_df,
#                 path=[px.Constant("Transactions"), 'CAMPUS', 'BUILDING_NAME'],
#                 values='TOTAL_TRANS',
#                 color='TOTAL_TRANS',
#                 hover_data=['BUILDING_NAME'],
#                 color_continuous_scale='Reds'
#             )
#             fig.update_traces(texttemplate="%{label}<br>%{value:,}", textposition="middle center")
#             fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
#             st.plotly_chart(fig, use_container_width=True)

#             st.subheader("Detailed Data:")
#             show_data = st.toggle(label="Hide/View", key="toggle_txn2_data", value=True)
#             if show_data:
#                 display_txn_details(cumulative_df)

#         else:
#             st.write("No data available for this selection.")


# def plot_transaction_volume(transactional_df):
#     # st.subheader("Transaction Volume per Campus")

#     test = st.expander("Click to view or hide description", expanded=True)
#     test.title("Transaction Volume per Campus")
#     test.write("This treemap visualizes the total number of transactions per building, illustrating each building's contribution to the overall transaction volume. Users can filter the data by campus, custom date ranges, and hour of the day. Hourly totals are aggregated and displayed at the end of each hour, offering detailed insights into peak usage patterns and activity distribution.")
    
#     device_data = fetch_data()
#     merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
    
#     # st.write(transactional_df[transactional_df["BUILDING_NAME"]=="Richmond Campus Building 2"])

#     merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
#     merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)

#     # Clean DEVICE_TYPE
#     merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")
#     # st.write(merged_df[merged_df["CAMPUS"]=="CSTARS"])

#     # Show Map Toggle
#     show_map = st.toggle(label="Hide/View", key="toggle_map_display_transactions", value=True)

#     if show_map:
#         # Campus Selection with st.pills (No default selection, selecting none means all campuses)
#         campuses = merged_df['CAMPUS'].dropna().unique().tolist()
#         # campuses = ["All"] + [campus for campus in campuses if campus.lower() != "unknown"]
#         campuses = [campus for campus in campuses if campus.lower() != "unknown"]
#         # Get min/max dates
#         min_date = merged_df['DATE'].min()
#         max_date = merged_df['DATE'].max()

#         # Initialize session state variables
#         # Ensure default values are within the allowed range
#         if "start_date" not in st.session_state or not (min_date <= st.session_state["start_date"] <= max_date):
#             st.session_state["start_date"] = min_date

#         if "end_date" not in st.session_state or not (min_date <= st.session_state["end_date"] <= max_date):
#             st.session_state["end_date"] = max_date

#         if "selected_hour" not in st.session_state:
#             st.session_state["selected_hour"] = "11:59 PM"
#         if "selected_campus" not in st.session_state:
#             st.session_state["selected_campus"] = ["CG"]
#         if "selected_device_type_exclusion" not in st.session_state:
#             st.session_state["selected_device_type_exclusion"] = ["None"]  # Initialize as a list
#         if "pills_key" not in st.session_state:
#             st.session_state["pills_key"] = 0

#         # Define the callback function for device type selection
#         def handle_device_exclusion_selection():
#             # Get the current selection from the widget
#             selected = st.session_state["device_type_widget"]
            
#             # Handle selection logic
#             if "None" in selected:
#                 # If "All" is among the selections
#                 other_selections = [d for d in selected if d != "None"]
#                 if other_selections:
#                     # If there are other selections besides "All", remove "All"
#                     st.session_state["selected_device_type_exclusion"] = other_selections
#                 else:
#                     # Only "All" is selected
#                     st.session_state["selected_device_type_exclusion"] = ["None"]
#             elif not selected:
#                 # If nothing is selected, default to "All"
#                 st.session_state["selected_device_type_exclusion"] = ["None"]
#             else:
#                 # Normal case: specific devices selected (no "All")
#                 st.session_state["selected_device_type_exclusion"] = selected

#         # Filter device options based on selected campus
#         # Create boolean masks
#         mask_campus = merged_df["CAMPUS"].isin(st.session_state["selected_campus"])
#         mask_device = merged_df["DEVICE_TYPE"].notna()

#         # Combine masks using bitwise AND
#         combined_mask = mask_campus & mask_device

#         # Filter and extract unique device types
#         device_options = merged_df[combined_mask]['DEVICE_TYPE'].unique().tolist()

#         # FIRST ROW: Campus, Start Date, Device Type Exclusions
#         col1, col2, col3, col4 = st.columns(4)
        
#         with col1:
#             selected_campus = st.pills("Select Campus:", campuses, selection_mode="single",
#                            default=st.session_state["selected_campus"], key=f"pills_{st.session_state['pills_key']}")

#             # Ensure selected_campus is always a list
#             if isinstance(selected_campus, str):
#                 selected_campus = [selected_campus]
        
#         with col2:
#             start_date = st.date_input("Start Date:", value=st.session_state["start_date"], min_value=min_date, max_value=max_date)
        
#         with col3:
#             # Determine which options to show based on current selection
#             current_selection = st.session_state["selected_device_type_exclusion"]
            
#             # If specific options are selected, don't show "All" in the dropdown
#             if current_selection and current_selection != ["None"]:
#                 display_options = [d for d in device_options if d != "None"]
#             else:
#                 # When "All" or nothing is selected, show all options including "All"
#                 display_options = device_options.copy()
#                 if "None" not in display_options:
#                     display_options.append("None")
            
#             # Use the current session state as the default
#             device_multiselect = st.multiselect(
#                 "Device Type Exclusions:",
#                 options=display_options,
#                 default=current_selection,
#                 key="device_type_widget",  # Different key than session state
#                 on_change=handle_device_exclusion_selection
#             )
            
#             # Update device_type_exclusion from session state for use in filtering
#             device_type_exclusion = st.session_state["selected_device_type_exclusion"]

#         # SECOND ROW: Reset Filters, End Date, Hour of Day
#         col4, col5, col6, col7 = st.columns(4)
        
#         with col4:
#             # Add custom CSS to add padding above the reset button
#             st.markdown("""
#             <style>
#             div[data-testid="column"]:nth-of-type(4) {
#                 padding-top: 25px;
#             }
#             </style>
#             """, unsafe_allow_html=True)
#             # Reset filters button (positioned at the start of second row)
#             if st.button("Reset Filters"):
#                 st.session_state["start_date"] = min_date
#                 st.session_state["end_date"] = max_date
#                 st.session_state["selected_hour"] = "11:59 PM"
#                 st.session_state["selected_campus"] = ["CG"]  # Reset campus selection explicitly
#                 st.session_state["selected_device_type_exclusion"] = ["None"]  # List, not string
#                 st.session_state["pills_key"] += 1  # Update key to force UI refresh
#                 st.rerun()
        
#         with col5:
#             end_date = st.date_input("End Date:", value=st.session_state["end_date"], min_value=min_date, max_value=max_date)
        
#         with col6:
#             hours = [f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)] + ["11:59 PM"]
#             selected_hour = st.select_slider("Hour of Day:", options=hours, value=st.session_state["selected_hour"])

#         if device_type_exclusion == ['None']:
#             device_type_exclusion = None

#         # Ensure the user can pick the same date
#         if start_date > end_date:
#             st.warning("End date cannot be before start date. Please adjust.")
#             st.stop()

#         # Convert hour properly (including 11:59 PM handling)
#         if selected_hour == "11:59 PM":
#             hour_value = 23.99  # Slightly below midnight
#         else:
#             hour_value = int(selected_hour.split(' ')[0]) % 12 + (12 if 'PM' in selected_hour else 0)

#         # Store updates in session state
#         st.session_state["start_date"] = start_date
#         st.session_state["end_date"] = end_date
#         st.session_state["selected_hour"] = selected_hour
#         st.session_state["selected_campus"] = selected_campus

#         # Apply filters for metrics (same logic as process_transaction_data)
#         filtered_df_for_metrics = merged_df.copy()
        
#         # Apply campus filter
#         filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['CAMPUS'].isin(selected_campus)]
        
#         # Apply date filters
#         filtered_df_for_metrics = filtered_df_for_metrics[
#             (filtered_df_for_metrics['DATE'] >= start_date) & 
#             (filtered_df_for_metrics['DATE'] <= end_date)
#         ]
        
#         # Apply hour filter
#         filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['HOUR'] <= hour_value]
        
#         # Apply device type exclusion filter
#         if device_type_exclusion is not None:
#             filtered_df_for_metrics = filtered_df_for_metrics[~filtered_df_for_metrics['DEVICE_TYPE'].isin(device_type_exclusion)]

#         # Apply custom CSS styles for metrics
#         st.markdown("""
#             <style>
#                 .metric-box {
#                     border: none;
#                     border-radius: 15px;
#                     padding: 20px;
#                     text-align: center;
#                     background-color: #1E3A8A;
#                     color: white;
#                     margin: 10px;
#                     box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
#                 }
#                 .metric-label {
#                     font-weight: bold;
#                     font-size: 22px;
#                     color: white;
#                 }
#                 .metric-value {
#                     font-size: 30px;
#                     font-weight: bold;
#                     color: white;
#                 }
#             </style>
#         """, unsafe_allow_html=True)

#         # Calculate transaction counts for metrics
#         tx_counts = {
#             "Magstripe": 0,
#             "Proximity": 0,
#             "Biometric": 0,
#             "MobileANDREMOTE": 0
#         }
        
#         if not filtered_df_for_metrics.empty:
#             # Check if each column exists before accessing it
#             if 'MAGSTRIPE' in filtered_df_for_metrics.columns:
#                 tx_counts["Magstripe"] = int(filtered_df_for_metrics['MAGSTRIPE'].sum())
#             if 'PROXIMITY' in filtered_df_for_metrics.columns:
#                 tx_counts["Proximity"] = int(filtered_df_for_metrics['PROXIMITY'].sum())
#             if 'BIOMETRIC' in filtered_df_for_metrics.columns:
#                 tx_counts["Biometric"] = int(filtered_df_for_metrics['BIOMETRIC'].sum())
#             if 'MOBILEANDREMOTE' in filtered_df_for_metrics.columns:
#                 tx_counts["MobileANDREMOTE"] = int(filtered_df_for_metrics['MOBILEANDREMOTE'].sum())

#         # Display metrics
#         col1, col2, col3, col4 = st.columns(4)
#         with col1:
#             st.markdown(f'<div class="metric-box"><div class="metric-label">💳 Magstripe</div><div class="metric-value">{tx_counts["Magstripe"]:,}</div></div>', unsafe_allow_html=True)
#         with col2:
#             st.markdown(f'<div class="metric-box"><div class="metric-label">📳 Proximity</div><div class="metric-value">{tx_counts["Proximity"]:,}</div></div>', unsafe_allow_html=True)
#         with col3:
#             st.markdown(f'<div class="metric-box"><div class="metric-label">🧬 Biometric</div><div class="metric-value">{tx_counts["Biometric"]:,}</div></div>', unsafe_allow_html=True)
#         with col4:
#             st.markdown(f'<div class="metric-box"><div class="metric-label">📱 Mobile/Remote</div><div class="metric-value">{tx_counts["MobileANDREMOTE"]:,}</div></div>', unsafe_allow_html=True)

#         # Process and display data
#         # Pass device_type_exclusion to process_transaction_data without applying filter here
#         cumulative_df = process_transaction_data(merged_df, start_date, end_date, selected_hour, selected_campus, device_type_exclusion)
        
#         if not cumulative_df.empty:
#             fig = px.treemap(
#                 cumulative_df,
#                 path=[px.Constant("Transactions"), 'CAMPUS', 'BUILDING_NAME'],
#                 values='TOTAL_TRANS',
#                 color='TOTAL_TRANS',
#                 hover_data=['BUILDING_NAME'],
#                 color_continuous_scale='Reds'
#             )
#             fig.update_traces(texttemplate="%{label}<br>%{value:,}", textposition="middle center")
#             fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
#             st.plotly_chart(fig, use_container_width=True)

#             st.subheader("Detailed Data:")
#             show_data = st.toggle(label="Hide/View", key="toggle_txn2_data", value=True)
#             if show_data:
#                 display_txn_details(cumulative_df)

#         else:
#             st.write("No data available for this selection.")

def plot_transaction_volume(transactional_df):
    # Description expander
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Transaction Volume per Campus")
    test.write("This treemap visualizes the total number of transactions per building, illustrating each building's contribution to the overall transaction volume. Users can filter the data by campus, custom date ranges, and hour of the day. Hourly totals are aggregated and displayed at the end of each hour, offering detailed insights into peak usage patterns and activity distribution.")
    
    device_data = fetch_data()
    merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
    
    merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
    merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)

    # Clean DEVICE_TYPE
    merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")

    # Show Map Toggle
    show_map = st.toggle(label="Hide/View", key="toggle_map_display_transactions", value=True)

    if show_map:
        # Get unique campuses
        campuses_only = merged_df['CAMPUS'].dropna().unique().tolist()
        campuses = ["All"] + [campus for campus in campuses_only if campus.lower() != "unknown"]
        # Get min/max dates
        min_date = merged_df['DATE'].min()
        max_date = merged_df['DATE'].max()

        # Initialize session state variables
        if "start_date" not in st.session_state or not (min_date <= st.session_state["start_date"] <= max_date):
            # st.session_state["start_date"] = min_date
            st.session_state["start_date"] = max_date

        if "end_date" not in st.session_state or not (min_date <= st.session_state["end_date"] <= max_date):
            st.session_state["end_date"] = max_date

        if "selected_hour" not in st.session_state:
            st.session_state["selected_hour"] = "11:59 PM"
        if "selected_campus" not in st.session_state:
            st.session_state["selected_campus"] = ["All"]
        if "selected_device_type_exclusion" not in st.session_state:
            st.session_state["selected_device_type_exclusion"] = ["None"]
        if "pills_key" not in st.session_state:
            st.session_state["pills_key"] = 0
        
        # Create a container for metrics that will appear above filters
        metrics_container = st.container()
        
        # Add custom CSS for spacing between metrics and filters
        st.markdown("""
        <style>
        .metrics-filter-spacer {
            margin-bottom: 20px;
        }
        .metric-box {
            border: 3px solid #4B0082;  /* Purple border only */
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            background-color: transparent;  /* No fill, transparent background */
            color: white;  /* White text for dark theme */
            margin: 10px;
            box-shadow: 4px 4px 10px rgba(0,0,0,0.1); /* Soft shadow */
        }
        .metric-label {
            font-weight: bold;
            font-size: 22px;  /* Increased label font size */
            color: white;
        }
        .metric-value {
            font-size: 30px;  /* Increased value font size */
            font-weight: bold;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)

        st.subheader("Filter Options:")

        # Container for filters (will be below metrics)
        with st.container():
            st.markdown('<div class="metrics-filter-spacer"></div>', unsafe_allow_html=True)
            
            
            # Define the callback function for device type selection
            def handle_device_exclusion_selection():
                # Get the current selection from the widget
                selected = st.session_state["device_type_widget"]
                
                # Handle selection logic
                if "None" in selected:
                    # If "None" is among the selections
                    other_selections = [d for d in selected if d != "None"]
                    if other_selections:
                        # If there are other selections besides "None", remove "None"
                        st.session_state["selected_device_type_exclusion"] = other_selections
                    else:
                        # Only "None" is selected
                        st.session_state["selected_device_type_exclusion"] = ["None"]
                elif not selected:
                    # If nothing is selected, default to "None"
                    st.session_state["selected_device_type_exclusion"] = ["None"]
                else:
                    # Normal case: specific devices selected
                    st.session_state["selected_device_type_exclusion"] = selected

            # Filter device options based on selected campus
            if "All" in st.session_state["selected_campus"]:
                mask_campus = merged_df["CAMPUS"].notna()
            else:
                mask_campus = merged_df["CAMPUS"].isin(st.session_state["selected_campus"])
            
            mask_device = merged_df["DEVICE_TYPE"].notna()
            combined_mask = mask_campus & mask_device
            device_options = merged_df[combined_mask]['DEVICE_TYPE'].unique().tolist()

            # FIRST ROW: Campus, Start Date, Device Type Exclusions
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                selected_campus = st.pills("Select Campus:", campuses, selection_mode="single",
                            default=st.session_state["selected_campus"], key=f"pills_{st.session_state['pills_key']}")

                if selected_campus == ["All"]:
                    selected_campus = campuses_only
                # Ensure selected_campus is always a list
                if isinstance(selected_campus, str):
                    selected_campus = [selected_campus]
            
            with col2:
                start_date = st.date_input("Start Date:", value=st.session_state["start_date"], min_value=min_date, max_value=max_date)
            
            with col3:
                # Determine which options to show based on current selection
                current_selection = st.session_state["selected_device_type_exclusion"]
                
                # If specific options are selected, don't show "None" in the dropdown
                if current_selection and current_selection != ["None"]:
                    display_options = [d for d in device_options if d != "None"]
                else:
                    # When "None" or nothing is selected, show all options including "None"
                    display_options = device_options.copy()
                    if "None" not in display_options:
                        display_options.append("None")
                
                # Use the current session state as the default
                device_multiselect = st.multiselect(
                    "Device Type Exclusions:",
                    options=display_options,
                    default=current_selection,
                    key="device_type_widget",
                    on_change=handle_device_exclusion_selection
                )
                
                # Update device_type_exclusion from session state for use in filtering
                device_type_exclusion = st.session_state["selected_device_type_exclusion"]

            # SECOND ROW: Reset Filters, End Date, Hour of Day
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                # Add padding above the reset button
                st.markdown("""
                <style>
                div[data-testid="column"]:nth-of-type(4) {
                    padding-top: 25px;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Reset filters button
                if st.button("Reset Filters", key="reset_filters_transactions"):
                    st.session_state["start_date"] = max_date
                    st.session_state["end_date"] = max_date
                    st.session_state["selected_hour"] = "11:59 PM"
                    st.session_state["selected_campus"] = ["All"]
                    st.session_state["selected_device_type_exclusion"] = ["None"]
                    st.session_state["pills_key"] += 1
                    st.rerun()
            
            with col6:
                end_date = st.date_input("End Date:", value=st.session_state["end_date"], min_value=min_date, max_value=max_date)
            
            with col7:
                hours = [f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)] + ["11:59 PM"]
                selected_hour = st.select_slider("Hour Range:", options=hours, value=st.session_state["selected_hour"])

            if device_type_exclusion == ['None']:
                device_type_exclusion = None

            # Ensure the user can pick the same date
            if start_date > end_date:
                st.warning("End date cannot be before start date. Please adjust.")
                st.stop()

            # Convert hour properly (including 11:59 PM handling)
            if selected_hour == "11:59 PM":
                hour_value = 23.99  # Slightly below midnight
            else:
                hour_value = int(selected_hour.split(' ')[0]) % 12 + (12 if 'PM' in selected_hour else 0)

            # Store updates in session state
            st.session_state["start_date"] = start_date
            st.session_state["end_date"] = end_date
            st.session_state["selected_hour"] = selected_hour
            st.session_state["selected_campus"] = selected_campus

        # Apply filters for metrics
        filtered_df_for_metrics = merged_df.copy()
        
        # Apply campus filter
        if "All" not in selected_campus:
            filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['CAMPUS'].isin(selected_campus)]
        
        # Apply date filters
        filtered_df_for_metrics = filtered_df_for_metrics[
            (filtered_df_for_metrics['DATE'] >= start_date) & 
            (filtered_df_for_metrics['DATE'] <= end_date)
        ]
        
        # Apply hour filter
        filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['HOUR'] <= hour_value]
        
        # Apply device type exclusion filter
        if device_type_exclusion is not None:
            filtered_df_for_metrics = filtered_df_for_metrics[~filtered_df_for_metrics['DEVICE_TYPE'].isin(device_type_exclusion)]

        # Calculate transaction counts for metrics
        tx_counts = {
            "Magstripe": 0,
            "Proximity": 0,
            "Biometric": 0,
            "MobileANDREMOTE": 0
        }
        
        if not filtered_df_for_metrics.empty:
            # Check if each column exists before accessing it
            if 'MAGSTRIPE' in filtered_df_for_metrics.columns:
                tx_counts["Magstripe"] = int(filtered_df_for_metrics['MAGSTRIPE'].sum())
            if 'PROXIMITY' in filtered_df_for_metrics.columns:
                tx_counts["Proximity"] = int(filtered_df_for_metrics['PROXIMITY'].sum())
            if 'BIOMETRIC' in filtered_df_for_metrics.columns:
                tx_counts["Biometric"] = int(filtered_df_for_metrics['BIOMETRIC'].sum())
            if 'MOBILEANDREMOTE' in filtered_df_for_metrics.columns:
                tx_counts["MobileANDREMOTE"] = int(filtered_df_for_metrics['MOBILEANDREMOTE'].sum())

        # Display metrics in the metrics container (above filters)
        with metrics_container:
            st.subheader("Transaction Metrics:")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-box"><div class="metric-label">💳 Magstripe</div><div class="metric-value">{tx_counts["Magstripe"]:,}</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-box"><div class="metric-label">📳 Proximity</div><div class="metric-value">{tx_counts["Proximity"]:,}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-box"><div class="metric-label">🧬 Biometric</div><div class="metric-value">{tx_counts["Biometric"]:,}</div></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric-box"><div class="metric-label">📱 Mobile/Remote</div><div class="metric-value">{tx_counts["MobileANDREMOTE"]:,}</div></div>', unsafe_allow_html=True)

        # Process and display treemap
        cumulative_df = process_transaction_data(merged_df, start_date, end_date, selected_hour, selected_campus, device_type_exclusion)
        
        # Adjust CAMPUS column based on selection
        if 'All' in selected_campus:
            cumulative_df['CAMPUS'] = 'All Campuses'
        else:
            cumulative_df['CAMPUS'] = cumulative_df['CAMPUS']  # Keep original values

        # Display visualization and detailed data
        st.subheader("Visualization:")
        if not cumulative_df.empty:
            fig = px.treemap(
                cumulative_df,
                path=[px.Constant("Transactions"), 'CAMPUS', 'BUILDING_NAME'],
                values='TOTAL_TRANS',
                color='TOTAL_TRANS',
                hover_data=['BUILDING_NAME'],
                color_continuous_scale='Reds'
            )
            fig.update_traces(texttemplate="%{label}<br>%{value:,}", textposition="middle center")
            fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Detailed Data:")
            show_data = st.toggle(label="Hide/View", key="toggle_txn2_data", value=True)
            if show_data:
                display_txn_details(cumulative_df)
        else:
            st.write("No data available for this selection.")


# def process_transaction_volume_per_opening(df):
#     # Session state initialization
#     campuses = df['CAMPUS'].dropna().unique().tolist()
#     campuses = [campus for campus in campuses if campus.lower() != "unknown"]

#     if "txn_selected_start_date" not in st.session_state:
#         st.session_state["txn_selected_start_date"] = pd.to_datetime(df['DATE'].min())
#     if "txn_selected_end_date" not in st.session_state:
#         st.session_state["txn_selected_end_date"] = pd.to_datetime(df['DATE'].max())
#     if "txn_selected_campus" not in st.session_state:
#         st.session_state["txn_selected_campus"] = "CG"
#     if "txn_key_" not in st.session_state:
#         st.session_state["txn_key_"] = 0
#     # Add session state for device type exclusion
#     if "txn_selected_device_type_exclusion" not in st.session_state:
#         st.session_state["txn_selected_device_type_exclusion"] = ["None"]

#     if "txn_selected_location_description" not in st.session_state:
#         st.session_state["txn_selected_location_description"] = "All"
#     if "txn_selected_location_number" not in st.session_state:
#         st.session_state["txn_selected_location_number"] = "All"

#     # Generate dynamic labels for 12-hour format, including 11:59 PM
#     hour_labels = [f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}" for h in range(24)] + ["11:59 PM"]

#     def hour_to_24h(label):
#         if label == "11:59 PM":
#             return 23.99
#         num, meridian = label.split()
#         num = int(num)
#         if meridian == "AM" and num == 12:
#             return 0
#         elif meridian == "PM" and num != 12:
#             return num + 12
#         return num

#     with st.container():
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             selected_campus = st.pills("Select Campus:", campuses, selection_mode="single", default="CG", key=f"pills__{st.session_state['txn_key_']}")
#             selected_campus = selected_campus if isinstance(selected_campus, list) else [selected_campus]
#             st.session_state["txn_selected_campus"] = selected_campus
#             df = df[df['CAMPUS'].isin(selected_campus)]

#         with col2:
#             if pd.isna(st.session_state.get("txn_selected_start_date", None)):
#                 st.session_state["txn_selected_start_date"] = pd.to_datetime(df['DATE'].min())
#             selected_start_date = st.date_input("Start Date:", st.session_state["txn_selected_start_date"], key=f"start_date_key_{st.session_state['txn_key_']}")

#         with col3:
#             if pd.isna(st.session_state.get("txn_selected_end_date", None)):
#                 st.session_state["txn_selected_end_date"] = pd.to_datetime(df['DATE'].max())
#             selected_end_date = st.date_input("End Date:", st.session_state["txn_selected_end_date"], key=f"end_date_key_{st.session_state['txn_key_']}")

#     with st.container():
#         col1, col2, col3, col4 = st.columns(4)

#         with col1:
#             buildings = sorted(df['BUILDING_NAME'].unique())
#             selected_building = st.selectbox("Building Name:", buildings, index=0, key=f"building_key_{st.session_state['txn_key_']}")

#         building_filtered_df = df[df['BUILDING_NAME'] == selected_building]

#         description_to_number = dict(zip(building_filtered_df['LOCATION_DESCRIPTION'], building_filtered_df['LOCATION'].astype(str)))
#         number_to_description = dict(zip(building_filtered_df['LOCATION'].astype(str), building_filtered_df['LOCATION_DESCRIPTION']))

#         with col2:
#             location_descriptions = ["All"] + sorted(building_filtered_df['LOCATION_DESCRIPTION'].dropna().unique().tolist())
#             selected_location_description = st.selectbox(
#                 "Location Description:",
#                 location_descriptions,
#                 index=(location_descriptions.index(st.session_state["txn_selected_location_description"])
#                         if st.session_state["txn_selected_location_description"] in location_descriptions
#                         else 0),
#                 key=f"location_desc_key_{st.session_state['txn_key_']}"
#             )

#             if selected_location_description != st.session_state["txn_selected_location_description"]:
#                 st.session_state["txn_selected_location_description"] = selected_location_description
#                 if selected_location_description == "All":
#                     st.session_state["txn_selected_location_number"] = "All"
#                 else:
#                     st.session_state["txn_selected_location_number"] = description_to_number[selected_location_description]
#                 st.rerun()

#         with col3:
#             location_numbers = ["All"] + sorted(building_filtered_df['LOCATION'].astype(str).dropna().unique().tolist())
#             selected_location_number = st.selectbox(
#                 "Location Number:",
#                 location_numbers,
#                 index=(location_numbers.index(st.session_state["txn_selected_location_number"])
#                         if st.session_state["txn_selected_location_number"] in location_numbers
#                         else 0),
#                 key=f"location_num_key_{st.session_state['txn_key_']}"
#             )

#             if selected_location_number != st.session_state["txn_selected_location_number"]:
#                 st.session_state["txn_selected_location_number"] = selected_location_number
#                 if selected_location_number == "All":
#                     st.session_state["txn_selected_location_description"] = "All"
#                 else:
#                     st.session_state["txn_selected_location_description"] = number_to_description[selected_location_number]
#                 st.rerun()

#         with col4:
#             start_hour_label, end_hour_label = st.select_slider(
#                 "Hour of Day:",
#                 options=hour_labels,
#                 value=(hour_labels[0], hour_labels[-1]),
#                 key=f"slider_key_{st.session_state['txn_key_']}"
#             )

#     # Device Type Exclusion Filter
#     # Define the callback function for device type selection
#     def handle_device_exclusion_selection():
#         # Get the current selection from the widget
#         selected = st.session_state["txn_device_type_widget"]
        
#         # Handle selection logic
#         if "None" in selected:
#             # If "None" is among the selections
#             other_selections = [d for d in selected if d != "None"]
#             if other_selections:
#                 # If there are other selections besides "None", remove "None"
#                 st.session_state["txn_selected_device_type_exclusion"] = other_selections
#             else:
#                 # Only "None" is selected
#                 st.session_state["txn_selected_device_type_exclusion"] = ["None"]
#         elif not selected:
#             # If nothing is selected, default to "None"
#             st.session_state["txn_selected_device_type_exclusion"] = ["None"]
#         else:
#             # Normal case: specific devices selected (no "None")
#             st.session_state["txn_selected_device_type_exclusion"] = selected

#     # Filter device options based on selected building
#     device_options = sorted(df[df['BUILDING_NAME'] == selected_building]['DEVICE_TYPE'].unique().tolist())
#     # Ensure "None" is in the original options list
#     if "None" not in device_options:
#         device_options.append("None")
    
#     col1, col2 = st.columns([1, 4])
#     with col1:
#         # Determine which options to show based on current selection
#         current_selection = st.session_state["txn_selected_device_type_exclusion"]
        
#         # If specific options are selected, don't show "None" in the dropdown
#         if current_selection and current_selection != ["None"]:
#             display_options = [d for d in device_options if d != "None"]
#         else:
#             # When "None" or nothing is selected, show all options including "None"
#             display_options = device_options.copy()
#             if "None" not in display_options:  
#                 display_options.append("None")
        
#         # Use the current session state as the default
#         device_multiselect = st.multiselect(
#             "Device Type Exclusions:",
#             options=display_options,
#             default=current_selection,
#             key="txn_device_type_widget",
#             on_change=handle_device_exclusion_selection
#         )
        
#         # Update device_type_exclusion from session state for use in filtering
#         device_type_exclusion = st.session_state["txn_selected_device_type_exclusion"]
    
#     # Set device_exclusion to None if "None" is selected
#     if device_type_exclusion == ['None']:
#         device_type_exclusion = None

#     start_hour, end_hour = hour_to_24h(start_hour_label), hour_to_24h(end_hour_label)

#     filtered_df = df[df['BUILDING_NAME'] == selected_building]

#     if st.session_state["txn_selected_location_description"] != "All":
#         filtered_df = filtered_df[filtered_df['LOCATION_DESCRIPTION'] == st.session_state["txn_selected_location_description"]]

#     if st.session_state["txn_selected_location_number"] != "All":
#         filtered_df = filtered_df[filtered_df['LOCATION'] == int(st.session_state["txn_selected_location_number"])]

#     filtered_df = filtered_df[(filtered_df['DATE'] >= selected_start_date) & (filtered_df['DATE'] <= selected_end_date)]
#     filtered_df = filtered_df[filtered_df['HOUR'].between(start_hour, end_hour)]

#     # Apply device type exclusion filter if selected - matching process_transaction_data implementation
#     if device_type_exclusion is not None:
#         filtered_df = filtered_df[~filtered_df['DEVICE_TYPE'].isin(device_type_exclusion)]

#     reset = st.button("Reset Filters", key="reset_filters_button_opening")

#     if reset:
#         st.session_state["txn_selected_start_date"] = pd.to_datetime(df['DATE'].min())
#         st.session_state["txn_selected_end_date"] = pd.to_datetime(df['DATE'].max())
#         st.session_state["txn_selected_campus"] = "CG"
#         st.session_state["txn_selected_location_description"] = "All"
#         st.session_state["txn_selected_location_number"] = "All"
#         st.session_state["txn_selected_device_type_exclusion"] = ["None"]
#         st.session_state["txn_key_"] += 1
#         st.rerun()

#     return filtered_df


def process_transaction_volume_per_opening(df):
    # Session state initialization
    campuses_only = df['CAMPUS'].dropna().unique().tolist()
    campuses = ["All"] + [campus for campus in campuses_only if campus.lower() != "unknown"]

    min_date = pd.to_datetime(df['DATE'].min())
    max_date = pd.to_datetime(df['DATE'].max())

    # Use max_date (last available date) as default for both start and end dates
    if "txn_selected_start_date" not in st.session_state or not (min_date <= pd.Timestamp(st.session_state["txn_selected_start_date"]) <= max_date):
        st.session_state["txn_selected_start_date"] = max_date

    if "txn_selected_end_date" not in st.session_state or not (min_date <= pd.Timestamp(st.session_state["txn_selected_end_date"]) <= max_date):
        st.session_state["txn_selected_end_date"] = max_date

    if "txn_selected_campus" not in st.session_state:
        st.session_state["txn_selected_campus"] = "All"
    if "txn_key_" not in st.session_state:
        st.session_state["txn_key_"] = 0
    # Add session state for device type exclusion
    if "txn_selected_device_type_exclusion" not in st.session_state:
        st.session_state["txn_selected_device_type_exclusion"] = ["None"]

    if "txn_selected_building" not in st.session_state:
        st.session_state["txn_selected_building"] = "All"

    # Generate dynamic labels for 12-hour format, including 11:59 PM
    hour_labels = [f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}" for h in range(24)] + ["11:59 PM"]

    def hour_to_24h(label):
        if label == "11:59 PM":
            return 23.99
        num, meridian = label.split()
        num = int(num)
        if meridian == "AM" and num == 12:
            return 0
        elif meridian == "PM" and num != 12:
            return num + 12
        return num

    # Pre-filter by campus for building selection
    if st.session_state["txn_selected_campus"] == "All":
        campus_filtered_df = df.copy()  # Use all data if "All" is selected
    else:
        campus_filtered_df = df[df['CAMPUS'].isin([st.session_state["txn_selected_campus"]])]

    # Define the callback function for device type selection
    def handle_device_exclusion_selection():
        # Get the current selection from the widget
        selected = st.session_state["txn_device_type_widget"]
        
        # Handle selection logic
        if "None" in selected:
            # If "None" is among the selections
            other_selections = [d for d in selected if d != "None"]
            if other_selections:
                # If there are other selections besides "None", remove "None"
                st.session_state["txn_selected_device_type_exclusion"] = other_selections
            else:
                # Only "None" is selected
                st.session_state["txn_selected_device_type_exclusion"] = ["None"]
        elif not selected:
            # If nothing is selected, default to "None"
            st.session_state["txn_selected_device_type_exclusion"] = ["None"]
        else:
            # Normal case: specific devices selected (no "None")
            st.session_state["txn_selected_device_type_exclusion"] = selected

    st.write("")
    st.subheader("Filter Options:")
    st.write("")
    # FIRST ROW: Select Campus, Start Date, Device Type Exclusions
    with st.container():
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_campus = st.pills("Select Campus:", campuses, selection_mode="single", default=st.session_state["txn_selected_campus"], key=f"pills__{st.session_state['txn_key_']}")
            selected_campus = selected_campus if isinstance(selected_campus, list) else [selected_campus]
            
            # Update session state and handle campus change
            if st.session_state["txn_selected_campus"] != selected_campus[0]:
                st.session_state["txn_selected_campus"] = selected_campus[0]
                st.rerun()

        with col2:
            selected_start_date = st.date_input(
                "Start Date:",
                value=st.session_state["txn_selected_start_date"],
                min_value=min_date,
                max_value=max_date,
                key=f"start_date_key_{st.session_state['txn_key_']}"
            )
            
            # Update session state when date changes
            if selected_start_date != st.session_state["txn_selected_start_date"]:
                st.session_state["txn_selected_start_date"] = selected_start_date


        with col3:
            # Filter device options based on selected campus and building
            if st.session_state["txn_selected_campus"] == "All":
                device_df = df.copy()
            else:
                device_df = df[df['CAMPUS'].isin([st.session_state["txn_selected_campus"]])]
                
            if st.session_state["txn_selected_building"] != "All":
                device_df = device_df[device_df['BUILDING_NAME'] == st.session_state["txn_selected_building"]]
                
            device_options = sorted(device_df['DEVICE_TYPE'].unique().tolist())
            # Ensure "None" is in the original options list
            if "None" not in device_options:
                device_options.append("None")
            
            # Determine which options to show based on current selection
            current_selection = st.session_state["txn_selected_device_type_exclusion"]
            
            # If specific options are selected, don't show "None" in the dropdown
            if current_selection and current_selection != ["None"]:
                display_options = [d for d in device_options if d != "None"]
            else:
                # When "None" or nothing is selected, show all options including "None"
                display_options = device_options.copy()
                if "None" not in display_options:  
                    display_options.append("None")
            
            # Use the current session state as the default
            device_multiselect = st.multiselect(
                "Device Type Exclusions:",
                options=display_options,
                default=current_selection,
                key="txn_device_type_widget",
                on_change=handle_device_exclusion_selection
            )

    # SECOND ROW: Building Name, End Date, Hour of Day
    with st.container():
        col1, col2, col3 = st.columns(3)

        with col1:
            # Add "All" to buildings list
            buildings = ["All"] + sorted(campus_filtered_df['BUILDING_NAME'].unique())
            
            if st.session_state["txn_selected_building"] not in buildings:
                st.session_state["txn_selected_building"] = "All"
                
            selected_building = st.selectbox(
                "Building Name:", 
                buildings, 
                index=buildings.index(st.session_state["txn_selected_building"]),
                key=f"building_key_{st.session_state['txn_key_']}"
            )
            
            # Handle building change
            if selected_building != st.session_state["txn_selected_building"]:
                st.session_state["txn_selected_building"] = selected_building
                st.rerun()

        with col2:
            selected_end_date = st.date_input(
                "End Date:",
                value=st.session_state["txn_selected_end_date"],
                min_value=min_date,
                max_value=max_date,
                key=f"end_date_key_{st.session_state['txn_key_']}"
            )
            
            # Update session state when date changes
            if selected_end_date != st.session_state["txn_selected_end_date"]:
                st.session_state["txn_selected_end_date"] = selected_end_date

        with col3:
            start_hour_label, end_hour_label = st.select_slider(
                "Hour Range:",
                options=hour_labels,
                value=(hour_labels[0], hour_labels[-1]),
                key=f"slider_key_{st.session_state['txn_key_']}"
            )

    # THIRD ROW: Reset Filters
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            # Add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(1) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            reset = st.button("Reset Filters", key="reset_filters_button_opening")
    st.write("")
    # Handle reset functionality
    if reset:
        st.session_state["txn_selected_start_date"] = max_date  # Keep as max_date for last available
        st.session_state["txn_selected_end_date"] = max_date    # Keep as max_date for last available
        st.session_state["txn_selected_campus"] = "All"
        st.session_state["txn_selected_building"] = "All"  # Reset to "All"
        st.session_state["txn_selected_device_type_exclusion"] = ["None"]
        st.session_state["txn_key_"] += 1
        st.rerun()

    # Apply all filters in the correct order
    start_hour, end_hour = hour_to_24h(start_hour_label), hour_to_24h(end_hour_label)

    # Get device_type_exclusion from session state for use in filtering
    device_type_exclusion = st.session_state["txn_selected_device_type_exclusion"]
    
    # Set device_exclusion to None if "None" is selected
    if device_type_exclusion == ['None']:
        device_type_exclusion = None

    # Apply filters step by step
    if st.session_state["txn_selected_campus"] == "All":
        filtered_df = df.copy()  # Use all data if "All" is selected
    else:
        filtered_df = df[df['CAMPUS'].isin([st.session_state["txn_selected_campus"]])]
    
    # Apply building filter if not "All"    
    if st.session_state["txn_selected_building"] != "All":
        filtered_df = filtered_df[filtered_df['BUILDING_NAME'] == selected_building]

    # Use the updated date values from session state for filtering
    filtered_df = filtered_df[(filtered_df['DATE'] >= st.session_state["txn_selected_start_date"]) & 
                             (filtered_df['DATE'] <= st.session_state["txn_selected_end_date"])]
    filtered_df = filtered_df[filtered_df['HOUR'].between(start_hour, end_hour)]

    # Apply device type exclusion filter if selected
    if device_type_exclusion is not None:
        filtered_df = filtered_df[~filtered_df['DEVICE_TYPE'].isin(device_type_exclusion)]

    return filtered_df


def plot_transaction_volume_per_opening(transactional_df):
    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    st.write("")  # Add spacing

    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Transaction Volume per Building")
    test.write("This stacked bar chart displays hourly transaction totals at the building level...")

    show_map = st.toggle(label="Hide/View", key="toggle_map_display_opening", value=True)

    device_data = fetch_data()

    if show_map:
        # Create an empty container at the top for metrics
        metrics_placeholder = st.empty()
        if transactional_df.empty or device_data.empty:
            st.write("No data available for this selection.")
            return

        merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
        merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
        merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)
        merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")

        filtered_data = process_transaction_volume_per_opening(merged_df)

        # Metrics logic
        possible_types = {
            "MAGSTRIPE": {"icon": "💳", "label": "Magstripe"},
            "PROXIMITY": {"icon": "📳", "label": "Proximity"},
            "BIOMETRIC": {"icon": "🧬", "label": "Biometric"},
            "MOBILEANDREMOTE": {"icon": "📱", "label": "Mobile/Remote"}
        }

        transaction_types = []
        for col_name, details in possible_types.items():
            value = int(filtered_data[col_name].sum()) if col_name in filtered_data.columns else 0
            transaction_types.append({
                "column": col_name,
                "icon": details["icon"],
                "label": details["label"],
                "value": value
            })

        # Use the placeholder to update metrics at the top
        with metrics_placeholder.container():
            st.subheader("Transaction Metrics:")
            cols = st.columns(4)
            for i, metric in enumerate(transaction_types):
                with cols[i]:
                    st.markdown(
                        f'<div class="metric-box"><div class="metric-label">{metric["icon"]} {metric["label"]}</div><div class="metric-value">{metric["value"]:,}</div></div>',
                        unsafe_allow_html=True
                    )

        # Chart (same as before)
        if not filtered_data.empty:
            device_hourly_df = filtered_data.groupby(['HOUR', 'DEVICE_TYPE'], as_index=False)['TOTAL_TRANS'].sum()
            st.subheader("Visualization:")
            fig = px.bar(
                device_hourly_df,
                x='HOUR',
                y='TOTAL_TRANS',
                color='DEVICE_TYPE',
                barmode='stack',
                labels={'HOUR': 'Hour of Day', 'TOTAL_TRANS': 'Transaction Count', 'DEVICE_TYPE': 'Device Type'},
                title="Hourly Transaction Volume by Device Type"
            )
            fig.update_xaxes(
                tickmode='array',
                tickvals=list(range(24)),
                ticktext=[f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)]
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No data available for this selection.")



# def plot_transaction_volume_per_opening(transactional_df):
#     st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)

#     test = st.expander("Click to view or hide description", expanded=True)
#     test.title("Transaction Volume per Building")
#     test.write("This stacked bar chart displays hourly transaction totals at the building level, segmented by the device types reporting each transaction. It provides a detailed view of activity patterns throughout the day, helping identify peak usage times and device-specific trends.")

#     show_map = st.toggle(label="Hide/View", key="toggle_map_display_opening", value=True)

#     device_data = fetch_data()

#     if show_map:
#         if transactional_df.empty or device_data.empty:
#             st.write("No data available for this selection.")
#             return

#         merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
#         merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
#         merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)
#         merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")

#         # ✅ First, get the filtered data using all current filter settings
#         filtered_data = process_transaction_volume_per_opening(merged_df)

#         # CSS for metrics
#         st.markdown("""
#             <style>
#                 .metric-box {
#                     border: none;
#                     border-radius: 15px;
#                     padding: 20px;
#                     text-align: center;
#                     background-color: #1E3A8A;
#                     color: white;
#                     margin: 10px;
#                     box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
#                 }
#                 .metric-label {
#                     font-weight: bold;
#                     font-size: 22px;
#                     color: white;
#                 }
#                 .metric-value {
#                     font-size: 30px;
#                     font-weight: bold;
#                     color: white;
#                 }
#             </style>
#         """, unsafe_allow_html=True)

#         # ✅ METRICS SECTION - Now use the filtered data for metrics calculation
#         possible_types = {
#             "MAGSTRIPE": {"icon": "💳", "label": "Magstripe"},
#             "PROXIMITY": {"icon": "📳", "label": "Proximity"},
#             "BIOMETRIC": {"icon": "🧬", "label": "Biometric"},
#             "MOBILEANDREMOTE": {"icon": "📱", "label": "Mobile/Remote"}
#         }

#         transaction_types = []
#         for col_name, details in possible_types.items():
#             value = int(filtered_data[col_name].sum()) if col_name in filtered_data.columns else 0
#             transaction_types.append({
#                 "column": col_name,
#                 "icon": details["icon"],
#                 "label": details["label"],
#                 "value": value
#             })

#         st.subheader("Transaction Metrics:")

#         # Display metrics - these will now update based on filters
#         cols = st.columns(4)
#         for i, metric in enumerate(transaction_types):
#             with cols[i]:
#                 st.markdown(
#                     f'<div class="metric-box"><div class="metric-label">{metric["icon"]} {metric["label"]}</div><div class="metric-value">{metric["value"]:,}</div></div>', 
#                     unsafe_allow_html=True
#                 )

#         # ✅ Now create the visualization using the same filtered data
#         if not filtered_data.empty:
#             device_hourly_df = filtered_data.groupby(['HOUR', 'DEVICE_TYPE'], as_index=False)['TOTAL_TRANS'].sum()

#             st.subheader("Visualization:")
#             fig = px.bar(
#                 device_hourly_df,
#                 x='HOUR',
#                 y='TOTAL_TRANS',
#                 color='DEVICE_TYPE',
#                 barmode='stack',
#                 labels={'HOUR': 'Hour of Day', 'TOTAL_TRANS': 'Transaction Count', 'DEVICE_TYPE': 'Device Type'},
#                 title="Hourly Transaction Volume by Device Type"
#             )

#             fig.update_xaxes(
#                 tickmode='array',
#                 tickvals=list(range(24)),
#                 ticktext=[f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)]
#             )

#             st.plotly_chart(fig, use_container_width=True)
#         else:
#             st.write("No data available for this selection.")


# def plot_transaction_volume_per_opening(transactional_df):
#     st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)

#     test = st.expander("Click to view or hide description", expanded=True)
#     test.title("Transaction Volume per Building")
#     test.write("This stacked bar chart displays hourly transaction totals at the building level, segmented by the device types reporting each transaction. It provides a detailed view of activity patterns throughout the day, helping identify peak usage times and device-specific trends.")

#     show_map = st.toggle(label="Hide/View", key="toggle_map_display_opening", value=True)

#     device_data = fetch_data()

#     if show_map:
#         if transactional_df.empty or device_data.empty:
#             st.write("No data available for this selection.")
#             return

#         merged_df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
#         merged_df["CAMPUS"] = merged_df["CAMPUS_y"].combine_first(merged_df["CAMPUS_x"])
#         merged_df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)
#         merged_df["DEVICE_TYPE"] = merged_df["DEVICE_TYPE"].str.strip().fillna("Unknown")

#         # ✅ METRICS SECTION
#         selected_campus = st.session_state.get("txn_selected_campus", "All")
#         selected_building = st.session_state.get("txn_selected_building", "All")
#         selected_start_date = pd.to_datetime(st.session_state.get("txn_selected_start_date", merged_df['DATE'].min()))
#         selected_end_date = pd.to_datetime(st.session_state.get("txn_selected_end_date", merged_df['DATE'].max()))
#         device_type_exclusion = st.session_state.get("txn_selected_device_type_exclusion", ["None"])

#         filtered_df_for_metrics = merged_df.copy()

#         if selected_campus != "All":
#             filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['CAMPUS'] == selected_campus]
#         if selected_building != "All":
#             filtered_df_for_metrics = filtered_df_for_metrics[filtered_df_for_metrics['BUILDING_NAME'] == selected_building]

#         filtered_df_for_metrics['DATE'] = pd.to_datetime(filtered_df_for_metrics['DATE'])
#         filtered_df_for_metrics = filtered_df_for_metrics[
#             (filtered_df_for_metrics['DATE'] >= selected_start_date) &
#             (filtered_df_for_metrics['DATE'] <= selected_end_date)
#         ]
#         if device_type_exclusion != ["None"]:
#             filtered_df_for_metrics = filtered_df_for_metrics[~filtered_df_for_metrics['DEVICE_TYPE'].isin(device_type_exclusion)]

#         # CSS for metrics
#         st.markdown("""
#             <style>
#                 .metric-box {
#                     border: none;
#                     border-radius: 15px;
#                     padding: 20px;
#                     text-align: center;
#                     background-color: #1E3A8A;
#                     color: white;
#                     margin: 10px;
#                     box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
#                 }
#                 .metric-label {
#                     font-weight: bold;
#                     font-size: 22px;
#                     color: white;
#                 }
#                 .metric-value {
#                     font-size: 30px;
#                     font-weight: bold;
#                     color: white;
#                 }
#             </style>
#         """, unsafe_allow_html=True)

#         # Build metric values
#         possible_types = {
#             "MAGSTRIPE": {"icon": "💳", "label": "Magstripe"},
#             "PROXIMITY": {"icon": "📳", "label": "Proximity"},
#             "BIOMETRIC": {"icon": "🧬", "label": "Biometric"},
#             "MOBILEANDREMOTE": {"icon": "📱", "label": "Mobile/Remote"}
#         }

#         transaction_types = []
#         for col_name, details in possible_types.items():
#             value = int(filtered_df_for_metrics[col_name].sum()) if col_name in filtered_df_for_metrics.columns else 0
#             transaction_types.append({
#                 "column": col_name,
#                 "icon": details["icon"],
#                 "label": details["label"],
#                 "value": value
#             })

#         st.subheader("Transaction Metrics:")

#         # Display metrics above filters
#         cols = st.columns(4)
#         for i, metric in enumerate(transaction_types):
#             with cols[i]:
#                 st.markdown(
#                     f'<div class="metric-box"><div class="metric-label">{metric["icon"]} {metric["label"]}</div><div class="metric-value">{metric["value"]:,}</div></div>', 
#                     unsafe_allow_html=True
#                 )

#         # ✅ Now render the filters below
#         filtered_data = process_transaction_volume_per_opening(merged_df)

#         if not filtered_data.empty:
#             device_hourly_df = filtered_data.groupby(['HOUR', 'DEVICE_TYPE'], as_index=False)['TOTAL_TRANS'].sum()

#             st.subheader("Visualization:")
#             fig = px.bar(
#                 device_hourly_df,
#                 x='HOUR',
#                 y='TOTAL_TRANS',
#                 color='DEVICE_TYPE',
#                 barmode='stack',
#                 labels={'HOUR': 'Hour of Day', 'TOTAL_TRANS': 'Transaction Count', 'DEVICE_TYPE': 'Device Type'},
#                 title="Hourly Transaction Volume by Device Type"
#             )

#             fig.update_xaxes(
#                 tickmode='array',
#                 tickvals=list(range(24)),
#                 ticktext=[f"{i % 12 if i % 12 != 0 else 12} {'AM' if i < 12 else 'PM'}" for i in range(24)]
#             )

#             st.plotly_chart(fig, use_container_width=True)
#         else:
#             st.write("No data available for this selection.")



# @st.cache_data(ttl=3600)  # Cache for 1 hour
def _prepare_base_data(transactional_df_hash, device_data_hash):
    """Cached function to prepare base merged dataframe"""
    # Re-fetch data inside cached function
    device_data = fetch_data()
    transactional_df = st.session_state.get('cached_transactional_df')
    
    if transactional_df is None or transactional_df.empty or device_data.empty:
        return pd.DataFrame()
    
    df = pd.merge(transactional_df, device_data, on=['BUILDING_NAME', 'LOCATION_DESCRIPTION'], how='inner')
    df["CAMPUS"] = df["CAMPUS_y"].combine_first(df["CAMPUS_x"])
    df.drop(["CAMPUS_x", "CAMPUS_y"], axis=1, inplace=True)
    df["DEVICE_TYPE"] = df["DEVICE_TYPE"].str.strip().fillna("Unknown")
    return df

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def _calculate_aggregated_metrics(df_hash, campus, start_date, end_date, hour_start, hour_end, 
                                building, location_desc, location_num, device_exclusions, selected_types):
    """Cached function to calculate transaction metrics"""
    df = st.session_state.get('cached_base_df')
    if df is None or df.empty:
        return {"Magstripe": 0, "Proximity": 0, "Biometric": 0, "Mobile/Remote": 0}
    
    # Apply filters
    filtered_df = df.copy()
    
    if campus != "All":
        filtered_df = filtered_df[filtered_df['CAMPUS'] == campus]
    
    filtered_df = filtered_df[(filtered_df['DATE'] >= start_date) & (filtered_df['DATE'] <= end_date)]
    filtered_df = filtered_df[filtered_df['HOUR'].between(hour_start, hour_end)]
    
    if building != "All":
        filtered_df = filtered_df[filtered_df['BUILDING_NAME'] == building]
    
    if location_desc != "All":
        filtered_df = filtered_df[filtered_df['LOCATION_DESCRIPTION'] == location_desc]
    
    if location_num != "All":
        filtered_df = filtered_df[filtered_df['LOCATION'] == int(location_num)]
    
    if device_exclusions != ["None"]:
        filtered_df = filtered_df[~filtered_df['DEVICE_TYPE'].isin(device_exclusions)]
    
    # Calculate counts
    tx_counts = {"Magstripe": 0, "Proximity": 0, "Biometric": 0, "Mobile/Remote": 0}
    if not filtered_df.empty:
        for tx_type in selected_types:
            # Map display name to column name
            col_name = "MOBILEANDREMOTE" if tx_type == "Mobile/Remote" else tx_type.upper()
            if col_name in filtered_df.columns:
                tx_counts[tx_type] = int(filtered_df[col_name].sum())
    
    return tx_counts

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def _prepare_chart_data(df_hash, campus, start_date, end_date, hour_start, hour_end,
                       building, location_desc, location_num, device_exclusions, selected_types):
    """Cached function to prepare chart data"""
    df = st.session_state.get('cached_base_df')
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Apply filters
    filtered_df = df.copy()
    
    if campus != "All":
        filtered_df = filtered_df[filtered_df['CAMPUS'] == campus]
        
    filtered_df = filtered_df[(filtered_df['DATE'] >= start_date) & (filtered_df['DATE'] <= end_date)]
    filtered_df = filtered_df[filtered_df['HOUR'].between(hour_start, hour_end)]
    
    if building != "All":
        filtered_df = filtered_df[filtered_df['BUILDING_NAME'] == building]
    
    if location_desc != "All":
        filtered_df = filtered_df[filtered_df['LOCATION_DESCRIPTION'] == location_desc]
    
    if location_num != "All":
        filtered_df = filtered_df[filtered_df['LOCATION'] == int(location_num)]
    
    if device_exclusions != ["None"]:
        filtered_df = filtered_df[~filtered_df['DEVICE_TYPE'].isin(device_exclusions)]

    if filtered_df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Prepare chart data
    filtered_df['LOCATION_LABEL'] = filtered_df['BUILDING_NAME'] + ' - ' + filtered_df['LOCATION_DESCRIPTION']
    
    # Map display names to column names
    agg_cols = []
    for tx_type in selected_types:
        col_name = "MOBILEANDREMOTE" if tx_type == "Mobile/Remote" else tx_type.upper()
        agg_cols.append(col_name)
    
    # Group and sort ALL locations (no limit)
    grouped = filtered_df.groupby('LOCATION_LABEL')[agg_cols].sum().reset_index()
    # Calculate total transactions per location for sorting
    grouped['Total'] = grouped[agg_cols].sum(axis=1)
    sorted_grouped = grouped.sort_values(by='Total', ascending=False).drop('Total', axis=1)
    
    # Melt the data and map column names back to display names
    melted = sorted_grouped.melt(id_vars='LOCATION_LABEL', var_name='Transaction Type', value_name='Count')
    # Map column names back to display names
    melted['Transaction Type'] = melted['Transaction Type'].map({
        'MAGSTRIPE': 'Magstripe',
        'PROXIMITY': 'Proximity', 
        'BIOMETRIC': 'Biometric',
        'MOBILEANDREMOTE': 'Mobile/Remote'
    })
    
    # Prepare summary data for detailed view
    summary_df = filtered_df.groupby(['BUILDING_NAME', 'LOCATION_DESCRIPTION', 'DATE']).agg({
        col: 'sum' for col in agg_cols
    }).reset_index()
    
    # Rename columns in summary_df for display
    column_mapping = {
        'MAGSTRIPE': 'Magstripe',
        'PROXIMITY': 'Proximity',
        'BIOMETRIC': 'Biometric', 
        'MOBILEANDREMOTE': 'Mobile/Remote'
    }
    summary_df = summary_df.rename(columns=column_mapping)
    
    return melted, summary_df



def plot_transaction_volume_rankings(transactional_df):
    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    st.write("")  # Add spacing

    expander = st.expander("Click to view or hide description", expanded=True)
    expander.title("Transaction Volume per Location")
    expander.write("This stacked bar chart presents the transaction volume across all card readers, offering insights into activity patterns, peak usage times, and device-specific trends. It helps identify high-traffic areas for maintenance prioritization. Users can filter data by campus, date range, hour, building name, location description, location number, and transaction type. Hourly totals are aggregated and displayed at the close of each hour.")

    show_chart = st.toggle(label="Hide/View", key="toggle_map_display_rankings", value=True)
    if not show_chart:
        return

    # Cache the input dataframes in session state to avoid repeated processing
    if 'cached_transactional_df' not in st.session_state or st.session_state.get('transactional_df_hash') != hash(str(transactional_df.values.tobytes())):
        st.session_state['cached_transactional_df'] = transactional_df.copy()
        st.session_state['transactional_df_hash'] = hash(str(transactional_df.values.tobytes()))

    device_data = fetch_data()
    if transactional_df.empty or device_data.empty:
        st.warning("No data available for this selection.")
        return

    # Use cached data preparation
    transactional_hash = st.session_state.get('transactional_df_hash', 0)
    device_hash = hash(str(device_data.values.tobytes())) if not device_data.empty else 0
    
    df = _prepare_base_data(transactional_hash, device_hash)
    if df.empty:
        st.warning("No data available for this selection.")
        return
    
    # Cache the base dataframe
    st.session_state['cached_base_df'] = df
    df_hash = hash(str(df.values.tobytes()))

    # campuses = sorted([c for c in df['CAMPUS'].dropna().unique() if c.lower() != "unknown"])
    # # Add 'All' option for campus selection
    # campus_options = ["All"] + campuses

    campuses_only = df['CAMPUS'].dropna().unique().tolist()
    campus_options = ["All"] + [campus for campus in campuses_only if campus.lower() != "unknown"]
    
    # MODIFIED: Get min and max dates, but default to latest date only
    min_date, max_date = df['DATE'].min(), df['DATE'].max()
    latest_date = max_date  # Use the most recent date as default for both start and end
    
    hour_labels = [f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}" for h in range(24)] + ["11:59 PM"]

    def hour_to_24h(label):
        if label == "11:59 PM":
            return 23.99
        num, meridian = label.split()
        num = int(num)
        return num + 12 if meridian == "PM" and num != 12 else (0 if num == 12 and meridian == "AM" else num)

    # Initialize session state variables
    if "rankings_key" not in st.session_state:
        st.session_state["rankings_key"] = 0
    if "rankings_filters" not in st.session_state:
        # MODIFIED: Default to latest date for both start and end dates
        initial_campus = "All"
        initial_building = "All"
        
        st.session_state["rankings_filters"] = {
            "campus": initial_campus,
            "start_date": latest_date,  # Changed from min_date to latest_date
            "end_date": latest_date,    # Changed from max_date to latest_date
            "hour_range": (hour_labels[0], hour_labels[-1]),
            "txn_types": ["Magstripe", "Proximity", "Biometric", "Mobile/Remote"],
            "building": initial_building,
            "location_number": "All",
            "location_description": "All",
            "device_type_exclusion": ["None"]
        }
    
    # Ensure all required keys exist (for backward compatibility)
    required_keys = {
        "building": "All",  
        "location_number": "All", 
        "location_description": "All",
        "device_type_exclusion": ["None"]
    }
    for key, default_value in required_keys.items():
        if key not in st.session_state["rankings_filters"]:
            st.session_state["rankings_filters"][key] = default_value

    k = st.session_state["rankings_key"]

    # Pre-filter by campus for building selection
    if st.session_state["rankings_filters"]["campus"] == "All":
        campus_filtered_df = df  # Use all data when "All" campuses are selected
    else:
        campus_filtered_df = df[df['CAMPUS'].isin([st.session_state["rankings_filters"]["campus"]])]

    # Define the callback function for device type exclusion selection
    def handle_device_exclusion_selection():
        # Get the current selection from the widget
        selected = st.session_state["rankings_device_type_widget"]
        
        # Handle selection logic
        if "None" in selected:
            # If "None" is among the selections
            other_selections = [d for d in selected if d != "None"]
            if other_selections:
                # If there are other selections besides "None", remove "None"
                st.session_state["rankings_filters"]["device_type_exclusion"] = other_selections
            else:
                # Only "None" is selected
                st.session_state["rankings_filters"]["device_type_exclusion"] = ["None"]
        elif not selected:
            # If nothing is selected, default to "None"
            st.session_state["rankings_filters"]["device_type_exclusion"] = ["None"]
        else:
            # Normal case: specific devices selected (no "None")
            st.session_state["rankings_filters"]["device_type_exclusion"] = selected

    # Get the current building-filtered data based on selected building
    if st.session_state["rankings_filters"]["building"] == "All":
        building_filtered_df = campus_filtered_df  # Use all buildings when "All" is selected
    else:
        building_filtered_df = campus_filtered_df[campus_filtered_df['BUILDING_NAME'] == st.session_state["rankings_filters"]["building"]]
    
    # Apply custom CSS styles for metrics
    st.markdown("""
        <style>
            .metric-box {
                border: 3px solid #4B0082;  /* Purple border only */
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                background-color: transparent;  /* No fill, transparent background */
                color: white;  /* White text for dark theme */
                margin: 10px;
                box-shadow: 4px 4px 10px rgba(0,0,0,0.1); /* Soft shadow */
            }
            .metric-label {
                font-weight: bold;
                font-size: 22px;  /* Increased label font size */
                color: white;
            }
            .metric-value {
                font-size: 30px;  /* Increased value font size */
                font-weight: bold;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # # MOVED: Transaction Type Checkboxes to be above all filters
    # types = ["Magstripe", "Proximity", "Biometric", "Mobile/Remote"]
    # # type_icons = {"Magstripe": "💳", "Proximity": "📳", "Biometric": "🧬", "Mobile/Remote": "📱"}
    # selected_types = []
    # cols = st.columns([3,3,3,3])
    # for i, t in enumerate(types):
    #     with cols[i]:
    #         checked = t in st.session_state["rankings_filters"]["txn_types"]
    #         if st.checkbox(f"{t}", value=checked, key=f"rankings_type_{t}_{k}"):
    #             selected_types.append(t)
    

    st.subheader("Transaction Metrics:")
    # MOVED: Transaction Type Checkboxes to be above all filters
    types = ["Magstripe", "Proximity", "Biometric", "Mobile/Remote"]
    # type_icons = {"Magstripe": "💳", "Proximity": "📳", "Biometric": "🧬", "Mobile/Remote": "📱"}
    selected_types = []

    # Create 4 columns for checkboxes
    cols = st.columns(4)

    for i, t in enumerate(types):
        with cols[i]:
            checked = t in st.session_state["rankings_filters"]["txn_types"]
            if st.checkbox(f"{t}", value=checked, key=f"rankings_type_{t}_{k}"):
                selected_types.append(t)
    # Use cached metrics calculation
    tx_counts = _calculate_aggregated_metrics(
        df_hash, st.session_state["rankings_filters"]["campus"],
        st.session_state["rankings_filters"]["start_date"], 
        st.session_state["rankings_filters"]["end_date"],
        hour_to_24h(st.session_state["rankings_filters"]["hour_range"][0]), 
        hour_to_24h(st.session_state["rankings_filters"]["hour_range"][1]),
        st.session_state["rankings_filters"]["building"],
        st.session_state["rankings_filters"]["location_description"],
        st.session_state["rankings_filters"]["location_number"],
        tuple(st.session_state["rankings_filters"]["device_type_exclusion"]),  # Convert to tuple for hashing
        tuple(selected_types)  # Convert to tuple for hashing
    )
    
    # Display metrics based on calculated values (zero for unselected types)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-label">💳 Magstripe</div><div class="metric-value">{tx_counts["Magstripe"]:,}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-label">📳 Proximity</div><div class="metric-value">{tx_counts["Proximity"]:,}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-label">🧬 Biometric</div><div class="metric-value">{tx_counts["Biometric"]:,}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="metric-label">📱 Mobile/Remote</div><div class="metric-value">{tx_counts["Mobile/Remote"]:,}</div></div>', unsafe_allow_html=True)

    st.write("")
    # NOW START FILTERS SECTION
    st.subheader("Filter Options:")
    st.write("")

    # ROW 1: Campus, Start Date, Location Number, Device Type Exclusions
    col1, col2, col3, col4 = st.columns(4)
    
    with st.container():
        with col1:
            selected_campus = st.pills("Select Campus:", campus_options, default=[st.session_state["rankings_filters"]["campus"]],
                                    key=f"rankings_campus_{k}", selection_mode="single")
            selected_campus = selected_campus[0] if isinstance(selected_campus, list) else selected_campus
            
            # Update session state and handle campus change
            if st.session_state["rankings_filters"]["campus"] != selected_campus:
                st.session_state["rankings_filters"]["campus"] = selected_campus
                # Reset building and location when campus changes
                st.session_state["rankings_filters"]["building"] = "All"  # Reset to "All"
                st.session_state["rankings_filters"]["location_description"] = "All"
                st.session_state["rankings_filters"]["location_number"] = "All"
                st.session_state["rankings_key"] += 1
                st.rerun()
        
        with col2:
            start_date = st.date_input("Start Date:", value=st.session_state["rankings_filters"]["start_date"],
                                    min_value=min_date, max_value=max_date, key=f"rankings_start_date_{k}")
        
        with col3:
            location_numbers = ["All"] + sorted(building_filtered_df['LOCATION'].astype(str).dropna().unique().tolist())
            selected_location_number = st.selectbox(
                "Location Number:",
                location_numbers,
                index=(location_numbers.index(st.session_state["rankings_filters"]["location_number"])
                        if st.session_state["rankings_filters"]["location_number"] in location_numbers
                        else 0),
                key=f"rankings_location_num_{k}"
            )
            
            # Handle location number change
            if selected_location_number != st.session_state["rankings_filters"]["location_number"]:
                st.session_state["rankings_filters"]["location_number"] = selected_location_number
                if selected_location_number == "All":
                    st.session_state["rankings_filters"]["location_description"] = "All"
                else:
                    # Update corresponding description
                    number_to_description = dict(zip(building_filtered_df['LOCATION'].astype(str), building_filtered_df['LOCATION_DESCRIPTION']))
                    st.session_state["rankings_filters"]["location_description"] = number_to_description.get(selected_location_number, "All")
                st.session_state["rankings_key"] += 1
                st.rerun()
        
        with col4:
            # Filter device options based on selected building
            device_options = sorted(building_filtered_df['DEVICE_TYPE'].unique().tolist())
            # Ensure "None" is in the original options list
            if "None" not in device_options:
                device_options.append("None")
            
            # Determine which options to show based on current selection
            current_selection = st.session_state["rankings_filters"]["device_type_exclusion"]
            
            # If specific options are selected, don't show "None" in the dropdown
            if current_selection and current_selection != ["None"]:
                display_options = [d for d in device_options if d != "None"]
            else:
                # When "None" or nothing is selected, show all options including "None"
                display_options = device_options.copy()
                if "None" not in display_options:  
                    display_options.append("None")
            
            # Use the current session state as the default
            device_multiselect = st.multiselect(
                "Device Type Exclusions:",
                options=display_options,
                default=current_selection,
                key="rankings_device_type_widget",
                on_change=handle_device_exclusion_selection
            )

        # ROW 2: Building Name, End Date, Location Description, Hour Range
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Add "All" option to buildings
            buildings = ["All"] + sorted(campus_filtered_df['BUILDING_NAME'].unique())
            selected_building_index = buildings.index(st.session_state["rankings_filters"]["building"]) if st.session_state["rankings_filters"]["building"] in buildings else 0
            selected_building = st.selectbox("Building Name:", buildings, index=selected_building_index, key=f"rankings_building_{k}")

            # Handle building change
            if selected_building != st.session_state["rankings_filters"]["building"]:
                st.session_state["rankings_filters"]["building"] = selected_building
                # Reset location when building changes
                st.session_state["rankings_filters"]["location_description"] = "All"
                st.session_state["rankings_filters"]["location_number"] = "All"
                st.session_state["rankings_key"] += 1
                st.rerun()
        
        with col2:
            end_date = st.date_input("End Date:", value=st.session_state["rankings_filters"]["end_date"],
                                min_value=min_date, max_value=max_date, key=f"rankings_end_date_{k}")
        
        # Update building_filtered_df for location description based on current building selection
        if selected_building == "All":
            building_for_locations_df = campus_filtered_df
        else:
            building_for_locations_df = campus_filtered_df[campus_filtered_df['BUILDING_NAME'] == selected_building]
        
        description_to_number = dict(zip(building_for_locations_df['LOCATION_DESCRIPTION'], building_for_locations_df['LOCATION'].astype(str)))
        
        with col3:
            location_descriptions = ["All"] + sorted(building_for_locations_df['LOCATION_DESCRIPTION'].dropna().unique().tolist())
            selected_location_description = st.selectbox(
                "Location Description:",
                location_descriptions,
                index=(location_descriptions.index(st.session_state["rankings_filters"]["location_description"])
                        if st.session_state["rankings_filters"]["location_description"] in location_descriptions
                        else 0),
                key=f"rankings_location_desc_{k}"
            )
            
            # Handle location description change
            if selected_location_description != st.session_state["rankings_filters"]["location_description"]:
                st.session_state["rankings_filters"]["location_description"] = selected_location_description
                if selected_location_description == "All":
                    st.session_state["rankings_filters"]["location_number"] = "All"
                else:
                    st.session_state["rankings_filters"]["location_number"] = description_to_number.get(selected_location_description, "All")
                st.session_state["rankings_key"] += 1
                st.rerun()
        
        with col4:
            start_hour_label, end_hour_label = st.select_slider("Hour Range:", options=hour_labels,
                                                            value=st.session_state["rankings_filters"]["hour_range"],
                                                            key=f"rankings_hour_range_{k}")

        # ROW 3: Reset Button
        col1, col2 = st.columns([1, 3])
        with col1:
            # Add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(1) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            if st.button("Reset Filters", key=f"rankings_reset_button_{k}"):
                # MODIFIED: Reset to latest date instead of full date range
                st.session_state["rankings_filters"] = {
                    "campus": "All",  
                    "start_date": latest_date,  # Changed from min_date to latest_date
                    "end_date": latest_date,    # Changed from max_date to latest_date
                    "hour_range": (hour_labels[0], hour_labels[-1]),
                    "txn_types": ["Magstripe", "Proximity", "Biometric", "Mobile/Remote"],
                    "building": "All",  
                    "location_number": "All",
                    "location_description": "All",
                    "device_type_exclusion": ["None"]
                }
                st.session_state["rankings_key"] += 1
                st.rerun()

    st.write("")

    # Save updated selections
    st.session_state["rankings_filters"].update({
        "campus": selected_campus,
        "start_date": start_date,
        "end_date": end_date,
        "hour_range": (start_hour_label, end_hour_label),
        "txn_types": selected_types,
        "building": selected_building
    })

    # Show warning if no transaction types are selected
    if not selected_types:
        st.warning("Please select at least one transaction type.")
        return

    # FIXED: Use cached chart data preparation with correct variable name
    melted, summary_df = _prepare_chart_data(
        df_hash, selected_campus, start_date, end_date,
        hour_to_24h(start_hour_label), hour_to_24h(end_hour_label),
        selected_building, st.session_state["rankings_filters"]["location_description"],
        st.session_state["rankings_filters"]["location_number"],
        tuple(st.session_state["rankings_filters"]["device_type_exclusion"]), tuple(selected_types)
    )

    if melted.empty:
        st.warning("No data available for this selection.")
        return

    # Create and display vertical stacked bar chart with scroll and mid-range visible
    num_locations = len(melted['LOCATION_LABEL'].unique())
    unique_locations = melted['LOCATION_LABEL'].unique().tolist()

    # Calculate middle half index range
    start_idx = max(0, num_locations // 4)
    end_idx = min(num_locations, start_idx + (num_locations // 2))

    # Get actual location labels for mid-range
    initial_range = [unique_locations[start_idx], unique_locations[end_idx - 1]]

    visible_range = unique_locations[:30]
    # Chart configuration
    fig = px.bar(
        melted,
        x='LOCATION_LABEL',
        y='Count',
        color='Transaction Type',
        orientation='v',
        title=f"Transaction Volume Rankings by Location ({num_locations} Locations)",
        labels={'LOCATION_LABEL': 'Location', 'Count': 'Transactions'},
        height=800
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=20, r=20, t=60, b=160),
        xaxis=dict(
            tickangle=45,
            automargin=True,
            fixedrange=False,
            categoryorder='array',
            categoryarray=unique_locations,
            rangeslider=dict(visible=True),
            range=[0,31],  # index range like the template
            type='category'
        ),
        yaxis=dict(
            fixedrange=False
        ),
        height=800,
        autosize=True  # Enable autosize for responsive behavior
    )

    st.subheader("Visualization:")

    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d']
    })

    st.subheader("Detailed Data:")
    if st.toggle(label="Hide/View", key="toggle_txn4_data", value=True):
        if not summary_df.empty:
            # Add TOTAL_TRANS as sum of selected type columns (if available)
            trans_cols = ['Magstripe', 'Proximity', 'Biometric', 'Mobile/Remote']
            existing_cols = [col for col in trans_cols if col in summary_df.columns]
            summary_df['TOTAL_TRANS'] = summary_df[existing_cols].sum(axis=1)
            st.dataframe(summary_df, use_container_width=True)
        else:
            st.warning("No detailed data available for this selection.")




# ------ TPS and NODE STATUS -------

# Function to filter TPS and Node status data

st.cache_data()
def filter_tps_node_statuses(df):
    # Keep relevant columns
    df = df.copy()

    # Standardize status values
    df["TPS_STATUS"] = df["TPS_STATUS"].str.upper().fillna("INACTIVE")
    df["NODE_STATUS"] = df["NODE_STATUS"].str.upper().fillna("OFFLINE")

    # Filter to only expected values
    df = df[df["TPS_STATUS"].isin(["ACTIVE", "INACTIVE"])]
    df = df[df["NODE_STATUS"].isin(["ONLINE", "OFFLINE"])]

    df = df[df["CAMPUS"].str.upper() != "UNKNOWN"]

    return df


def plot_tps_node_statuses(df):

    def create_chart(filtered_df, status_column):
        # Aggregate total devices per building while keeping device type for stacking colors
        status_counts = filtered_df.groupby(["BUILDING_NAME", "DEVICE_TYPE"]).size().reset_index(name="Device Count")
        
        # Sort DEVICE_TYPE alphabetically (ascending order)
        status_counts = status_counts.sort_values(by="DEVICE_TYPE", ascending=True)

        # Calculate the total count per building for annotations
        total_counts = status_counts.groupby("BUILDING_NAME")["Device Count"].sum().reset_index()

        fig = px.bar(
            status_counts, 
            x="BUILDING_NAME",
            y="Device Count",
            color="DEVICE_TYPE",  # Device type determines color
            barmode="stack",
            labels={"BUILDING_NAME": "Buildings", "Device Count": "Device Count", "DEVICE_TYPE": "Device Type"},
            height=680
        )

        # Add total count labels at the top of each bar
        for i, row in total_counts.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["BUILDING_NAME"]],
                y=[row["Device Count"]],
                text=[f"{row['Device Count']:,}"],
                mode="text",
                textposition="top center",
                showlegend=False
            ))

        # Enable range slider for horizontal scrolling with default 50% visible
        if status_column in ["LOCATION_STATUS", "STATUS", "MODE"]:
            num_buildings = len(total_counts)
            fig.update_layout(
                xaxis=dict(
                    rangeslider=dict(visible=True),  # Allows zooming and panning
                    range=[num_buildings // 4, 3 * num_buildings // 4]  # Show 50% of data by default
                ),
                bargap=0.1, 
                bargroupgap=0.05
            )

        # Sort the legend alphabetically (ascending order) and improve layout
        fig.update_layout(
            legend=dict(
                traceorder="normal"  # Ensures the legend follows the order of the data
            ),
            margin=dict(l=20, r=20, t=60, b=160),  # Add margins to prevent cutoff
            autosize=True,  # Enable autosize for responsive behavior
            height=680
        )

        return fig

    # Add after create_chart function definition
    if "location_key_" not in st.session_state:
        st.session_state["location_key_"] = 0
    if "status_key_" not in st.session_state:
        st.session_state["status_key_"] = 0
    if "mode_key_" not in st.session_state:
        st.session_state["mode_key_"] = 0

    # **SECTION 1: TPS STATUS**
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("TPS Status per Building")
    test.write("This graph displays the number of devices with specific TPS status values, categorized by building and device type. It provides insights into TPS-based operational status across the infrastructure, helping identify areas that may need attention based on TPS-specific criteria.")

    # Initialize session state for TPS status filter
    if "tps_status_filter" not in st.session_state:
        st.session_state["tps_status_filter"] = "INACTIVE"  # Default to show inactive devices
    
    show_location = st.toggle(label="Hide/View", key="toggle_location_bar_chart", value=True)

    if show_location:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            campus_options_location = df["CAMPUS"].dropna().astype(str).str.strip().unique().tolist()
            selected_campus_location = st.pills("Select Campus:", campus_options_location, selection_mode="single", key=f"selected_campus_location_{st.session_state['location_key_']}", default="CG")

        with col2:
            # TPS Status filter toggle
            tps_status_options = ["ACTIVE", "INACTIVE"]
            selected_tps_status = st.pills(
                "TPS Status:", 
                tps_status_options, 
                selection_mode="single", 
                default=st.session_state["tps_status_filter"],
                key=f"tps_status_filter_{st.session_state['location_key_']}"
            )
            st.session_state["tps_status_filter"] = selected_tps_status

        with col3:
            # Filter data based on TPS status
            location_filtered_df = df[df["TPS_STATUS"] == selected_tps_status]
            location_filtered_df = location_filtered_df[location_filtered_df["CAMPUS"] == selected_campus_location]

            building_options_location = sorted(location_filtered_df["BUILDING_NAME"].unique().tolist())
            selected_buildings_location = st.multiselect("Select Building:", building_options_location, key=f"selected_building_location_{st.session_state['location_key_']}")
            
            if selected_buildings_location:
                location_filtered_df = location_filtered_df[location_filtered_df["BUILDING_NAME"].isin(selected_buildings_location)]

        with col4:
            # Add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(4) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            reset_location = st.button("Reset Filters", key="reset_filters_button_location")
            if reset_location:
                st.session_state["location_key_"] += 1
                st.session_state["tps_status_filter"] = "INACTIVE"  # Reset to default
                st.rerun()

        if location_filtered_df.empty:
            st.info("No data available for the selected filters in TPS Status.", icon="ℹ️")
        else:
            location_fig = create_chart(location_filtered_df, "LOCATION_STATUS")
            st.plotly_chart(location_fig, use_container_width=True, key="tps_status_chart")
            st.subheader("Detailed Data (TPS Status):")
            if st.toggle(label="Hide/View", key="toggle_switch_location", value=True):
                st.dataframe(location_filtered_df)

    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    st.write("")

    # **SECTION 2: NODE STATUS**
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Node Status per Building")
    test.write("This graph shows the number of devices with specific node status values, organized by building and device type. It provides a clear overview of node status across the infrastructure, helping identify potential issues that may require attention. Users can filter the data by campus and building name for focused analysis.")

    # Initialize session state for Node status filter
    if "node_status_filter" not in st.session_state:
        st.session_state["node_status_filter"] = "OFFLINE"  # Default to show offline devices
    
    show_status = st.toggle(label="Hide/View", key="toggle_status_bar_chart", value=True)

    if show_status:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            campus_options_status = df["CAMPUS"].unique().tolist()
            selected_campus_status = st.pills("Select Campus:", campus_options_status, selection_mode="single", key=f"selected_campus_status_{st.session_state['status_key_']}", default="CG")

        with col2:
            # Node Status filter toggle
            node_status_options = ["ONLINE", "OFFLINE"]
            selected_node_status = st.pills(
                "Node Status:", 
                node_status_options, 
                selection_mode="single", 
                default=st.session_state["node_status_filter"],
                key=f"node_status_filter_{st.session_state['status_key_']}"
            )
            st.session_state["node_status_filter"] = selected_node_status

        with col3:
            # Filter data based on Node status
            status_filtered_df = df[df["NODE_STATUS"] == selected_node_status]
            status_filtered_df = status_filtered_df[status_filtered_df["CAMPUS"] == selected_campus_status]

            building_options_status = sorted(status_filtered_df["BUILDING_NAME"].unique().tolist())
            selected_buildings_status = st.multiselect("Select Building:", building_options_status, key=f"selected_building_status_{st.session_state['status_key_']}")
            
            if selected_buildings_status:
                status_filtered_df = status_filtered_df[status_filtered_df["BUILDING_NAME"].isin(selected_buildings_status)]
        
        with col4:
            # Add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(4) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            reset_status = st.button("Reset Filters", key="reset_filters_button_status")
            if reset_status:
                st.session_state["status_key_"] += 1
                st.session_state["node_status_filter"] = "OFFLINE"  # Reset to default
                st.rerun()

        if status_filtered_df.empty:
            st.info("No data available for the selected filters in Node Status.", icon="ℹ️")
        else:
            status_fig = create_chart(status_filtered_df, "STATUS")
            st.plotly_chart(status_fig, use_container_width=True, key="node_status_chart")
            st.subheader("Detailed Data (Node Status):")
            if st.toggle(label="Hide/View", key="toggle_switch_status", value=True):
                st.dataframe(status_filtered_df)

    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    st.write("")

    # **SECTION 3: LOCATION STATUS**
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Location Status per Building")
    test.write("This graph displays the number of devices with specific location status values, categorized by building and device type. It provides insights into location-based operational status across the infrastructure, helping identify areas that may need attention based on location-specific criteria.")

    # Initialize session state for Location status filter
    if "location_status_filter" not in st.session_state:
        st.session_state["location_status_filter"] = "INACTIVE"  # Default to show inactive devices
    
    show_mode = st.toggle(label="Hide/View", key="toggle_mode_bar_chart", value=True)

    if show_mode:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            campus_options_mode = df["CAMPUS"].unique().tolist()
            selected_campus_mode = st.pills("Select Campus:", campus_options_mode, selection_mode="single", key=f"selected_campus_mode_{st.session_state['mode_key_']}", default="CG")

        with col2:
            # Location Status filter toggle (using TPS_STATUS as proxy for location status)
            location_status_options = ["ACTIVE", "INACTIVE"]
            selected_location_status = st.pills(
                "Location Status:", 
                location_status_options, 
                selection_mode="single", 
                default=st.session_state["location_status_filter"],
                key=f"location_status_filter_{st.session_state['mode_key_']}"
            )
            st.session_state["location_status_filter"] = selected_location_status

        with col3:
            # Filter data based on Location status (using TPS_STATUS as proxy)
            mode_filtered_df = df[df["TPS_STATUS"] == selected_location_status]
            mode_filtered_df = mode_filtered_df[mode_filtered_df["CAMPUS"] == selected_campus_mode]

            building_options_mode = sorted(mode_filtered_df["BUILDING_NAME"].unique().tolist())
            selected_buildings_mode = st.multiselect("Select Building:", building_options_mode, key=f"selected_building_mode_{st.session_state['mode_key_']}")
            
            if selected_buildings_mode:
                mode_filtered_df = mode_filtered_df[mode_filtered_df["BUILDING_NAME"].isin(selected_buildings_mode)]
        
        with col4:
            # Add padding above the reset button
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-of-type(4) {
                padding-top: 25px;
            }
            </style>
            """, unsafe_allow_html=True)
            reset_mode = st.button("Reset Filters", key="reset_filters_button_mode")
            if reset_mode:
                st.session_state["mode_key_"] += 1
                st.session_state["location_status_filter"] = "INACTIVE"  # Reset to default
                st.rerun()

        if mode_filtered_df.empty:
            st.info("No data available for the selected filters in Location Status.", icon="ℹ️")
        else:
            mode_fig = create_chart(mode_filtered_df, "MODE")
            st.plotly_chart(mode_fig, use_container_width=True, key="location_status_chart")
            st.subheader("Detailed Data (Location Status):")
            if st.toggle(label="Hide/View", key="toggle_switch_mode", value=True):
                st.dataframe(mode_filtered_df)

def initialize_session_state_voltage():
    defaults = {
        "selected_campus_voltage": "CG",
        "selected_building_voltage": ["All"],
        "selected_device_voltage": ["All"],
        "reset_filters_voltage": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_voltage_filters():
    st.session_state["reset_filters_voltage"] = True
    st.rerun()

def filter_battery_devices(df):
    return df[
        (df['DEVICE_TYPE'].isin(['NDE', 'NDEB', 'AD400','LEB']))
    ]

def battery_voltage_levels(df):
    filtered_df = filter_battery_devices(df)
    grouped = (
        filtered_df.groupby(['BUILDING_NAME', 'DEVICE_TYPE'])
        .size()
        .reset_index(name='Device Counts')
    )

    # Compute totals per building
    totals = grouped.groupby('BUILDING_NAME')['Device Counts'].sum().to_dict()
    totals_formatted = {building: f"{count:,}" for building, count in totals.items()}

    fig = px.bar(
        grouped,
        x='BUILDING_NAME',
        y='Device Counts',
        color='DEVICE_TYPE',
        barmode='stack',
        title='Battery Voltage Levels',
        height=800,
        labels={'BUILDING_NAME': 'Building Name', 'Device Counts': 'Device Count'}
    )

    # Add total values on top of bars with reduced font size
    fig.add_trace(go.Scatter(
        x=list(totals.keys()), 
        y=list(totals.values()), 
        mode='text',
        text=list(totals_formatted.values()), 
        textposition='top center',
        textfont=dict(size=10)
    ))

    return fig, filtered_df


def get_voltage_range(df):
    # Create a new numeric column for BATTERY_VOLTAGE
    df['BATTERY_VOLTAGE_NUMERIC'] = pd.to_numeric(df['BATTERY_VOLTAGE'], errors='coerce') / 100
    
    # Calculate min and max voltage
    min_voltage = df['BATTERY_VOLTAGE_NUMERIC'].min()
    max_voltage = df['BATTERY_VOLTAGE_NUMERIC'].max()

    # Store in session state to retain values
    if "min_voltage" not in st.session_state:
        st.session_state["min_voltage"] = min_voltage
    if "max_voltage" not in st.session_state:
        st.session_state["max_voltage"] = max_voltage

    return min_voltage, max_voltage


def plot_battery_voltage_status_section(df):
    # st.write(df[df['BUILDING_NAME']=='1551 Brescia'])
    def handle_building_selection():
        selected = st.session_state["selected_building_voltage"]
        if "All" in selected:
            # If user selected "All" along with others, remove "All"
            if len(selected) > 1:
                st.session_state["selected_building_voltage"] = [b for b in selected if b != "All"]
            # If user ONLY selects "All", remove others (even previously selected ones)
            else:
                st.session_state["selected_building_voltage"] = ["All"]
        elif not selected:
            st.session_state["selected_building_voltage"] = ["All"]

    def handle_device_selection():
        selected = st.session_state["selected_device_voltage"]
        if "All" in selected:
            if len(selected) > 1:
                st.session_state["selected_device_voltage"] = [d for d in selected if d != "All"]
            else:
                st.session_state["selected_device_voltage"] = ["All"]
        elif not selected:
            st.session_state["selected_device_voltage"] = ["All"]

    # Custom CSS will be applied directly in the container

    initialize_session_state_voltage()
    # st.subheader("Battery Voltage Status")

    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Battery Voltage Status")
    test.write("This section highlights battery-operated devices with low or critical battery levels, broken down by building and device type. It enables quick identification of power-related issues across the infrastructure. Users can filter the data by campus, building name, device type, and battery status for focused troubleshooting and maintenance planning.")


    if st.toggle(label="Hide/View", key="toggle_status_battery", value=True):

        # 🔹 Get Voltage Range
        min_voltage, max_voltage = get_voltage_range(df)

        # 🔹 Initialize Session State for Filters
        if "selected_campus_voltage" not in st.session_state:
            st.session_state["selected_campus_voltage"] = 'All'
        if "selected_building_voltage" not in st.session_state:
            st.session_state["selected_building_voltage"] = ["All"]
        if "selected_device_voltage" not in st.session_state:
            st.session_state["selected_device_voltage"] = ["All"]
        # if "voltage_threshold" not in st.session_state:
        #     st.session_state["voltage_threshold"] = max_voltage
        if "reset_filters_voltage" not in st.session_state:
            st.session_state["reset_filters_voltage"] = False
        if "Normal" not in st.session_state:
            st.session_state["Normal"] = True
        if "Low" not in st.session_state:
            st.session_state["Low"] = True
        if "Critical" not in st.session_state:
            st.session_state["Critical"] = True
        if "Not reporting" not in st.session_state:
            st.session_state["Not reporting"] = True

        # 🔹 Reset Filters Logic
        if st.session_state["reset_filters_voltage"]:
            st.session_state["selected_campus_voltage"] = 'CG'
            st.session_state["selected_building_voltage"] = ["All"]
            st.session_state["selected_device_voltage"] = ["All"]
            # st.session_state["voltage_threshold"] = max_voltage
            st.session_state["Normal"] = True
            st.session_state["Low"] = True
            st.session_state["Critical"] = True
            st.session_state["Not reporting"] = True
            st.session_state["reset_filters_voltage"] = False
            st.rerun()


        # Define allowed device types
        allowed_device_types = ['NDE', 'NDEB', 'LEB', 'AD400']

        # Create main layout with 3 columns: Left controls, Battery Status, Right space
        col_left, col_battery, col_right = st.columns([3.5, 3, 0.5])

        with col_left:
            # FIRST ROW: Campus and Building
            col1, col2 = st.columns([1.3, 2.2])
            
            campus_options = [campus for campus in df['CAMPUS'].dropna().unique().tolist() if campus.lower() != "unknown"]

            with col1:
                campuses = st.pills(
                    "Select Campus:",
                    campus_options, 
                    default=st.session_state["selected_campus_voltage"], 
                    key="selected_campus_voltage", 
                    selection_mode="single"
                )

            # Get selected device types
            selected_device_types = allowed_device_types  # Default to all allowed types
            if "All" not in st.session_state["selected_device_voltage"]:
                selected_device_types = st.session_state["selected_device_voltage"]

            # Collect selected statuses in a list
            selected_statuses = []
            if st.session_state["Normal"]:
                selected_statuses.append("Normal")
            if st.session_state["Low"]:
                selected_statuses.append("Low")
            if st.session_state["Critical"]:
                selected_statuses.append("Critical")
            if st.session_state["Not reporting"]:
                selected_statuses.append("Not reporting")

            # Filter DataFrame before generating building options
            filtered_for_building = df[
                (df["CAMPUS"] == campuses) &
                (df["DEVICE_TYPE"].isin(selected_device_types)) &
                (df["BATTERY_VOLTAGE"].isin(selected_statuses))
            ]

            building_options = sorted(filtered_for_building['BUILDING_NAME'].dropna().unique().tolist())
            
            with col2:
                building_options_filtered = building_options
                # If user has selected something other than "All", remove "All" from the options
                if "All" not in st.session_state["selected_building_voltage"]:
                    building_options_filtered = [b for b in building_options if b != "All"]
                else:
                    # Restore "All" in the options when nothing is selected
                    building_options_filtered = ["All"] + building_options

                # Check if the selected building exists in the options after filtering
                if any(b not in building_options_filtered for b in st.session_state["selected_building_voltage"]):
                    st.session_state["selected_building_voltage"] = building_options_filtered[:1]  # Default to first option

                st.multiselect(
                    "Select Building:",
                    building_options_filtered,
                    default=st.session_state["selected_building_voltage"],
                    key="selected_building_voltage",
                    on_change=handle_building_selection
                )

            # SECOND ROW: Reset and Device Type
            col3, col4 = st.columns([1.3, 2.2])
            
            with col3:
                # 🔹 Reset Filters Button
                if st.button("Reset Filters", key="reset_filters_button_voltage"):
                    st.session_state["reset_filters_voltage"] = True
                    st.rerun()

            with col4:
                device_options = df[
                    (df["CAMPUS"] == campuses) &
                    (df["BATTERY_VOLTAGE"].notna()) &
                    (df["DEVICE_TYPE"].notna()) &
                    (df["DEVICE_TYPE"].isin(allowed_device_types))
                ]['DEVICE_TYPE'].unique().tolist()

                device_options_filtered = device_options
                # If user has selected something other than "All", remove "All" from the options
                if "All" not in st.session_state["selected_device_voltage"]:
                    device_options_filtered = [d for d in device_options if d != "All"]
                else:
                    # Restore "All" in the options when nothing is selected
                    device_options_filtered = ["All"] + device_options

                # Check if the selected device exists in the options after filtering
                if any(d not in device_options_filtered for d in st.session_state["selected_device_voltage"]):
                    st.session_state["selected_device_voltage"] = device_options_filtered[:1]  # Default to first option

                st.multiselect(
                    "Select Device Type:",
                    device_options_filtered,
                    default=st.session_state["selected_device_voltage"],
                    key="selected_device_voltage",
                    on_change=handle_device_selection
                )

        with col_battery:
            # Battery status container spanning both rows
            with st.container(border=True):
                st.write("**Select battery status:**")
                
                # Create checkboxes in a single row
                col1_status, col2_status, col3_status, col4_status = st.columns(4)
                with col1_status:
                    normal = st.checkbox("Normal", value=st.session_state["Normal"], key="Normal")
                with col2_status:
                    low = st.checkbox("Low", value=st.session_state["Low"], key="Low")
                with col3_status:
                    critical = st.checkbox("Critical", value=st.session_state["Critical"], key="Critical")
                with col4_status:
                    not_reporting = st.checkbox("Not reporting", value=st.session_state["Not reporting"], key="Not reporting")

        # 🔹 Apply Filters
        filtered_df = df.copy()
        filtered_df = filtered_df[filtered_df['CAMPUS'] == campuses]

        if "All" not in st.session_state["selected_building_voltage"]:
            filtered_df = filtered_df[filtered_df['BUILDING_NAME'].isin(st.session_state["selected_building_voltage"])]
        if "All" not in st.session_state["selected_device_voltage"]:
            filtered_df = filtered_df[filtered_df['DEVICE_TYPE'].isin(st.session_state["selected_device_voltage"])]

        # Collect selected statuses in a list
        selected_statuses = []
        if st.session_state["Normal"]:
            selected_statuses.append("Normal")
        if st.session_state["Low"]:
            selected_statuses.append("Low")
        if st.session_state["Critical"]:
            selected_statuses.append("Critical")
        if st.session_state["Not reporting"]:
            selected_statuses.append("Not reporting")

        # Apply filter using .isin()
        if selected_statuses:
            filtered_df = filtered_df[filtered_df["BATTERY_VOLTAGE"].isin(selected_statuses)]
        else:
            filtered_df = filtered_df.iloc[0:0]  # Empty DataFrame if nothing selected

        
        fig, filtered_df = battery_voltage_levels(filtered_df)

        st.plotly_chart(fig)

        st.subheader("Detailed Data:")
        # 🔹 Detailed Data Toggle
        if st.toggle("Hide/View", value=True):
            st.dataframe(filtered_df.drop(columns='BATTERY_VOLTAGE_NUMERIC'))

def analytics_workbench(df):
    """Displays the Analytics Workbench with PyGWalker visualization."""

    # Styling and title
    st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
    # st.subheader("Analytics Workbench")
    test = st.expander("Click to view or hide description", expanded=True)
    test.title("Analytics Workbench")
    test.write("The Analytics Workbench offers an interactive, on-demand visualization tool for exploring base data. Users can drag and drop data fields to generate custom graphs tailored to their analysis needs. With smart handling of different data types (e.g., numerical, categorical, text) and dynamic filtering options, this tool enables deep exploration and easy export of insights in a flexible, visual format.")

    # Generate PyGWalker HTML with dark mode
    pyg_html = pyg.to_html(df, appearance='dark')

    # Toggle for showing PyGWalker (default: visible)
    show_pygwalker = st.toggle(label="Show PyGWalker", key="toggle_pygwalker", value=True)

    # Display PyGWalker if toggle is ON
    if show_pygwalker:
        st.components.v1.html(pyg_html, height=1000, scrolling=False)




def display_system_browser(df):
    @st.fragment
    # def system_browser():

    def system_browser():
        if "search_query_tab1" not in st.session_state:
            st.session_state.search_query_tab1 = []
        if "tag_input_key" not in st.session_state:
            st.session_state.tag_input_key = 0

        # --- Search Query ---
        # st.subheader("Global Browser")
        test = st.expander("Click to view or hide description", expanded=True)
        test.title("Global Browser")
        test.write("This section enables users to search across all data points within the dataset, allowing for comprehensive research and flexible data aggregation. Any records that match the search criteria will be displayed in the 'Detailed Data' section below, making it easy to analyze and export relevant information.")

        def clear_search():
            
            st.session_state.search_query_tab1 = []
            st.session_state.tag_input_key += 1
            # st.rerun()

        search_query = st_tags(
            label="Enter search values:",
            text="Press enter to add",
            suggestions=[],  
            key=f"search_query_tab1_{st.session_state.tag_input_key}"
        )

        st.button("Clear Search", key="clear_search", help="Clear search", on_click=clear_search) 

        df_searched = filter_search_dataframe(df, search_query)
        display_raw_data(df_searched)

        analytics_workbench(df)

    system_browser()



def display_integrations(df):
    @st.fragment
    def integrations():
        # Create a copy of the column
        cleaned_dates = df['LOCAL_DATE_CREATED'].str.replace(
            r'(\d{2}-[A-Z]{3}-\d{2} \d{2}\.\d{2}\.\d{2})\.(\d{6})\d{3} ([AP]M)',
            r'\1.\2 \3',
            regex=True
        )

        # Try converting to datetime without specifying the format
        df['Year'] = pd.to_datetime(cleaned_dates, errors='coerce').dt.year

        # Create two separate containers for filtering and metrics
        metrics_container = st.container()
        filters_container = st.container()

        with filters_container:
            # Sidebar filters (Functional, but will appear below overview metrics visually)
            (selected_campus, selected_building, selected_device_type, 
            selected_status, selected_reader_status, selected_year, selected_term_type) = create_sidebar_filters(df)

            # Filtering the DataFrame based on selections:
            df_filtered = df.copy()
            if selected_campus:
                unique_campuses_options = df['CAMPUS'].dropna().unique().tolist()
                if selected_campus == 'All':
                    df_filtered = df_filtered[df_filtered['CAMPUS'].isin(unique_campuses_options)]
                else:
                    df_filtered = df_filtered[df_filtered['CAMPUS'] == selected_campus]

            if selected_building and ("All" not in selected_building) and 'BUILDING_NAME' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['BUILDING_NAME'].isin(selected_building)]

            if selected_device_type and ("All" not in selected_device_type) and 'DEVICE_TYPE' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['DEVICE_TYPE'].isin(selected_device_type)]

            if selected_status != 'All' and 'TPS_STATUS' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['TPS_STATUS'] == selected_status]

            if selected_reader_status:
                if 'NODE_STATUS' in df_filtered.columns:
                    if selected_reader_status == "All":
                        df_filtered = df_filtered[df_filtered['NODE_STATUS'].notna()]
                    else:
                        df_filtered = df_filtered[df_filtered['NODE_STATUS'] == selected_reader_status]

            if selected_year and ("All" not in selected_year):
                if 'Year' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['Year'].isin(selected_year)]
                else:
                    st.warning("The selected data does not contain a 'Year' column.")

            if selected_term_type and "All" not in selected_term_type:
                if 'TERM_TYPE_SID' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['TERM_TYPE_SID'].astype(str).isin(selected_term_type)]


            # # Reset Filters Button
            # if st.button("Reset Filters", key="reset_filters_button"):
            #     st.session_state['reset_filters'] = True
            #     st.rerun()

        # Custom CSS to reverse the display order
        st.markdown(
            """
            <style>
            .container { display: flex; flex-direction: column-reverse; }
            </style>
            """,
            unsafe_allow_html=True
        )

        with metrics_container:
            # Display summary metrics above filters (Visually above, but runs later in code)
            display_overview_metrics(df_filtered)

        # Display charts
        st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)
        display_totals_per_item(df_filtered)

        # SECTION #3.1: Building Tech per Campus
        plot_building_tech_per_campus(df_filtered)

        # SECTION #3.2: Online Integrations per Campus ===
        st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)

        display_online_integrations_per_campus(df_filtered)            
        
        st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)

        display_total_devices_per_building(df_filtered)

        st.markdown('<hr style="height:2px;border-width:0;color:purple;background-color:purple">', unsafe_allow_html=True)

        display_devices_by_year(df_filtered)

    integrations()


def display_location_status(df):
    @st.fragment
    def location_status():
        # ------ TPS and NODE Section -------
        tps_node_df = filter_tps_node_statuses(df)
        plot_tps_node_statuses(tps_node_df)

    location_status()


def display_battery_status(df):
    @st.fragment
    def battery_status():
        # ------- Battery Voltage Section --------
        plot_battery_voltage_status_section(df)

    battery_status()


def display_transactions():
    # ------ Transactions Section -------
    transactional_df = fetch_transaction_data()
    plot_transaction_volume(transactional_df)
    plot_transaction_volume_per_opening(transactional_df)
    plot_transaction_volume_rankings(transactional_df)

def display_campus_explorer(filtered_df, campus_df):
    @st.fragment
    def campus_explorer():
        # Map Section
        # update_map_center_and_zoom(filtered_df)
        campus_map_filters(campus_df)

    campus_explorer()





def main():
    """Main application function that handles authentication and content display."""
    # First check if the user is authenticated
    if "authentication_status" not in st.session_state or not st.session_state["authentication_status"]:
        st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
        </style>
        """, unsafe_allow_html=True)
    
    # Run authentication check
    authenticated, username, name, is_Admin = check_authentication()
    
    # If not authenticated, stop here
    if not authenticated:
        return
    
    # At this point, the user is authenticated, show proper UI
    display_sidebar_logo()
    # st.logo("https://i.postimg.cc/4ds6cJ3k/logo.png")
    
    # Make sure sidebar is visible after authentication
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: block !important;
        }
                /* Force correct emoji rendering for all emojis */
    [data-testid="stIconEmoji"] {
        font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Android Emoji", emoji !important;
        font-style: normal !important;
        font-weight: normal !important;
        font-variant-emoji: emoji !important;
    }
    
    /* Ensure consistent emoji rendering in navigation */
    [data-testid="stSidebarNav"] [data-testid="stIconEmoji"] {
        font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Android Emoji", emoji !important;
        font-style: normal !important;
        font-variant-emoji: emoji !important;
    }

    </style>
    """, unsafe_allow_html=True)
    
    # Set user role and permissions
    if is_Admin:
        devices_access = True
        chatBot_access = True
        projects_access = True
        settings_access = True
        st.session_state["role"] = "admin" 
    else:
        check_feature_access(username)
        devices_access = st.session_state["user_permissions"][username].get("devices", False)
        chatBot_access = st.session_state["user_permissions"][username].get("chatBot", False)
        projects_access = st.session_state["user_permissions"][username].get("projects", False)
        settings_access = st.session_state["user_permissions"][username].get("settings", False)
        st.session_state["role"] = "client"

    # Apply appropriate styling based on role
    if st.session_state["role"] == "admin":
        st.markdown("""
        <style>
        /* Hide signup.py from Sidebar */
        [data-testid="stSidebarNav"] ul li a[href*="Signup"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] ul li a[href*="ForgotPassword"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    elif st.session_state["role"] == "client":
        css = """
        <style>
        [data-testid="stSidebarNav"] ul li:nth-child(5) {  /* Hide the 5th item */
            display: none;
        }
        [data-testid="stSidebarNav"] ul li a[href*="Signup"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] ul li a[href*="ForgotPassword"] {
            display: none !important;
        }
        """
        # Conditionally hide sidebar items based on access rights
        if not devices_access:
            css += """
            [data-testid="stSidebarNav"] ul li:nth-child(1) {  /* Hide the 1st item */
            display: none;
            }
            """
        if not projects_access:
            css += """
            [data-testid="stSidebarNav"] ul li:nth-child(2) {  /* Hide the 2nd item - Projects */
            display: none;
            }
            """
        if not chatBot_access:
            css += """
            [data-testid="stSidebarNav"] ul li:nth-child(3) {  /* Hide the 3rd item - Graphy */
            display: none;
            }
            """
        if not settings_access:
            css += """
            [data-testid="stSidebarNav"] ul li:nth-child(4) {  /* Hide the 4th item - Settings */
            display: none;
            }
            """
        css += "</style>"
        # Apply the dynamically generated CSS
        st.markdown(css, unsafe_allow_html=True)

    # Add logout and refresh buttons to sidebar
    col1, col2 = st.sidebar.columns([1,1])
    with col1:
        if st.button("Logout", key="logout_devices"):
            logout()
    with col2:
        if st.button('Refresh Data', key="refresh_data_devices"):
            st.session_state['refetch_data'] = True  # Set flag to trigger cache clear
            refresh_data()
            st.rerun()  # Force rerun to apply changes

    # Display content based on user permissions
    if authenticated and devices_access:
        # Check if refresh is requested, then clear cache
        if st.session_state.get("refetch_data", False):
            fetch_data.clear()  # Clears the cached data
            st.session_state["refetch_data"] = False  # Reset flag after clearing

        df = fetch_data()
        df_filtered = df

        campus_df = df.copy()
        initialize_session_state(campus_df)

        # Filtered data
        filtered_df = filter_dataframe(campus_df)
        
        # CSS for styling st.radio as pills
        st.markdown("""
        <style>
            /* Hide the main radio label */
            .stRadio > label {
                display: none !important;
            }
            
            /* Style the radio button container */
            div[data-testid="stRadio"] [role="radiogroup"] {
                display: flex !important;
                flex-direction: row !important;
                gap: 12px !important;
                justify-content: center !important;
                align-items: center !important;
                padding: 15px !important;
                background-color: #1a1a1a !important;
                border-radius: 15px !important;
                margin-bottom: 30px !important;
                flex-wrap: wrap !important;
            }
            
            /* Hide default radio circles */
            div[data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
                display: none !important;
            }
            
            /* Style radio button labels as pills */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] {
                margin-right: 8px !important;
                margin-bottom: 0px !important;
                background-color: #262730 !important;
                border-radius: 25px !important;
                padding: 12px 20px !important;
                color: white !important;
                font-weight: 500 !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
                border: 2px solid transparent !important;
                white-space: nowrap !important;
                min-height: auto !important;
                position: relative !important;
            }
            
            /* Add radio indicator inside the pill */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]::before {
                content: '';
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 2px solid #666;
                background: transparent;
                display: inline-block;
                margin-right: 8px;
                transition: all 0.3s ease;
            }
            
            /* Style the text inside labels */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] > div:last-child {
                background: transparent !important;
                color: white !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] > div:last-child p {
                color: white !important;
                margin: 0 !important;
                font-weight: 500 !important;
            }
            
            /* Hover effect */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:hover {
                background-color: #3a3b47 !important;
                transform: translateY(-2px) !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:hover > div:last-child p {
                color: white !important;
            }
            
            /* Style for selected radio button - keep black background */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) {
                background-color: #262730 !important;
                color: white !important;
                border: 2px solid #ff4b4b !important;
                font-weight: bold !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[type="radio"]:checked)::before {
                background: #ff4b4b !important;
                border-color: #ff4b4b !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:last-child p {
                color: white !important;
                font-weight: bold !important;
            }
            
            /* Alternative selector for selected state using tabindex - keep black background */
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[tabindex="0"]) {
                background-color: #262730 !important;
                color: white !important;
                border: 2px solid #ff4b4b !important;
                font-weight: bold !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[tabindex="0"])::before {
                background: #ff4b4b !important;
                border-color: #ff4b4b !important;
            }
            
            div[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input[tabindex="0"]) > div:last-child p {
                color: white !important;
                font-weight: bold !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Create radio button navigation using native st.radio
        menu_options = [
            "🔎 System Browser",
            "🏗️ Integrations", 
            "🛜 Location Status",
            "🔋 Battery Voltage",
            "🔄 Transactions",
            "🗺️ Campus Explorer"
        ]

        selected_menu_display = st.radio(
            "Navigation Menu",
            options=menu_options,
            horizontal=True,
            label_visibility="collapsed",
            key="devices_menu_radio"
        )

        # Convert display text to internal values
        if selected_menu_display == "🔎 System Browser":
            selected_menu = "system-browser"
        elif selected_menu_display == "🏗️ Integrations":
            selected_menu = "integrations"
        elif selected_menu_display == "🛜 Location Status":
            selected_menu = "location-status"
        elif selected_menu_display == "🔋 Battery Voltage":
            selected_menu = "battery-voltage"
        elif selected_menu_display == "🔄 Transactions":
            selected_menu = "transactions"
        elif selected_menu_display == "🗺️ Campus Explorer":
            selected_menu = "campus-explorer"
        else:
            selected_menu = "system-browser"

        # Display content based on selected menu
        if selected_menu == "system-browser":
            display_system_browser(df)
        elif selected_menu == "integrations":
            display_integrations(df)
        elif selected_menu == "location-status":
            display_location_status(df)
        elif selected_menu == "battery-voltage":
            display_battery_status(df)
        elif selected_menu == "transactions":
            display_transactions()
        elif selected_menu == "campus-explorer":
            display_campus_explorer(filtered_df, campus_df)

    elif authenticated and projects_access:
        st.switch_page("pages/2_🗂️Projects.py")

    elif authenticated and chatBot_access:
        st.switch_page("pages/3_🤖Graphy.py")

    elif authenticated and settings_access:
        st.switch_page("pages/4_⚙️Settings.py")
        
    elif authenticated and not devices_access and not projects_access and not chatBot_access and not settings_access:   
        st.error("Please contact the Admin to receive the required level of access.")

if __name__ == "__main__":
    main()