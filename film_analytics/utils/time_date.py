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


def calculate_runtime_genre(df):
    """
    Calculate average runtime by genre
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing 'genres' list column and 'runtime' column
        
    Returns:
    --------
    list
        List of dictionaries with genre stats
    """
    
    genre_runtime = []
    # Total runtime per genre
    genre_time_dict = {}
    # total number of movies per genre 
    genre_movie_counts = {}
    
    # loop over rows
    for _, row in df.iterrows():
        # Skip rows with missing runtime
        runtime = row.get('runtime')
        if pd.isna(runtime) or runtime <= 0:
            continue
            
        genres = row.get('genres', [])
        if not isinstance(genres, list):
            continue
            
        # access runtime and genre column 
        for genre in genres:
            # Add runtime to genre total
            if genre in genre_movie_counts:
                genre_movie_counts[genre] += 1
                genre_time_dict[genre] += runtime
            # create new instance
            else:
                genre_movie_counts[genre] = 1
                genre_time_dict[genre] = runtime
    
    # calculate average runtime per genre 
    for genre, total_time in genre_time_dict.items():
        genre_runtime.append({
            'genre': genre,
            'total_runtime': total_time,
            'movie_count': genre_movie_counts[genre],
            'avg_runtime': round(total_time / genre_movie_counts[genre], 2)
        })
    
    # Sort by total runtime (descending)
    genre_runtime = sorted(genre_runtime, key=lambda x: x['total_runtime'], reverse=True)
    
    return genre_runtime

def create_runtime_plot(
    df,
    genre_stats=None,
    config: dict = {
        "width": 1200,
        "height": 800,
        "time_range": (1920, 2025),
        "bin_size": "1Y",
        "title": "Movies and Series Released Over Time"
    }
):
    """
    Create an interactive line plot showing average runtime over years with genre filter
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing 'runtime', 'release_year' and 'genres' columns
    config : dict
        Configuration parameters for the plot
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Interactive line plot
    """
    # Extract parameters
    width = config.get("width", 1200)
    height = config.get("height", 600)
    start_year = config.get("time_range", (1900, 2024))[0]
    end_year = config.get("time_range", (1900, 2024))[1]
    main_title = config.get("title", "Average Movie Runtime Over Time")
    
    # Adjust the range values to be integers
    if isinstance(start_year, str):
        start_year = int(start_year)
    if isinstance(end_year, str):
        end_year = int(end_year)
    
    # Check if required columns exist
    if "release_year" not in df.columns or "runtime" not in df.columns or "genres" not in df.columns:
        raise ValueError("DataFrame must contain 'release_year', 'runtime', and 'genres' columns")
    
    # Filter data by year range
    filtered_df = df[(df['release_year'] >= start_year) & (df['release_year'] <= end_year)]
    
    # Get all unique genres from pre-calculated genre stats or calculate them
    if genre_stats is None:
        genre_stats = calculate_runtime_genre(df)
    # Add "All Genres" option
    all_genres = ['All Genres'] + [genre_data['genre'] for genre_data in genre_stats]
    
    # Create figure
    fig = go.Figure()
    
    # Calculate average runtime by year for all movies
    runtime_by_year = filtered_df.groupby('release_year')['runtime'].mean().reset_index()
    
    # Add trace for all genres
    fig.add_trace(
        go.Scatter(
            x=runtime_by_year['release_year'],
            y=runtime_by_year['runtime'],
            mode='lines+markers',
            name='All Genres',
            line=dict(color='black', width=2),
            visible=True
        )
    )
    
    # Add trace for each genre
    for i, genre in enumerate(all_genres[1:]):  # Skip 'All Genres'
        # Get movies with this genre
        genre_movies = filtered_df[filtered_df['genres'].apply(lambda x: genre in x if isinstance(x, list) else False)]
        
        # Calculate average runtime by year for this genre
        if not genre_movies.empty:
            genre_runtime_by_year = genre_movies.groupby('release_year')['runtime'].mean().reset_index()
            
            fig.add_trace(
                go.Scatter(
                    x=genre_runtime_by_year['release_year'],
                    y=genre_runtime_by_year['runtime'],
                    mode='lines+markers',
                    name=genre,
                    visible=False  # Initially hidden
                )
            )
    
    # Create dropdown menu
    buttons = []
    
    # Button for All Genres
    buttons.append(
        dict(
            method='update',
            label='All Genres',
            args=[{'visible': [True] + [False] * (len(all_genres) - 1)},
                  {'title': f'Average Runtime Over Time: All Genres'}]
        )
    )
    
    # Button for each genre
    for i, genre in enumerate(all_genres[1:], 1):
        # Create visibility list (only show the selected genre)
        visibility = [False] * len(all_genres)
        visibility[i] = True
        
        buttons.append(
            dict(
                method='update',
                label=genre,
                args=[{'visible': visibility},
                      {'title': f'Average Runtime Over Time: {genre}'}]
            )
        )
    
    # Add dropdown menu to figure
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.15,
                yanchor="top",
                bgcolor="white",     # White background for dropdown
                bordercolor="gray",  # Gray border like in the heatmap
                borderwidth=1      
            )
        ],
        
        annotations=[
            dict(
                text="Select Genre:",
                x=0.1,
                y=1.18,  # Position slightly above the dropdown
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=12)
            )
        ]
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': main_title,
            'x': 0.5,
            'xanchor': 'center',
            'y': 0.95  # Move title down slightly
        },
        width=width,
        height=height-50,
        xaxis_title='Year',
        yaxis_title='Average Runtime (minutes)',
        hovermode='closest',
        template='plotly_white',
        plot_bgcolor='#e5ecf6',  # This is the standard Plotly blue background
        paper_bgcolor='white',   # Remove the # before 'white'
        xaxis=dict(
            showgrid=True,       # Show grid lines
            gridcolor='white',   # White grid lines
            gridwidth=1.5,       # Make grid lines thicker
            linecolor='black',   # Black axis lines
            linewidth=1.5,       # Make axis lines thicker
            mirror=True          # Show axis lines on all sides
        ),
        yaxis=dict(
            showgrid=True,       # Show grid lines
            gridcolor='white',   # White grid lines
            gridwidth=1.5,       # Make grid lines thicker
            linecolor='black',   # Black axis lines
            linewidth=1.5,       # Make axis lines thicker
            mirror=True          # Show axis lines on all sides
        ),
        margin=dict(l=80, r=80, t=100, b=80)  # Adjust margins to match heatmap
    )
    
    
    # Add reference line for 2-hour mark
    fig.add_shape(
        type="line",
        x0=start_year,
        x1=end_year,
        y0=120,
        y1=120,
        line=dict(
            color="red",
            width=1,
            dash="dash",
        ),
        name="2 Hours"
    )
    
    # Add annotations for context
    fig.add_annotation(
        x=start_year + 5,
        y=120,
        text="2 Hours",
        showarrow=False,
        yshift=10,
        font=dict(color="red")
    )
    
    return fig