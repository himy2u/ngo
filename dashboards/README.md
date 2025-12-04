# 📊 NGO Platform Dashboards

Interactive data dashboards for petition analytics.

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
uv sync

# Ensure PostgreSQL is running with petition data
docker compose -f dev/docker-compose.yaml ps
```

### Run Dashboard
```bash
# From project root
streamlit run dashboards/petition_analytics.py

# Or with custom port
streamlit run dashboards/petition_analytics.py --server.port 8501
```

The dashboard will open in your browser at `http://localhost:8501`

## 📈 Dashboard Features

### Main Dashboard
- **Key Metrics**: Total petitions, signatures, viral rate, government response rate
- **Cumulative Signature Trend**: Growth over time
- **Status Distribution**: Open vs Closed vs Rejected petitions
- **Top Petitions Table**: Most signed petitions with filters
- **Monthly Trends**: New petitions and average signatures per month

### Data Quality Page (Coming Soon)
- Data completeness scores
- Quality check results
- Validation failures
- Data freshness metrics

### Pipeline Monitoring (Coming Soon)
- Pipeline execution status
- Run history
- Error logs
- Performance metrics

## 🎨 Customization

### Database Connection
Edit connection parameters in `petition_analytics.py`:
```python
@st.cache_resource
def get_database_connection():
    return psycopg2.connect(
        host='your-host',
        port=5432,
        database='your-db',
        user='your-user',
        password='your-password'
    )
```

### Cache TTL
Adjust cache time-to-live for data freshness:
```python
@st.cache_data(ttl=300)  # 5 minutes
```

## 🔧 Troubleshooting

### Dashboard won't start
```bash
# Check Streamlit is installed
streamlit --version

# Reinstall if needed
uv add streamlit plotly
```

### Database connection errors
```bash
# Verify PostgreSQL is running
docker exec dev-postgres-1 psql -U postgres -d petitions -c "SELECT COUNT(*) FROM raw_petitions;"

# Check if data exists
psql -h localhost -p 5432 -U postgres -d petitions -c "SELECT COUNT(*) FROM raw_petitions;"
```

### No data showing
```bash
# Load sample data
python data/scripts/load_data.py
```

## 📚 Additional Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
