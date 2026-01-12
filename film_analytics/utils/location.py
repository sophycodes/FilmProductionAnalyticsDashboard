import pandas as pd
import numpy as np
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc
import pandas as pd
import json
from utils.data_processing import process_movie_data  # Import your data processing function


def calculate_marketshare(df):
    """
    Calculate film market share by country from a DataFrame.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'production_countries' (list of dicts with 'name' key) 
        and 'revenue' columns.
    
    Returns:
    --------
    list of dict
        Sorted list of countries with their market share statistics:
        - 'country': Country name
        - 'films_produced': Number of films
        - 'count_share': Percentage of total films
        - 'revenue': Revenue in millions
        - 'revenue_share': Percentage of total revenue
        
    """
    
    num_rows = len(df)
    market_share = []
    country_counts = {}
    country_revenue = {}
    total_revenue = 0
    
    # check if column exists 
    if "production_countries" in df.columns and "revenue" in df.columns:
        # iterate through each row in the dataframe
        for idx, row in df.iterrows(): 
            # For the current row, extract value from the "production_countries" column
            countries = row["production_countries"]
            # For the current row, extract value from the "revenue" column
            revenue = row["revenue"]
            
            # Skip null values or zero revenue
            if not isinstance(countries, list) or pd.isna(revenue) or revenue <= 0:
                continue
            
            # Add to total revenue for percentage calculation later
            total_revenue += revenue
            
            # Calculate how much revenue to attribute to each country
            # (Dividing equally among production countries)
            if len(countries) > 0:
                country_revenue_share = revenue / len(countries)
                
                for country_dict in countries:
                    # Check that format is dictionary and name key exists
                    if isinstance(country_dict, dict) and "name" in country_dict:
                        # Store country name
                        country_name = country_dict["name"]
                        
                        # if already in dict update 
                        if country_name in country_counts:
                            country_counts[country_name] += 1
                            country_revenue[country_name] += country_revenue_share
                        # if not already in dict create instance 
                        else:
                            country_counts[country_name] = 1
                            country_revenue[country_name] = country_revenue_share
                            
        # Calculate market shares
        for country, count in country_counts.items():
            # Calculate count-based share
            count_share = (count / num_rows) * 100
            
            # Calculate revenue-based share
            revenue_share = 0
            if total_revenue > 0:  # Avoid division by zero
                revenue_share = (country_revenue[country] / total_revenue) * 100
            
            # Append to market share list
            market_share.append({
                "country": country,
                "films_produced": count,
                "count_share": round(count_share, 2),  # round down to 2 decimals
                "revenue": round(country_revenue[country] / 1000000, 2),  # In millions
                "revenue_share": round(revenue_share, 2)
            })
        
        # Sort in descending order by film count share
        market_share = sorted(market_share, key=lambda x: x['count_share'], reverse=True)
        
    
    return market_share
        
            
            

def create_location_heatmap(market_share_data):
    """
    Create a choropleth map showing film production by country
    
    Parameters:
    -----------
    market_share_data : list of dict
        List containing dictionaries with country, films_produced, revenue, etc.
        
    Returns:
    --------
    go.Choropleth
        Choropleth trace that can be added to a figure
    """
    # Convert list of dictionaries to more usable format
    df = pd.DataFrame(market_share_data)
    
    # Create the choropleth trace
    choropleth_trace = go.Choropleth(
        locations=df['country'],
        locationmode='country names',
        z=df['films_produced'],
        colorscale='Viridis',
        colorbar=dict(
            title="Number of Films",
            x=0.50,
            y=0.7,
            len=0.5
        ),
        hovertemplate='<b>%{location}</b><br>' + 
                      'Films Produced: %{z}<br>' +
                      'Revenue: $%{customdata[0]:,.1f} million<br>' +
                      'Market Share: %{customdata[1]}%<extra></extra>',
        # stack df['revenue'] and df['revenue_share'] column wise, results in 2D array where columns 1 is revenue and column 2 is revenue share
        customdata=np.stack((df['revenue'], df['revenue_share']), axis=-1)
    )
    
    return choropleth_trace


