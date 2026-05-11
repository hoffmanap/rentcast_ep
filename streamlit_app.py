import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="El Paso Rental Tracker", layout="wide")

st.title("🏠 El Paso Rental Market Trends")

# Load and process data
@st.cache_data(ttl=3600)
def load_data():
    if os.path.exists('rent_history.csv'):
        df = pd.read_csv('rent_history.csv')
        df['capture_date'] = pd.to_datetime(df['capture_date']).dt.date
        # Calculate Price per SqFt safely
        df['price_per_sqft'] = df['price'] / df['squareFootage']
        return df
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data found. Please run the collector script first.")
else:
    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("Controls")
    
    # Toggle for Price vs Price/SqFt
    view_mode = st.sidebar.radio("View Metric:", ["Total Price", "Price per SqFt"])
    metric_col = 'price' if view_mode == "Total Price" else 'price_per_sqft'
    metric_label = "Price ($)" if view_mode == "Total Price" else "Price / SqFt ($)"

    # Fix for the Slider Error
    available_dates = sorted(df['capture_date'].unique(), reverse=True)
    if len(available_dates) > 1:
        selected_date = st.sidebar.select_slider(
            "Select Snapshot Week",
            options=available_dates
        )
    else:
        selected_date = available_dates[0]
        st.sidebar.info(f"Viewing snapshot for: {selected_date}")

    # Filter data for the selected week
    week_df = df[df['capture_date'] == selected_date].copy()

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Listings Tracked", len(week_df))
    col2.metric(f"Avg {view_mode}", f"${week_df[metric_col].mean():,.2f}")
    col3.metric("Median Year Built", int(week_df['yearBuilt'].median()))

    # --- MAP ---
    st.subheader(f"Rental Density - {selected_date}")
    fig_map = px.scatter_mapbox(
        week_df, 
        lat="latitude", 
        lon="longitude", 
        color=metric_col,
        size='price' if view_mode == "Total Price" else None,
        hover_name="formattedAddress",
        hover_data=["price", "price_per_sqft", "bedrooms"],
        color_continuous_scale="Viridis",
        zoom=10,
        mapbox_style="carto-positron"
    )
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    # --- TRENDS BY BEDROOM COUNT ---
    st.subheader(f"{view_mode} Trends by Bedroom Count")
    
    # Categorize bedrooms for cleaner graphing
    def cat_beds(n):
        if n <= 1: return "1 Bed"
        if n == 2: return "2 Bed"
        return "3+ Beds"
    
    df['Bed Category'] = df['bedrooms'].apply(cat_beds)
    
    # Group data by date and bedroom category
    trend_df = df.groupby(['capture_date', 'Bed Category'])[metric_col].mean().reset_index()
    
    fig_trend = px.line(
        trend_df, 
        x='capture_date', 
        y=metric_col, 
        color='Bed Category',
        markers=True,
        labels={metric_col: metric_label, 'capture_date': 'Week'},
        line_shape="linear"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("View Raw Data"):
        st.write(week_df)
