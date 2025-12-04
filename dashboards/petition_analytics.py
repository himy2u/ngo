#!/usr/bin/env python3
"""
NGO Platform - Petition Analytics Dashboard
Interactive Streamlit dashboard for petition data analysis.
"""

import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Petition Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Database connection
@st.cache_resource
def get_database_connection():
    """Create database connection."""
    return psycopg2.connect(
        host="localhost", port=5432, database="petitions", user="postgres", password="postgres"
    )


# Data fetching functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_summary_stats():
    """Fetch summary statistics."""
    conn = get_database_connection()
    query = """
        SELECT
            COUNT(*) as total_petitions,
            SUM(signature_count) as total_signatures,
            ROUND(AVG(signature_count), 0) as avg_signatures,
            MAX(signature_count) as max_signatures,
            COUNT(CASE WHEN status = 'open' THEN 1 END) as open_petitions,
            COUNT(CASE WHEN signature_count >= 100000 THEN 1 END) as viral_petitions,
            COUNT(CASE WHEN government_response_at IS NOT NULL THEN 1 END) as with_response,
            ROUND(100.0 * COUNT(CASE WHEN government_response_at IS NOT NULL THEN 1 END) / COUNT(*), 1) as response_rate
        FROM raw_petitions
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df.iloc[0]


@st.cache_data(ttl=300)
def fetch_top_petitions(limit=10):
    """Fetch top petitions by signatures."""
    conn = get_database_connection()
    query = f"""
        SELECT
            petition_id,
            action as title,
            signature_count,
            status,
            created_at,
            CASE WHEN government_response_at IS NOT NULL THEN 'Yes' ELSE 'No' END as has_response
        FROM raw_petitions
        ORDER BY signature_count DESC
        LIMIT {limit}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def fetch_signature_trend():
    """Fetch signature trend over time."""
    conn = get_database_connection()
    query = """
        SELECT
            DATE_TRUNC('day', created_at::timestamp) as date,
            SUM(SUM(signature_count)) OVER (ORDER BY DATE_TRUNC('day', created_at::timestamp)) as cumulative_signatures
        FROM raw_petitions
        WHERE created_at IS NOT NULL
        GROUP BY DATE_TRUNC('day', created_at::timestamp)
        ORDER BY date
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def fetch_status_distribution():
    """Fetch petition status distribution."""
    conn = get_database_connection()
    query = """
        SELECT
            status,
            COUNT(*) as count,
            SUM(signature_count) as total_signatures
        FROM raw_petitions
        GROUP BY status
        ORDER BY count DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def fetch_monthly_trends():
    """Fetch monthly petition trends."""
    conn = get_database_connection()
    query = """
        SELECT
            DATE_TRUNC('month', created_at::timestamp) as month,
            COUNT(*) as petition_count,
            SUM(signature_count) as total_signatures,
            ROUND(AVG(signature_count), 0) as avg_signatures_per_petition
        FROM raw_petitions
        WHERE created_at IS NOT NULL
        GROUP BY DATE_TRUNC('month', created_at::timestamp)
        ORDER BY month DESC
        LIMIT 12
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# Main dashboard
def main():
    """Main dashboard function."""

    # Header
    st.title("📊 Petition Analytics Dashboard")
    st.markdown("Real-time analytics for UK Parliament petitions")

    # Sidebar
    with st.sidebar:
        st.header("Filters")

        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        st.info("""
        **Dashboard Features:**
        - Real-time petition metrics
        - Signature trends over time
        - Top performing petitions
        - Government response analytics
        """)

        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch data
    try:
        stats = fetch_summary_stats()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        st.info("Make sure PostgreSQL is running and contains petition data.")
        st.stop()

    # Summary metrics
    st.header("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Petitions",
            value=f"{int(stats['total_petitions']):,}",
            delta=f"{int(stats['open_petitions'])} open",
        )

    with col2:
        st.metric(
            label="Total Signatures",
            value=f"{int(stats['total_signatures']):,}",
            delta=f"Avg: {int(stats['avg_signatures']):,}",
        )

    with col3:
        st.metric(
            label="Viral Petitions (100K+)",
            value=f"{int(stats['viral_petitions'])}",
            delta=f"{(stats['viral_petitions'] / stats['total_petitions'] * 100):.1f}% of total",
        )

    with col4:
        st.metric(
            label="Government Response Rate",
            value=f"{float(stats['response_rate']):.1f}%",
            delta=f"{int(stats['with_response'])} responses",
        )

    st.markdown("---")

    # Main content area - two columns
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Signature trend chart
        st.subheader("📈 Cumulative Signatures Over Time")
        trend_data = fetch_signature_trend()

        fig = px.area(
            trend_data,
            x="date",
            y="cumulative_signatures",
            title="Total Signatures Growth",
            labels={"date": "Date", "cumulative_signatures": "Cumulative Signatures"},
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Status distribution pie chart
        st.subheader("📊 Petition Status")
        status_data = fetch_status_distribution()

        fig = px.pie(
            status_data, values="count", names="status", title="Distribution by Status", hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Top petitions table
    st.subheader("🔝 Top Petitions by Signatures")

    # Number of petitions to show
    n_petitions = st.slider("Number of petitions to display:", 5, 50, 10)
    top_petitions = fetch_top_petitions(n_petitions)

    # Format the table
    st.dataframe(
        top_petitions,
        column_config={
            "petition_id": st.column_config.NumberColumn("ID", format="%d"),
            "title": st.column_config.TextColumn("Petition Title", width="large"),
            "signature_count": st.column_config.NumberColumn("Signatures", format="%d"),
            "status": st.column_config.TextColumn("Status"),
            "created_at": st.column_config.DatetimeColumn("Created Date"),
            "has_response": st.column_config.TextColumn("Gov Response"),
        },
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("---")

    # Monthly trends
    st.subheader("📅 Monthly Petition Trends (Last 12 Months)")

    monthly_data = fetch_monthly_trends()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            monthly_data,
            x="month",
            y="petition_count",
            title="New Petitions per Month",
            labels={"month": "Month", "petition_count": "Number of Petitions"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            monthly_data,
            x="month",
            y="avg_signatures_per_petition",
            title="Average Signatures per Petition",
            labels={"month": "Month", "avg_signatures_per_petition": "Avg Signatures"},
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.markdown("---")
    st.caption("NGO Platform | Data from UK Parliament Petitions API | Built with Streamlit")


if __name__ == "__main__":
    main()