def create_market_share_pie(market_share_data, share_type='count_share', title="Market Share Distribution"):
    """
    Create a pie chart showing market share by country
    
    Parameters:
    -----------
    market_share_data : list of dict
        List containing dictionaries with country, films_produced, revenue, etc.
    share_type : str
        Type of share to display ('count_share' or 'revenue_share')
    title : str
        Title for the pie chart
        
    Returns:
    --------
    go.Pie
        Pie chart trace that can be added to a figure
    """
    # Convert to DataFrame and sort
    df = pd.DataFrame(market_share_data)
    df = df.sort_values(share_type, ascending=False)
    
    # Take top countries and group others
    top_countries = df.head(8)
    others = df.iloc[8:]
    
    if not others.empty:
        others_row = {
            'country': 'Others',
            'films_produced': others['films_produced'].sum(),
            'count_share': others['count_share'].sum(),
            'revenue': others['revenue'].sum(),
            'revenue_share': others['revenue_share'].sum()
        }
        
        # Append the "Others" category to the top countries
        top_countries = pd.concat([top_countries, pd.DataFrame([others_row])])
    
    # Determine which values to display based on share_type
    values = top_countries[share_type]
    labels = top_countries['country']
    
    # Create appropriate hover text based on share type
    if share_type == 'count_share':
        custom_data = top_countries[['films_produced']]
        hover_template = '<b>%{label}</b><br>Films: %{customdata[0]}<br>Share: %{value:.2f}%<extra></extra>'
    else:  # revenue_share
        custom_data = top_countries[['revenue']]
        hover_template = '<b>%{label}</b><br>Revenue: $%{customdata[0]:.1f}M<br>Share: %{value:.2f}%<extra></extra>'
    
    # Create pie chart
    pie_trace = go.Pie(
        labels=labels,
        values=values,
        hole=0.4,  # Creates a donut chart
        textposition='inside',  # Move text inside pie slices
        hovertemplate=hover_template,
        customdata=custom_data
    )
    
    return pie_trace




def location_production_dashboard(market_share_data):
    """
    Create a dashboard with two visualizations of film production data.
    
    Parameters:
    -----------
    market_share_data : list of dict
        Film market share data by country, with keys including 'country', 
        'count_share', and 'revenue_share'.
    
    Returns:
    --------
    plotly.graph_objects.Figure
        A figure with two plots:
        - A world map showing global film production distribution
        - A pie chart showing country market share by revenue
    """
    # Create a figure with only 2 subplots
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "choropleth"}, {"type": "domain"}]],
        subplot_titles=["Global Film Production Heatmap", "Country Market Share by Revenue"],
        horizontal_spacing=0.15,  # Increase spacing between visualizations (previously 0.1)
        column_widths=[0.6, 0.4]  # Adjust column widths to create more space
    )
    
    # Create a unified color palette
    unified_colorscale = px.colors.sequential.Viridis  # Use the same color scale for both visualizations
    
    # Add choropleth map with uniform colors
    choropleth_trace = create_location_heatmap(market_share_data)
    choropleth_trace.update(colorscale=unified_colorscale)
    fig.add_trace(choropleth_trace, row=1, col=1)
    
    # Add pie chart with matching colors
    pie_trace = create_market_share_pie(market_share_data, share_type='revenue_share')
    
    # Get the unique countries
    df = pd.DataFrame(market_share_data)
    countries = df.sort_values('revenue_share', ascending=False)['country'].tolist()
    
    # Create color mapping
    num_countries = min(len(countries), 9)  # Limit to match the number of colors in our palette
    color_mapping = {
        country: unified_colorscale[i * len(unified_colorscale) // num_countries] 
        for i, country in enumerate(countries[:num_countries])
    }
    
    # Set consistent colors for the pie chart
    pie_colors = [color_mapping.get(country, '#CCCCCC') for country in pie_trace.labels]
    pie_trace.update(marker=dict(colors=pie_colors))
    
    fig.add_trace(pie_trace, row=1, col=2)
    
    # Update layout with centered title and responsive sizing
    fig.update_layout(
        title={
            # 'text': "Global Film Production Analysis",
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        height=700,
        autosize=True,  # Changed from fixed width to autosize
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth'
        )
    )
    
    # Adjust pie position to create more balance
    fig.update_layout(
        grid=dict(columns=2, rows=1),
        grid_xgap=0.3  # Additional gap adjustment
    )
    
    return fig
