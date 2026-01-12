import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

def prepare_release_date_data(df):
    """
    Prepare movie release date data for heatmap visualization.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing movie data with release_date and revenue columns
        
    Returns:
    --------
    tuple
        (aggregated_data, day_names, month_names, pivots) where:
        - aggregated_data: processed DataFrame grouped by month and day of week
        - day_names: list of day names
        - month_names: list of month names
        - pivots: dict containing pivot tables for revenue, profit, roi, and count
    """
    # Skip processing if required columns don't exist
    if 'release_date' not in df.columns or 'revenue' not in df.columns:
        return None, None, None, None
    
    # Make a copy to avoid modifying the original dataframe
    df_copy = df.copy()
    
    # Clean up the data - make sure release_date is in datetime format
    df_copy['release_date'] = pd.to_datetime(df_copy['release_date'], errors='coerce')
    
    # Filter out rows with invalid dates or zero revenue
    df_copy = df_copy.dropna(subset=['release_date', 'revenue'])
    df_copy = df_copy[df_copy['revenue'] > 0]
    
    # Extract day of week and month from release date
    df_copy['day_of_week'] = df_copy['release_date'].dt.dayofweek  # 0 = Monday, 6 = Sunday
    df_copy['month'] = df_copy['release_date'].dt.month  # 1-12
    
    # Adjust to make Sunday = 0, Saturday = 6 for consistency with standard
    df_copy['day_of_week'] = (df_copy['day_of_week'] + 1) % 7
    
    # Create aggregation dataframe
    aggregated = df_copy.groupby(['month', 'day_of_week']).agg({
        'revenue': 'mean',
        'profit': 'mean',
        'roi': 'mean',
        'title': 'count'  # counting titles gives us the number of movies
    }).reset_index()
    
    # Rename columns for clarity
    aggregated.rename(columns={'title': 'count'}, inplace=True)
    
    # Create lists for our heatmap
    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
    
    # Create pivot tables for each metric
    pivot_revenue = pd.pivot_table(
        aggregated, 
        values='revenue', 
        index='month', 
        columns='day_of_week'
    )
    
    pivot_profit = pd.pivot_table(
        aggregated, 
        values='profit', 
        index='month', 
        columns='day_of_week'
    )
    
    pivot_roi = pd.pivot_table(
        aggregated, 
        values='roi', 
        index='month', 
        columns='day_of_week'
    )
    
    pivot_count = pd.pivot_table(
        aggregated, 
        values='count', 
        index='month', 
        columns='day_of_week'
    )
    
    # Package pivots in a dictionary
    pivots = {
        'revenue': pivot_revenue,
        'profit': pivot_profit,
        'roi': pivot_roi,
        'count': pivot_count
    }
    
    return aggregated, day_names, month_names, pivots

def create_date_heatmap(df):
    """
    Create a heatmap visualization of movie metrics by release date (month and day of week)
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing movie data with release_date and revenue columns
        
    Returns:
    --------
    go.Figure
        Plotly figure with interactive heatmap visualization
    """
    # Get prepared data
    aggregated, day_names, month_names, pivots = prepare_release_date_data(df)
    
    # If preparation failed, return an empty figure with a message
    if aggregated is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Required data not available (release_date, revenue)",
            showarrow=False,
            font=dict(size=14)
        )
        fig.update_layout(
            title="Movie Release Timing Heatmap",
            height=700
        )
        return fig
    
    # Get pivot tables
    pivot_revenue = pivots['revenue']
    pivot_profit = pivots['profit']
    pivot_roi = pivots['roi']
    pivot_count = pivots['count']
    
    # Create hover text for each metric
    hover_texts = {}
    for metric_name, pivot in pivots.items():
        hover_text = []
        for month in range(1, 13):
            hover_row = []
            for day in range(7):
                try:
                    value = pivot.loc[month, day]
                    count = pivot_count.loc[month, day]
                    
                    # Format based on metric type
                    if metric_name == 'revenue' or metric_name == 'profit':
                        value_text = f"Avg {metric_name.title()}: ${value/1000000:.2f}M"
                    elif metric_name == 'roi':
                        value_text = f"Avg ROI: {value:.2f}%"
                    else:  # count
                        value_text = f"Movies: {int(value)}"
                        
                    hover_row.append(
                        f"Month: {month_names[month-1]}<br>" +
                        f"Day: {day_names[day]}<br>" +
                        f"{value_text}<br>" +
                        (f"Movies: {int(count)}" if metric_name != 'count' else "")
                    )
                except:
                    hover_row.append("No data")
            hover_text.append(hover_row)
        hover_texts[metric_name] = hover_text
    
    # Create a combined figure with dropdown menu
    fig = go.Figure()
    
    # Define color scales for different metrics
    color_scales = {
        'revenue': 'Viridis',
        'profit': 'RdBu',
        'roi': 'RdBu',
        'count': 'YlOrRd'
    }
    
    # Define titles for color bars
    colorbar_titles = {
        'revenue': 'Average Revenue (USD)',
        'profit': 'Average Profit (USD)',
        'roi': 'ROI (%)',
        'count': 'Movie Count'
    }
    
    # Add traces for each metric
    for i, (metric_name, pivot) in enumerate(pivots.items()):
        fig.add_trace(
            go.Heatmap(
                z=pivot.values,
                x=day_names,
                y=month_names,
                hoverongaps=False,
                text=hover_texts[metric_name],
                hoverinfo='text',
                colorscale=color_scales[metric_name],
                colorbar=dict(
                    title=colorbar_titles[metric_name],
                    x=1.05,  # Move colorbar to the right
                    xpad=20
                ),
                visible=(i == 0)  # Only first trace (revenue) is visible initially
            )
        )
    
    # Create update menu buttons
    buttons = []
    metrics = list(pivots.keys())
    titles = {
        'revenue': "Movie Box Office Performance by Release Date",
        'profit': "Movie Profit by Release Date",
        'roi': "Movie ROI by Release Date",
        'count': "Number of Movies by Release Date"
    }
    
    for i, metric in enumerate(metrics):
        # Create visibility list (only show the selected metric)
        visibility = [j == i for j in range(len(metrics))]
        
        buttons.append(
            dict(
                label=metric.title(),
                method="update",
                args=[{"visible": visibility},
                     {"title": titles[metric]}]
            )
        )
    
    # Updated layout with better positioning of dropdown menu
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                type="dropdown",
                direction="down",
                x=0.1,  # Position dropdown on the left side
                y=1.15,  # Position above the plot
                xanchor="left",
                yanchor="top",
                pad={"r": 10, "t": 10},
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1
            ),
        ],
        title={
            'text': 'Movie Release Timing Heatmap',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Day of Week',
        yaxis_title='Month',
        height=700,
        margin=dict(l=80, r=120, t=120, b=80),  # Increased right and top margins
        xaxis=dict(tickangle=-45),
        annotations=[
            dict(
                text="Select Metric:",
                x=0.1,
                y=1.2,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=12)
            )
        ]
    )
    
    return fig

# This block only runs when the file is executed directly, not when imported
if __name__ == "__main__":
    # Load the data
    try:
        df = pd.read_csv('processed_movie_data.csv')
        print(f"Loaded dataset with {len(df)} records")
        
        # Create the heatmap
        fig = create_date_heatmap(df)
        
        # Show the figure in a browser
        fig.show()
        
        print("Heatmap created successfully!")
    except Exception as e:
        print(f"Error: {e}")