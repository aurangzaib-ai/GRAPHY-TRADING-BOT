# 📊 DEVICES.CSV - Complete Data Guide & Troubleshooting

## 📈 Overview
- **Total records**: 17,525 devices
- **Total columns**: 16 fields
- **Type**: Security devices dataset across university campuses

## 🏗️ Data Structure

### 📍 **Location and Geography**
- **CAMPUS** (4 unique values):
  - `CG`: Main campus (17,189 devices - 98%)
  - `RSMAES`: Secondary campus (265 devices)
  - `CSTARS`: Smaller campus (42 devices)
  - `UNKNOWN`: Unknown location (29 devices)

- **BUILDING_NAME** (124 unique buildings):
  - Examples: "University Village 4", "Richter Library", "Allen Hall"
  - Each building has a unique ID in BUILDING_ID

- **LOCATION_NUMBER** (17,384 unique locations):
  - Unique identifier for each location within buildings

- **LOCATION_DESCRIPTION** (17,145 unique descriptions):
  - Detailed descriptions like "G-UV3-314-Telecom-AD400-INT"

### 🔧 **Devices and Technology**
- **DEVICE_TYPE** (25 different types):
  - Examples: "NDE", "V100", "MTMS15", "GWE"
  - Access control device types

- **TECH** (2 technologies):
  - `Mercury`: 8,898 devices (51%)
  - `VertX`: 8,627 devices (49%)

- **SUBTYPE_DESCRIPTION** (24 subtypes, 65% filled):
  - Examples: "Schlage 400 PRK", "Schlage MTMSK15 Multi Keypad Mag"

### ⚡ **Status and Operation**
- **TPS_STATUS** (TPS Status):
  - `ACTIVE`: 17,443 devices (99.5%)
  - `INACTIVE`: 82 devices (0.5%)

- **NODE_STATUS** (Connectivity Status):
  - `ONLINE`: 16,772 devices (95.7%)
  - `OFFLINE`: 655 devices (3.7%)
  - `UNKNOWN`: 98 devices (0.6%)

- **BATTERY_VOLTAGE** (Battery Level):
  - `Not reporting`: 9,096 devices (52%)
  - `Normal`: 8,353 devices (48%)
  - `Low`: 47 devices
  - `Critical`: 29 devices

### 📅 **Dates and Time**
- **LOCAL_DATE_CREATED**: Creation date (99.7% filled)
- **TRANSITION_DATETIME**: Last transition date (48% filled)

## 🎯 **Recommended Visualization Queries**

### **Count by Campus**
```sql
-- Count of locations per campus
SELECT CAMPUS, COUNT(LOCATION_NUMBER) as count
FROM devices GROUP BY CAMPUS
```

### **Count by Building**
```sql
-- Count of devices per building
SELECT BUILDING_NAME, COUNT(*) as count
FROM devices GROUP BY BUILDING_NAME
```

### **Device Analysis**
```sql
-- Count of device types per campus
SELECT CAMPUS, DEVICE_TYPE, COUNT(*) as count
FROM devices GROUP BY CAMPUS, DEVICE_TYPE
```

### **Connectivity Status**
```sql
-- Device status by building
SELECT BUILDING_NAME, NODE_STATUS, COUNT(*) as count
FROM devices GROUP BY BUILDING_NAME, NODE_STATUS
```

## 📋 **Visualization Parameters**

### **For COUNT Charts**
- **x_column**: CAMPUS, BUILDING_NAME, DEVICE_TYPE, NODE_STATUS, TECH
- **group_by**: For stacked bars (DEVICE_TYPE, NODE_STATUS, TECH)
- **aggregation**: "count"
- **y_column**: Can be any column (will be ignored for counting)

### **For PIE CHARTS**
- **x_column**: CAMPUS, NODE_STATUS, TECH, BATTERY_VOLTAGE
- **aggregation**: "count" (always recommended for pie charts)
- **y_column**: Automatically handled by the system
- **Note**: Pie charts work best with 4-8 categories. System will automatically limit data if needed.

### **For BAR CHARTS**
- **x_column**: CAMPUS, BUILDING_NAME (top 10), DEVICE_TYPE
- **aggregation**: "count"
- **color_by**: TECH, NODE_STATUS, DEVICE_TYPE

