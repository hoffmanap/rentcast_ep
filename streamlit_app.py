import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="El Paso Rental Tracker", layout="wide")

st.title("🏠 El Paso Rental Market Trends")
st.markdown("Tracking rental listings, pricing, and density over time.")

# Load the historical CSV
@st.cache_data
def load_data():
    if os.path.exists('rent_history.csv'):
        df = pd.read_csv('rent_history.csv')
        df['capture_date'] = pd.to_datetime(df['capture_date'])
        return df
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No data found. Please run the collector script first.")
else:
    # Sidebar - Time Selection
    st.sidebar.header("Filters")
    available_dates = sorted(df['capture_date'].unique(), reverse=True)
    selected_date = st.sidebar.select_slider(
        "Select Snapshot Week",
        options=available_dates,
        format_func=lambda x: x.strftime('%Y-%m-%d')
    )

    # Filter data for the selected week
    week_df = df[df['capture_date'] == selected_date]

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Listings Tracked", len(week_df))
    col2.metric("Avg Rent", f"${week_df['price'].mean():,.0f}")
    col3.metric("Avg Year Built", int(week_df['yearBuilt'].dropna().mean()))

    # Map Visualization
    st.subheader(f"Rental Density - Week of {selected_date.strftime('%Y-%m-%d')}")
    
    # Map using Plotly for more control (allows hover data like Address and Price)
    fig = px.scatter_mapbox(
        week_df, 
        lat="latitude", 
        lon="longitude", 
        color="price",
        size="price",
        hover_name="formattedAddress",
        hover_data=["price", "bedrooms", "yearBuilt"],
        color_continuous_scale=px.colors.cyclical.IceFire, 
        size_max=15, 
        zoom=10,
        mapbox_style="carto-positron"
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # Historical Price Trend for the City
    st.subheader("Market Price Trend")
    trend_df = df.groupby('capture_date')['price'].mean().reset_index()
    st.line_chart(trend_df.set_index('capture_date'))

    # Raw Data View
    with st.expander("View Raw Data for this Week"):
        st.write(week_df)