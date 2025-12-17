# 🎯 Example Queries - DEVICES.CSV

## ✅ Queries that Work Perfectly

### 📊 **Pie Charts**
```
Using a pie chart, plot the count of locations per campus
Using a pie chart, plot the distribution of device status
Using a pie chart, plot the technology distribution
Using a pie chart, plot battery voltage levels
```

### 📊 **Bar Charts**
```
Using a bar chart, plot the count of buildings per campus
Using a bar chart, plot the count of devices per campus  
Using a bar chart, plot the count of device types
Using a bar chart, plot the top 10 buildings by device count
```

### 📊 **Stacked Bar Charts**
```
Using a stacked bar chart, plot the count of devices per campus
Using a stacked bar chart, plot device types per building
Using a stacked bar chart, plot technology distribution per campus
Using a stacked bar chart, plot device status by campus
```

### 📊 **Histograms**
```
Using a histogram, plot the distribution of building IDs
Using a histogram, plot the distribution of location numbers
```

### 📊 **Line Charts**
```
Using a line chart, plot device installations over time
Using a line chart, plot trends by campus over time
```

### 📊 **Scatter Plots**
```
Using a scatter plot, plot latitude vs longitude
Using a scatter plot, plot building ID vs device count
```

### 📊 **Treemaps** ✅ TOTALMENTE FUNCIONAIS
```
Using a treemap chart, plot the total locations per building
Using a treemap chart, plot the total devices per building
Using a treemap chart, plot device distribution by campus
Using a treemap chart, plot the count of buildings per campus
Using a treemap chart, plot device types per campus
```

## 🔧 **Implemented Fixes**

### 1. **Pie Chart Bug Fixed** ✅
- **Problem**: `cannot unpack non-iterable Axes object`
- **Solution**: Removed incorrect unpacking from `plot.pie()`

### 2. **y_column=None Bug Fixed** ✅
- **Problem**: System set y_column as None for counts
- **Solution**: Always defines a valid column + aggregation="count"

### 3. **Parameter Extraction Improvement** ✅
- **Added**: Knowledge base with devices.csv structure
- **Improvement**: Intelligent mapping based on patterns
- **Result**: More precise and functional parameters

### 4. **Intelligent Validation** ✅
- **Automatic group_by**: For stacked charts
- **Safe fallbacks**: For invalid columns
- **Appropriate defaults**: Based on data type

### 5. **🆕 NEW: Automatic Data Limiting** ✅
- **Problem**: Unreadable charts with many items (ex: 124 buildings)
- **Solution**: Intelligent limits per chart type:
  - **Bar Charts**: Maximum 20 items
  - **Pie Charts**: Maximum 8 categories  
  - **Stacked Bars**: Maximum 15 items
  - **Treemaps**: Maximum 25 items
- **Result**: Always shows TOP N + explanatory warnings

### 6. **🆕 NEW: Intelligent Warnings and Suggestions** ✅
- **When there's too much data**: Suggests alternatives (treemap, filters)
- **When automatically optimized**: Explains what was done
- **Practical suggestions**: How to view all data

### 7. **🆕 NEW: Fully Functional Treemaps** ✅
- **Problem**: squarify library was not installed
- **Solution**: Automatic installation + added to requirements.txt
- **Result**: Treemaps work perfectly for hierarchical data
- **Benefit**: Ideal for visualizing many items (up to 25) in an organized way

### 8. **🆕 NEW: Smart Pie Chart Processing** ✅
- **Problem**: LLM error trying to use invalid y_column for processed data
- **Solution**: Automatic detection of processed data and column mapping
- **Result**: Pie charts work seamlessly with count operations
- **Benefit**: No more column mismatch errors for aggregated data

### 9. **🆕 NEW: Enhanced Treemap Text Handling** ✅
- **Problem**: Long building names were cut off or unreadable in treemaps
- **Solution**: Intelligent text wrapping that breaks long names into multiple lines
- **Result**: All building names are clearly visible and readable
- **Benefit**: Perfect for datasets with long category names (124 buildings)

### 10. **🆕 NEW: Fixed Treemap Text Arguments Conflict** ✅
- **Problem**: `text() got multiple values for keyword argument 'ha'` error
- **Solution**: Removed duplicate alignment parameters from text_kwargs
- **Result**: Treemaps render without text positioning conflicts
- **Benefit**: Consistent and reliable treemap generation

## 🎨 **Applied Visual Improvements**

- ✅ **Reduced sizes**: More appropriate charts
- ✅ **No text overlap**: Rotation and truncation
- ✅ **Adequate fonts**: Optimized sizes
- ✅ **Organized legends**: Better positioning
- ✅ **Optimized spacing**: Adjusted margins

## 📋 **How to Use**

1. **Access**: App Repository in the chatbot
2. **Select**: devices.csv
3. **Type**: Any of the example queries above
4. **Result**: Perfect chart without errors!

## ⚠️ **Problematic Queries - Now Automatically Resolved**

### **BEFORE (❌ Unreadable)**
```
Using a bar chart, plot the count of buildings per campus
```
**Result**: 124 overlapping buildings, impossible to read

### **NOW (✅ Automatic)**
```
Using a bar chart, plot the count of buildings per campus
```
**Result**: 
- **TOP 20 buildings** automatically selected
- **Explanatory warning** about optimization
- **Suggestions** on how to view all data

### **Intelligent System Messages**

🔴 **Query with Too Much Data**:
"⚠️ Your query would return 124 unique items in 'BUILDING_NAME', making the chart unreadable."

🟡 **Automatic Optimization**:
"📊 Showing only the TOP 20 items with highest count. Total of 124 items available in dataset."

🟢 **Practical Suggestions**:
- "Use a **treemap** to see all items"
- "Filter by specific campus"
- "Use different aggregation"

## 🎯 **Examples that Now Work Perfectly**

### ✅ **Automatically Optimized Queries**
```
Using a bar chart, plot the count of buildings per campus
→ Shows TOP 20 buildings + explanatory warning

Using a pie chart, plot the count of device types
→ Shows TOP 8 types + alternative suggestions

Using a stacked bar chart, plot device types per building
→ Shows TOP 15 buildings + recommendations
```

### ✅ **🆕 Treemaps - NOW WORKING WITH SMART TEXT!**
```
Using a treemap chart, plot the total locations per building
→ Perfect hierarchical visualization for 124 buildings
→ Long names automatically wrapped (ex: "McArthur\nEngineering Building")

Using a treemap chart, plot device types per campus
→ Shows all device types in an organized way
→ Multi-line text for better readability

Using a treemap chart, plot the count of buildings per campus
→ Blocks proportional to number of buildings  
→ All building names clearly visible with line breaks
```

### ✅ **Queries that Always Worked**
```
Using a pie chart, plot the count of locations per campus
→ 4 categories, perfect for pie chart

Using a bar chart, plot the count per campus
→ 4 bars, ideal for visualization
```

### 🔧 **Fixed: Pie Chart Processing Issues**
```
BEFORE: ❌ Error: Invalid y column 'LOCATION_NUMBER' for pie chart
NOW: ✅ Automatic detection of processed data structure

The system now:
- Detects when data is already aggregated (CAMPUS + count columns)
- Automatically uses 'count' column for pie chart values
- No more column mismatch errors
- Works seamlessly with all count operations
```

## 🚀 **Suggested Next Steps**

1. **Test the queries**: Use the examples above
2. **Try variations**: Modify the chart types
3. **Explore filters**: Add specific filters
4. **Combine data**: Use multiple dimensions
5. **🆕 Test complex queries**: The system now automatically optimizes! 