### **For STACKED BAR CHARTS**
- **x_column**: CAMPUS, BUILDING_NAME
- **group_by**: DEVICE_TYPE, TECH, NODE_STATUS
- **aggregation**: "count"

## ⚠️ **Important Rules**

1. **For counts**: Always use `aggregation: "count"` and y_column can be any column
2. **Dominant campus**: CG has 98% of devices
3. **Connectivity**: 95% of devices are online
4. **Technologies**: Mercury and VertX are balanced (50/50)
5. **Buildings**: 124 different buildings, some with few devices

## 🔄 **How Data Processing Works**

### **Step 1: Data Input**
- **Raw data**: 17,525 rows with all device information
- **User query**: "Using a pie chart, plot the count of locations per campus"

### **Step 2: Automatic Processing**
- **System aggregates**: Groups by CAMPUS, counts LOCATION_NUMBER
- **Result**: DataFrame with columns ['CAMPUS', 'count']

### **Step 3: Chart Creation**
- **Old behavior**: ❌ Tried to use original 'LOCATION_NUMBER' column (doesn't exist anymore)
- **New behavior**: ✅ Automatically detects 'count' column and uses it

### **Why This Matters**
- **For pie charts**: System always creates aggregated data first
- **Column mapping**: Original columns may not exist in processed data
- **Automatic detection**: No manual intervention needed

## 🔍 **Valid Query Examples**

✅ **VALID PIE CHARTS** (Perfect for categories):
- "Using a pie chart, plot the count of locations per campus" → 4 categories ✨
- "Using a pie chart, plot the technology distribution" → 2 categories ✨
- "Using a pie chart, plot the device status distribution" → 3 categories ✨
- "Using a pie chart, plot the battery voltage levels" → 4 categories ✨

✅ **VALID BAR CHARTS**:
- "Using a bar chart, plot the count of devices per building" → TOP 20 automatically
- "Using a bar chart, plot the count of device types" → All 25 types

✅ **VALID STACKED CHARTS**:
- "Using a stacked bar chart, plot device types per campus" → Perfect visualization
- "Using a stacked bar chart, plot device status by campus" → Clear comparison

✅ **VALID TREEMAPS**:
- "Using a treemap chart, plot the total locations per building" → 124 buildings organized

❌ **INVALID QUERIES**:
- "Average voltage per building" → voltage is categorical, not numeric
- "Sum of locations" → locations are unique IDs, sum doesn't make sense
- "Total latitude per campus" → geographic coordinates can't be summed

## 🛠️ **Troubleshooting Common Issues**

### **Pie Chart Errors**
❌ **Error**: "Invalid y column 'LOCATION_NUMBER' for pie chart"
✅ **Solution**: This is automatically fixed. The system now detects processed data and uses 'count' column automatically.

### **Too Many Categories**
❌ **Error**: Charts with 50+ items become unreadable
✅ **Solution**: System automatically limits to TOP N items:
- Pie charts: 8 categories max
- Bar charts: 20 items max
- Stacked bars: 15 items max

### **Column Not Found**
❌ **Error**: "Column 'X' not found in dataset"
✅ **Solution**: Use exact column names:
- CAMPUS, BUILDING_NAME, DEVICE_TYPE, NODE_STATUS, TECH

### **Aggregation Issues**
❌ **Error**: "Cannot aggregate categorical data"
✅ **Solution**: Use "count" aggregation for categorical columns like DEVICE_TYPE, CAMPUS

### **Treemap Issues**
❌ **Error**: "text() got multiple values for keyword argument 'ha'"
✅ **Solution**: This is automatically fixed. Text alignment conflicts resolved.

❌ **Error**: "treemap visualization requires the 'squarify' library"
✅ **Solution**: Library is automatically installed with the system.

### **Best Practices**
✅ **For counts**: Always use "count" aggregation
✅ **For categories**: Use CAMPUS (4 items), TECH (2 items), NODE_STATUS (3 items)
✅ **For many items**: Use treemaps or bar charts with automatic limiting
✅ **For comparisons**: Use stacked bar charts with proper group_by
✅ **For treemaps**: Perfect for long category names (auto text wrapping)
✅ **For 124+ buildings**: Treemaps are ideal with multi-line text support 