# 📊 TRANSACTIONS.CSV - Complete Data Guide & Troubleshooting

## 📈 Overview
- **Type**: Access transactions dataset across university buildings
- **Typical use**: Analyze access patterns, credential usage, and transaction volumes
- **Total columns**: 10 fields

## 🏗️ Data Structure

### 📍 **Location and Time**
- **BUILDING_NAME**: Name of the building where the transaction occurred
- **TRANSACTION_DATE**: Date of the transaction (YYYY-MM-DD)
- **TRANSACTION_HOUR**: Hour of the transaction (0-23)
- **LOCATION**: Location ID (numeric)
- **LOCATION_DESCRIPTION**: Detailed description of the location (e.g., "G-1300CS-115Z-Office Circulation-MTMS15-EXT")

### 🔢 **Transaction Metrics**
- **TOTAL_TRANS**: Total number of transactions for the given record
- **MAGSTRIPE**: Number of transactions using magstripe credentials
- **PROXIMITY**: Number of transactions using proximity credentials
- **BIOMETRIC**: Number of transactions using biometric credentials
- **MOBILEANDREMOTE**: Number of transactions using mobile or remote credentials

## 🎯 **Recommended Visualization Queries**

### **Transactions by Building**
```sql
-- Total transactions per building
SELECT BUILDING_NAME, SUM(TOTAL_TRANS) as total
FROM transactions GROUP BY BUILDING_NAME
```

### **Transactions by Credential Type**
```sql
-- Credential usage breakdown per building
SELECT BUILDING_NAME, SUM(MAGSTRIPE) as magstripe, SUM(PROXIMITY) as proximity, SUM(BIOMETRIC) as biometric, SUM(MOBILEANDREMOTE) as mobile
FROM transactions GROUP BY BUILDING_NAME
```

### **Hourly Patterns**
```sql
-- Transactions by hour
SELECT TRANSACTION_HOUR, SUM(TOTAL_TRANS) as total
FROM transactions GROUP BY TRANSACTION_HOUR
```

### **Daily Trends**
```sql
-- Transactions by date
SELECT TRANSACTION_DATE, SUM(TOTAL_TRANS) as total
FROM transactions GROUP BY TRANSACTION_DATE
```

## 📋 **Visualization Parameters**

### **For COUNT/SUM Charts**
- **x_column**: BUILDING_NAME, TRANSACTION_DATE, TRANSACTION_HOUR
- **y_column**: TOTAL_TRANS, MAGSTRIPE, PROXIMITY, BIOMETRIC, MOBILEANDREMOTE
- **aggregation**: "sum" (recommended), "count" (for record counts)
- **group_by**: BUILDING_NAME, TRANSACTION_DATE, TRANSACTION_HOUR, credential type
- **color_by**: Credential type (MAGSTRIPE, PROXIMITY, etc.)

### **For PIE CHARTS**
- **x_column**: Credential type or BUILDING_NAME (for top N buildings)
- **aggregation**: "sum"
- **y_column**: TOTAL_TRANS or credential columns
- **Note**: Pie charts work best with 4-8 categories. System will automatically limit data if needed.

### **For BAR/STACKED BAR CHARTS**
- **x_column**: BUILDING_NAME, TRANSACTION_DATE, TRANSACTION_HOUR
- **group_by**: Credential type or building
- **aggregation**: "sum"
- **color_by**: Credential type

## ⚠️ **Important Rules**

1. **For transaction totals**: Use `aggregation: "sum"` and y_column as TOTAL_TRANS or credential columns
2. **Credential breakdown**: Use MAGSTRIPE, PROXIMITY, BIOMETRIC, MOBILEANDREMOTE for detailed analysis
3. **Hourly/daily analysis**: Use TRANSACTION_HOUR or TRANSACTION_DATE as x_column
4. **Too many buildings**: Use bar/treemap for top N buildings, or filter for specific buildings

## 🔄 **How Data Processing Works**

### **Step 1: Data Input**
- **Raw data**: Each row is a summary of transactions for a location, date, and hour
- **User query**: "Using a stacked bar chart, show credential usage per building"

### **Step 2: Automatic Processing**
- **System aggregates**: Groups by BUILDING_NAME and sums credential columns
- **Result**: DataFrame with columns ['BUILDING_NAME', 'MAGSTRIPE', 'PROXIMITY', 'BIOMETRIC', 'MOBILEANDREMOTE']

### **Step 3: Chart Creation**
- **Stacked bar**: Each bar is a building, segments are credential types
- **Pie chart**: Sums by credential type or building

## 🔍 **Valid Query Examples**

✅ **VALID PIE CHARTS**:
- "Using a pie chart, plot the share of each credential type in the last 30 days"
- "Using a pie chart, plot the top 8 buildings by total transactions"

✅ **VALID BAR CHARTS**:
- "Using a bar chart, plot the total transactions per building"
- "Using a bar chart, plot the number of magstripe transactions per hour"

✅ **VALID STACKED CHARTS**:
- "Using a stacked bar chart, show credential usage per building"
- "Using a stacked bar chart, plot transactions by hour and credential type"

✅ **VALID LINE CHARTS**:
- "Using a line chart, plot daily total transactions over the past month"

✅ **VALID HISTOGRAMS**:
- "Using a histogram, plot the distribution of transactions per hour"

❌ **INVALID QUERIES**:
- "Average of BUILDING_NAME" → not numeric
- "Sum of LOCATION_DESCRIPTION" → not numeric
- "Total of non-existent column" → column must exist

## 🛠️ **Troubleshooting Common Issues**

### **Too Many Categories**
❌ **Error**: Charts with 100+ buildings become unreadable
✅ **Solution**: System automatically limits to TOP N items:
- Pie charts: 8 categories max
- Bar charts: 20 items max
- Stacked bars: 15 items max

### **Column Not Found**
❌ **Error**: "Column 'X' not found in dataset"
✅ **Solution**: Use exact column names:
- BUILDING_NAME, TRANSACTION_DATE, TRANSACTION_HOUR, TOTAL_TRANS, MAGSTRIPE, PROXIMITY, BIOMETRIC, MOBILEANDREMOTE

### **Aggregation Issues**
❌ **Error**: "Cannot aggregate non-numeric data"
✅ **Solution**: Use "sum" aggregation for transaction columns

### **Best Practices**
✅ **For totals**: Always use "sum" aggregation for transaction columns
✅ **For credential analysis**: Use stacked bar or pie charts for breakdowns
✅ **For time trends**: Use line or bar charts with TRANSACTION_DATE or TRANSACTION_HOUR
✅ **For many buildings**: Use treemaps or bar charts with automatic limiting 