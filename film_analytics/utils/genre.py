from dash import Dash, dcc, html, Input, Output, State
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils.data_processing import process_movie_data

def get_unique_genres(df):
    """
    Extract all unique genres from the dataset.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing a 'genres' column with list data
        
    Returns:
    --------
    list
        Sorted list of unique genres
    """
    # Initialize an empty set to store unique genres
    unique_genres = set()
    
    if 'genres' in df.columns:
        # Iterate through each row in the DataFrame
        for _, row in df.iterrows():
            genres = row.get('genres', [])
            
            # Skip if genres is not a list or is empty
            if not isinstance(genres, list):
                continue
                
            # Add each genre to the set
            for genre in genres:
                if genre:  # Skip empty strings
                    unique_genres.add(genre)
        
    # Convert set to sorted list
    return sorted(list(unique_genres))


def prepare_genre_metrics(df, metric_field='vote_average'):
    """
    Prepare genre data with multiple metrics: rating, revenue, and budget
    
    Parameters:
    -----------
    df : pd.DataFrame
        Processed movie dataframe containing 'genres', 'vote_average', 
        'revenue', 'budget', etc.
    metric_field : str
        Field to use for metrics calculation
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with genre metrics for visualization
    """
    # Initialize list to store genre data
    genre_data_list = []
    
    unique_genres = get_unique_genres(df)
    
    # For each unique genre, calculate metrics
    for genre in unique_genres:
        # Filter movies with this genre
        genre_movies = df[df['genres'].apply(
            lambda x: genre in x if isinstance(x, list) else 
                     (genre in x if isinstance(x, str) else False)
        )]
        
        # Skip if no movies found for this genre
        if len(genre_movies) == 0:
            continue
        
        # Calculate metrics
        avg_rating = genre_movies['vote_average'].mean() if 'vote_average' in genre_movies.columns else np.nan
        title_count = len(genre_movies)
        
        # Calculate average revenue (in millions)
        avg_revenue = genre_movies['revenue'].mean() / 1000000 if 'revenue' in genre_movies.columns else np.nan
           
        # Calculate average revenue (in millions)
        avg_budget = genre_movies['budget'].mean() / 1000000 if 'budget' in genre_movies.columns else np.nan
 
        # Append data
        genre_data_list.append({
            'genre': genre,
            'vote_average': avg_rating,
            'revenue': avg_revenue,
            'budget': avg_budget,
            'title_count': title_count
        })
    
    # Convert to DataFrame
    genre_data = pd.DataFrame(genre_data_list)
    
    return genre_data


def create_genre_figure(df, sort_by='vote_average'):
    """
    Create a bar chart showing genre metrics.
    This function is designed to be used in the main dashboard app.
    """
    genre_data = prepare_genre_metrics(df, sort_by)
    
    if genre_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No genre data available. Check your dataset.",
            showarrow=False,
            font=dict(size=20)
        )
        return fig, None
        
    sorted_data = genre_data.sort_values(by=sort_by, ascending=True).reset_index(drop=True)
    sorted_data = sorted_data[~sorted_data['genre'].isin(['Tv', 'Movie'])]
    
    color_scale = {
        'vote_average': 'RdYlGn',
        'revenue': 'Greens',
        'budget': 'Blues'
    }.get(sort_by, 'RdYlGn')
    
    fig = px.bar(
        sorted_data,
        y='genre',
        x=sort_by,
        color=sort_by,
        color_continuous_scale=color_scale,
        labels={
            'genre': 'Genre',
            'vote_average': 'Average Rating (0-10)',
            'revenue': 'Average Revenue $',
            'budget': 'Average Budget $'
        },
        hover_data=['title_count'],
        text=sorted_data[sort_by].round(2)
    )
    
    # Update layout
    fig.update_layout(
        title=f"Movie Genres Ranked by {sort_by.title()}",
        xaxis_title=f"{sort_by.title()}",
        yaxis_title="Genre",
        height=700,
        template='plotly_white',
        margin=dict(l=200, r=50, t=100, b=50),
        coloraxis_colorbar=dict(
            title=sort_by.title()
        ),
        plot_bgcolor='#e5ecf6',  # Plotly's light blue background
        paper_bgcolor='#e5ecf6',
    )
    
     # Update y-axis grid with white lines
    fig.update_yaxes(
        showgrid=True,
        gridcolor='white',
        gridwidth=1
    )
    
    # Configure the x-axis
    fig.update_xaxes(
        showline=True,          
        linewidth=1,            
        linecolor='black',     
        mirror=True,            
        showgrid=True,  
        gridwidth=1,    
        gridcolor='white',     
        zeroline=True,     
        zerolinewidth=1,         
        zerolinecolor='black',   
        ticks="outside",         
        tickwidth=1,     
        tickcolor='black',    
        tickmode='auto',         
        ticklen=5               
    )
    
    # Configure the y-axis 
    fig.update_yaxes(
        showline=True,    
        linewidth=1,          
        linecolor='black',      
        mirror=True,             
        showgrid=True,           
        gridwidth=1,       
        gridcolor='white',       
        zeroline=True,         
        zerolinewidth=1,        
        zerolinecolor='black',   
        ticks="outside",         
        tickwidth=1,          
        tickcolor='black',      
        ticklen=5               
    )
    
    # Add formatting
    if sort_by in ['revenue', 'budget']:
        fig.update_xaxes(
            ticksuffix=" M",
            tickformat=".0f"
        )
    
    # Set hover and text templates
    text_template = '%{text:.1f}' if sort_by == 'vote_average' else '%{text:.0f}M'
    hover_format = {
        'vote_average': '<b>%{y}</b><br>Genre Rating: %{x:.1f}<br>Films: %{customdata[0]}<extra></extra>',
        'revenue': '<b>%{y}</b><br>Genre Revenue: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>',
        'budget': '<b>%{y}</b><br>Genre Budget: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>'
    }.get(sort_by)
    
    fig.update_traces(
        texttemplate=text_template,
        textposition='outside',
        hovertemplate=hover_format,
        customdata=sorted_data[['title_count']]
    )
    
    # Calculate top genres for insights
    top_genres = sorted_data.tail(3)
    
    # Return the figure and the top genres data for insights
    return fig, top_genres
