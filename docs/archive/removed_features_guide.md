# Removed Dashboard Features Guide

This document contains the code for features that were removed from the `dashboard/app_zepto.py` file upon request. You can restore these features by adding the code back to the script.

## Analytics Charts (Pie Chart & Histogram)

**Location:** Were located after the Metrics section and before the Data Grid.
**Purpose:** Displayed visual breakdown of Stock Availability and Price Distribution.

**Code to Restore:**
```python
# Charts
st.subheader("📊 Analytics")
c1, c2 = st.columns(2)

with c1:
    st.markdown("### Availability Status")
    if 'availability' in filtered_df.columns:
        fig_avail = px.pie(filtered_df, names='availability', title="In Stock vs Out of Stock", hole=0.4)
        st.plotly_chart(fig_avail, use_container_width=True)

with c2:
    st.markdown("### Price Distribution")
    if 'price' in filtered_df.columns:
        fig_price = px.histogram(filtered_df, x='price', nbins=30, title="Price Distribution", color_discrete_sequence=['#9C27B0'])
        st.plotly_chart(fig_price, use_container_width=True)
```

**Where to place it:**
Insert this code block immediately after the `Metrics` section (around line 191) and before the `Data Explorer` section.

## Average Price Metric

**Location:** Inside the Metrics section (top of the dashboard).
**Purpose:** Displayed the average price of filtered products.

**Code to Restore:**
```python
# Change st.columns(3) back to st.columns(4)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Products", len(filtered_df))

# Restored Metric
avg_price = filtered_df['price'].mean() if 'price' in filtered_df.columns else 0
col2.metric("Avg Price", f"₹{avg_price:.2f}")

# Shift other metrics back to col3, col4
# ...
```
