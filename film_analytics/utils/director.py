from dash import Dash, dcc, html, Input, Output, State
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import math
import random
import networkx as nx
from collections import Counter
import os  # For path operations

from utils.data_processing import process_movie_data



def get_unique_directors(df):
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
    unique_directors = set()
    
    if 'director' in df.columns:
        # Iterate through each row in the DataFrame
        for _, row in df.iterrows():
            director = row.get('director', [])
            
            # Skip if director if it is not a str or is empty
            if not isinstance(director, str):
                continue
            
            # Add the director to the set
            unique_directors.add(director)  # This line was missing

    # Convert set to sorted list
    return sorted(list(unique_directors))


    
def prepare_director_metrics(df, metric_field='vote_average'):
    """
    Prepare director data with multiple metrics: rating and revenue
    
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
    director_data_list = []
    
    unique_directors = get_unique_directors(df)
    
    # For each unique genre, calculate metrics
    for director in unique_directors:
        # Filter movies with this genre
        director_movies = df[df['director'].apply(
            lambda x: director in x if isinstance(x, str) else False)
        ]
        
        # Skip if no movies found for this genre
        if len(director_movies) == 0:
            continue
        
        # Calculate metrics
        avg_rating = director_movies['vote_average'].mean() if 'vote_average' in director_movies.columns else np.nan
        title_count = len(director_movies)
        
        # Calculate average revenue (in millions)
        avg_revenue = director_movies['revenue'].mean() / 1000000 if 'revenue' in director_movies.columns else np.nan
           
        # Calculate average revenue (in millions)
        avg_budget = director_movies['budget'].mean() / 1000000 if 'budget' in director_movies.columns else np.nan
 
        # Append data
        director_data_list.append({
            'director': director,
            'vote_average': avg_rating,
            'revenue': avg_revenue,
            'budget': avg_budget,
            'title_count': title_count
        })
    
    # Convert to DataFrame
    director_data = pd.DataFrame(director_data_list)
    
    return director_data


def create_director_dashboard(df_clean):
    """
    Create and launch a Dash dashboard for director analysis
    
    Parameters:
    -----------
    df_clean : pd.DataFrame
        Cleaned movie DataFrame
    """
    # Create the Dash app
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    
    # App layout
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Director Analysis Dashboard", className="text-center my-4")
            ], width=12)
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Label("Sort by:"),
                dcc.Dropdown(
                    id='sort-dropdown',
                    options=[
                        {'label': 'Average Rating', 'value': 'vote_average'},
                        {'label': 'Average Revenue $', 'value': 'revenue'},
                        {'label': 'Average Budget $', 'value': 'budget'}
                    ],
                    value='vote_average',
                    clearable=False
                )
            ], width=3),
            
            dbc.Col([
                dcc.Loading(
                    id="loading-graph",
                    type="default",
                    children=dcc.Graph(id='director-bar-chart', style={'height': '700px'})
                )
            ], width=9)
        ], className="my-4"),

    ], fluid=True)
    
    # Store DataFrame as a global variable to be accessed in callback
    app.df_clean = df_clean
    
    # Callback to update the graph based on dropdown selection
    @app.callback(
        Output('director-bar-chart', 'figure'),
        [Input('sort-dropdown', 'value')]
    )
    def update_graph(sort_by):
        # Use the cleaned DataFrame stored in app
        director_data = prepare_director_metrics(app.df_clean, sort_by)
        
        # Check if director_data is empty
        if director_data.empty:
            # Create a default figure with a message
            fig = go.Figure()
            fig.add_annotation(
                text="No director data available. Check your dataset.",
                showarrow=False,
                font=dict(size=20)
            )
            
            # Create an empty insights panel
            insights = html.Div("No data available")
            
            return fig
            
        # Sort data in descending order (highest values first)
        sorted_data = director_data.sort_values(by=sort_by, ascending=False).reset_index(drop=True)
        
        # Get only the top 10 directors
        sorted_data = sorted_data.head(20)
        
        # Re-sort for visualization (to have highest values at the top when displayed)
        sorted_data = sorted_data.sort_values(by=sort_by, ascending=True)
        
        # Create color scale based on selected metric
        if sort_by == 'vote_average':
            color_scale = 'RdYlGn'  # Red to Green
        elif sort_by == 'revenue':
            color_scale = 'Greens'  # Green scale for revenue
        else:  # Budget
            color_scale = 'Blues'  # Blue scale for budget
        
        # Create bar chart
        fig = px.bar(
            sorted_data,
            y='director',
            x=sort_by,
            color=sort_by,
            color_continuous_scale=color_scale,
            labels={
                'director': 'Director',
                'vote_average': 'Average Rating (0-10)',
                'revenue': 'Average Revenue $',
                'budget': 'Average Budget $'
            },
            hover_data=['title_count'],
            text=sorted_data[sort_by].round(2)
        )
        

        # Update layout
        fig.update_layout(
            title=f"Top 20 Directors Ranked by {sort_by.title()}",
            xaxis_title=f"{sort_by.title()}",
            yaxis_title="Director",
            height=700,
            template='plotly_white',
            margin=dict(l=200, r=50, t=100, b=50),
            coloraxis_colorbar=dict(
                title=sort_by.title()
            )
        )
        
        
        # Add "M" suffix to x-axis tick labels for revenue and budget
        if sort_by in ['revenue', 'budget']:
            fig.update_xaxes(
                ticksuffix=" M",
                tickformat=".0f"  # Format to 1 decimal place
            )
                
        # Conditional formatting based on selected metric
        if sort_by == 'vote_average':
            hover_format = '<b>%{y}</b><br>Director Rating: %{x:.1f}<br>Films: %{customdata[0]}<extra></extra>'
        elif sort_by == 'revenue':
            hover_format = '<b>%{y}</b><br>Director Revenue: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>'
        else:  # Budget
            hover_format = '<b>%{y}</b><br>Director Budget: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>'

        # Format text differently based on metric
        if sort_by == 'vote_average':
            text_template = '%{text:.1f}'
        else:  # For revenue and budget
            text_template = '%{text:.0f}M'
        

        # Update the traces with the conditional text template
        fig.update_traces(
            texttemplate=text_template,  # Use the conditional template
            textposition='outside',
            hovertemplate=hover_format,
            customdata=sorted_data[['title_count']]
        )
        
        return fig

    # Run the server
    app.run(debug=True)
    
    
    
def create_director_figure(df, sort_by='vote_average'):
    """Create a bar chart showing director metrics."""
    director_data = prepare_director_metrics(df, sort_by)
    
    if director_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No director data available. Check your dataset.",
            showarrow=False,
            font=dict(size=20)
        )
        return fig
        
    # Sort data in descending order (highest values first)
    sorted_data = director_data.sort_values(by=sort_by, ascending=False).reset_index(drop=True)
    
    # Get only the top 20 directors
    sorted_data = sorted_data.head(20)
    
    # Re-sort for visualization (to have highest values at the top when displayed)
    sorted_data = sorted_data.sort_values(by=sort_by, ascending=True)
    
    # Create color scale based on selected metric
    color_scale = {
        'vote_average': 'RdYlGn',
        'revenue': 'Greens',
        'budget': 'Blues'
    }.get(sort_by, 'RdYlGn')
    
    # Create bar chart
    fig = px.bar(
        sorted_data,
        y='director',
        x=sort_by,
        color=sort_by,
        color_continuous_scale=color_scale,
        labels={
            'director': 'Director',
            'vote_average': 'Average Rating (0-10)',
            'revenue': 'Average Revenue $',
            'budget': 'Average Budget $'
        },
        hover_data=['title_count'],
        text=sorted_data[sort_by].round(2)
    )
    
    # Update layout
    fig.update_layout(
        title=f"Top 20 Directors Ranked by {sort_by.title()}",
        xaxis_title=f"{sort_by.title()}",
        yaxis_title="Director",
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
    
    # Add "M" suffix to x-axis tick labels for revenue and budget
    if sort_by in ['revenue', 'budget']:
        fig.update_xaxes(
            ticksuffix=" M",
            tickformat=".0f"  # Format to 1 decimal place
        )
    
    # Format text and hover templates
    text_template = '%{text:.1f}' if sort_by == 'vote_average' else '%{text:.0f}M'
    hover_format = {
        'vote_average': '<b>%{y}</b><br>Director Rating: %{x:.1f}<br>Films: %{customdata[0]}<extra></extra>',
        'revenue': '<b>%{y}</b><br>Director Revenue: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>',
        'budget': '<b>%{y}</b><br>Director Budget: %{x:.1f} M<br>Films: %{customdata[0]}<extra></extra>'
    }.get(sort_by)
    
    fig.update_traces(
        texttemplate=text_template,
        textposition='outside',
        hovertemplate=hover_format,
        customdata=sorted_data[['title_count']]
    )
    
    return fig

def director_company_network(df, min_edge_weight=1, max_directors=10, max_companies=10):
    """Create network data for visualization"""
    # Count frequencies
    director_counts = Counter()
    company_counts = Counter()
    # Count collaborations
    collaborations = {}
    
    for _, row in df.iterrows():
        director = row.get("director")
        
        # check if director is empty container, Nan, or empty string if so skip row
        if not director or pd.isna(director) or director == "":
            continue
        
        # count this director 
        director_counts[director] += 1
        
        # Process production companies
        companies = row.get('production_companies', [])
        
        # Skip if empty or not a list
        if not isinstance(companies, list) or len(companies) == 0:
            continue
            
        # Extract company names and count them
        for company_dict in companies:
            company_name = None
            
            # Handle different formats of production_companies
            if isinstance(company_dict, dict) and 'name' in company_dict:
                company_name = company_dict['name']
            elif isinstance(company_dict, str):
                company_name = company_dict
                
            if company_name:
                # Count this company
                company_counts[company_name] += 1
                
                # Count this collaboration
                pair = (director, company_name)
                if pair in collaborations:
                    collaborations[pair] += 1
                else:
                    collaborations[pair] = 1
                    
    # Get top directors and companies
    top_directors = [d for d, _ in director_counts.most_common(max_directors)]
    top_companies = [c for c, _ in company_counts.most_common(max_companies)]
    
    # Create graph
    G = nx.Graph()
    
    # Add nodes
    for director in top_directors:
        G.add_node(director, type='director', count=director_counts[director])
    
    for company in top_companies:
        G.add_node(company, type='company', count=company_counts[company])
    
    # Add edges with minimum weight
    for (director, company), weight in collaborations.items():
        if director in top_directors and company in top_companies and weight >= min_edge_weight:
            G.add_edge(director, company, weight=weight)
            
    # Calculate node positions using a layout algorithm
    # First, identify directors and companies
    directors = {n for n, attr in G.nodes(data=True) if attr.get('type') == 'director'}
    companies = set(G.nodes()) - directors
    
    # Create positions - companies in the center, directors around
    pos = {}
    
    # Center point for the visualization
    center_x, center_y = 0, 0
    
    # Place companies in the center, in a smaller circle
    inner_radius = 1.5  # Smaller radius to keep companies clustered in center
    company_count = len(companies)
    if company_count > 0:  # Avoid division by zero
        # For a single company, place exactly at center
        if company_count == 1:
            pos[list(companies)[0]] = (center_x, center_y)
        else:
            for i, company in enumerate(companies):
                angle = 2 * math.pi * i / company_count
                pos[company] = (center_x + inner_radius * math.cos(angle), 
                               center_y + inner_radius * math.sin(angle))
    
    # Directors in the outer circle
    outer_radius = 5  # Increased radius for better separation
    director_count = len(directors)
    if director_count > 0:  # Avoid division by zero
        for i, director in enumerate(directors):
            angle = 2 * math.pi * i / director_count
            pos[director] = (center_x + outer_radius * math.cos(angle), 
                            center_y + outer_radius * math.sin(angle))
    
    # Add some random jitter to make it look more natural
    for node in pos:
        x, y = pos[node]
        pos[node] = (x + random.uniform(-0.2, 0.2), y + random.uniform(-0.2, 0.2))
    
    # Return network data needed for visualization
    return {
        'G': G, 
        'pos': pos, 
        'directors': directors, 
        'companies': companies,
        'collaborations': collaborations,
        'top_directors': top_directors,
        'top_companies': top_companies
    }

def create_network_figure(network_data, highlighted_node=None):
    """Create the network figure with optional node highlighting"""
    G = network_data['G']
    pos = network_data['pos']
    directors = network_data['directors']
    companies = network_data['companies']
    
    # Prepare edge traces
    normal_edges_x = []
    normal_edges_y = []
    highlighted_edges_x = []
    highlighted_edges_y = []
    
    # Process edges
    for edge in G.edges():
        node1, node2 = edge
        x0, y0 = pos[node1]
        x1, y1 = pos[node2]
        
        # If this edge is connected to the highlighted node, add to highlighted trace
        if highlighted_node and (node1 == highlighted_node or node2 == highlighted_node):
            highlighted_edges_x.extend([x0, x1, None])
            highlighted_edges_y.extend([y0, y1, None])
        else:
            normal_edges_x.extend([x0, x1, None])
            normal_edges_y.extend([y0, y1, None])
    
    # Create normal edge trace
    edge_trace = go.Scatter(
        x=normal_edges_x, 
        y=normal_edges_y,
        line=dict(width=1.5, color='rgba(150,150,150,0.6)'),
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    # Create highlighted edge trace
    highlighted_edge_trace = go.Scatter(
        x=highlighted_edges_x, 
        y=highlighted_edges_y,
        line=dict(width=3, color='rgba(255,0,0,0.8)'),  # Thicker red lines for highlighted edges
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    # Prepare node data
    director_x = []
    director_y = []
    director_sizes = []
    director_text = []
    director_hover = []
    director_ids = []
    
    company_x = []
    company_y = []
    company_sizes = []
    company_text = []
    company_hover = []
    company_ids = []
    
    # Process nodes
    for node in G.nodes():
        x, y = pos[node]
        node_type = G.nodes[node]['type']
        count = G.nodes[node]['count']
        neighbors = list(G.neighbors(node))
        
        if node_type == 'director':
            director_x.append(x)
            director_y.append(y)
            director_sizes.append(count * 0.5 + 15)
            director_text.append(node)
            director_hover.append(f"<b>{node}</b><br>Movies directed: {count}<br>Collaborations: {len(neighbors)}")
            director_ids.append(node)
        else:  # company node
            company_x.append(x)
            company_y.append(y)
            company_sizes.append(count * 0.4 + 15)
            company_text.append(node)
            company_hover.append(f"<b>{node}</b><br>Movies produced: {count}<br>Directors worked with: {len(neighbors)}")
            company_ids.append(node)
    
    # Create director trace
    director_trace = go.Scatter(
        x=director_x,
        y=director_y,
        mode='markers+text',
        marker=dict(
            size=director_sizes,
            color=['#ff0000' if d_id == highlighted_node else '#e74c3c' for d_id in director_ids],  # Highlight if selected
            line=dict(width=1.5, color='#444'),
            symbol='circle'
        ),
        text=director_text,
        textposition="middle right",
        textfont=dict(size=11, color='#111111'),
        hoverinfo='text',
        hovertext=director_hover,
        name='Directors',
        customdata=director_ids
    )
    
    # Create company trace
    company_trace = go.Scatter(
        x=company_x,
        y=company_y,
        mode='markers+text',
        marker=dict(
            size=company_sizes,
            color=['#ffff00' if c_id == highlighted_node else '#f1c40f' for c_id in company_ids],  # Highlight if selected
            line=dict(width=1.5, color='#444'),
            symbol='circle'  # Circles for companies
        ),
        text=company_text,
        textposition="middle left",
        textfont=dict(size=11, color='#111111'),
        hoverinfo='text',
        hovertext=company_hover,
        name='Production Companies',
        customdata=company_ids
    )
    
    # Create analysis data for the sidebar
    director_collab_count = {director: len(list(G.neighbors(director))) for director in G.nodes() if G.nodes[director]['type'] == 'director'}
    company_collab_count = {company: len(list(G.neighbors(company))) for company in G.nodes() if G.nodes[company]['type'] == 'company'}
    
    top_directors_by_collab = sorted(director_collab_count.items(), key=lambda x: x[1], reverse=True)[:5]
    top_companies_by_collab = sorted(company_collab_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Find strong collaborations
    collaborations = network_data['collaborations']
    top_directors = network_data['top_directors']
    top_companies = network_data['top_companies']
    
    strong_collabs = []
    for (director, company), weight in collaborations.items():
        if director in top_directors and company in top_companies and weight >= 2:
            strong_collabs.append((director, company, weight))
    
    strong_collabs = sorted(strong_collabs, key=lambda x: x[2], reverse=True)[:10]
    
    # Create the figure
    fig = go.Figure(data=[edge_trace, highlighted_edge_trace, director_trace, company_trace],
                 layout=go.Layout(
                    title={
                        'text': 'Director-Production Company Network', 
                        'font': {'size': 24, 'color': '#111111'}
                    },
                    showlegend=True,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=60),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        font=dict(color='#111111')
                    ),
                    annotations=[
                        dict(
                            text="Hover over nodes to highlight connections",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            font=dict(color='#111111')
                        )
                    ],
                    paper_bgcolor='#e8f0f9',  # Light grey-blue background
                    plot_bgcolor='#e8f0f9'    # Light grey-blue background
                )
            )
    
    # Add analysis text
    analysis_text = "<b>Network Analysis</b><br><br>"
    analysis_text += "<b>Most Connected Directors:</b><br>" + "<br>".join([f"{d}: {n} companies" for d, n in top_directors_by_collab]) + "<br><br>"
    analysis_text += "<b>Most Connected Studios:</b><br>" + "<br>".join([f"{c}: {n} directors" for c, n in top_companies_by_collab]) + "<br><br>"
    
    if strong_collabs:
        analysis_text += "<b>Strongest Collaborations:</b><br>" + "<br>".join([f"{d} & {c}: {w} films" for d, c, w in strong_collabs[:5]])
    
    fig.add_annotation(
        x=1.4,
        y=0.5,
        xref="paper",
        yref="paper",
        text=analysis_text,
        showarrow=False,
        font=dict(size=12, color="#111111"),
        align="left",
        bordercolor="#2980b9",
        borderwidth=1.5,
        borderpad=8,
        bgcolor="rgba(236, 240, 241, 0.9)",
        opacity=0.9
    )
    
    # Add figure size settings
    fig.update_layout(
        autosize=False,
        width=1100,
        height=700
    )
    
    return fig

def create_enhanced_network_figure(network_data, highlighted_node=None):
    """Create an aesthetically enhanced network figure with a blue-green color palette"""
    G = network_data['G']
    pos = network_data['pos']
    directors = network_data['directors']
    companies = network_data['companies']
    
    # Prepare edge traces
    normal_edges_x = []
    normal_edges_y = []
    highlighted_edges_x = []
    highlighted_edges_y = []
    
    # Process edges
    for edge in G.edges():
        node1, node2 = edge
        x0, y0 = pos[node1]
        x1, y1 = pos[node2]
        
        # If this edge is connected to the highlighted node, add to highlighted trace
        if highlighted_node and (node1 == highlighted_node or node2 == highlighted_node):
            highlighted_edges_x.extend([x0, x1, None])
            highlighted_edges_y.extend([y0, y1, None])
        else:
            normal_edges_x.extend([x0, x1, None])
            normal_edges_y.extend([y0, y1, None])
    
    # Create normal edge trace - softer colors
    edge_trace = go.Scatter(
        x=normal_edges_x, 
        y=normal_edges_y,
        line=dict(width=1.2, color='rgba(180,180,180,0.4)'),  # Lighter for better aesthetics
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    # Create highlighted edge trace - using teal for highlighted edges
    highlighted_edge_trace = go.Scatter(
        x=highlighted_edges_x, 
        y=highlighted_edges_y,
        line=dict(width=3, color='rgba(0,128,128,0.85)'),  # Teal color for highlighting
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    # Prepare node data
    director_x = []
    director_y = []
    director_sizes = []
    director_text = []
    director_hover = []
    director_ids = []
    
    company_x = []
    company_y = []
    company_sizes = []
    company_text = []
    company_hover = []
    company_ids = []
    
    # Process nodes
    for node in G.nodes():
        x, y = pos[node]
        node_type = G.nodes[node]['type']
        count = G.nodes[node]['count']
        neighbors = list(G.neighbors(node))
        
        if node_type == 'director':
            director_x.append(x)
            director_y.append(y)
            director_sizes.append(count * 0.5 + 20)  # Slightly larger
            director_text.append(node)
            director_hover.append(f"<b>{node}</b><br>Movies directed: {count}<br>Collaborations: {len(neighbors)}")
            director_ids.append(node)
        else:  # company node
            company_x.append(x)
            company_y.append(y)
            company_sizes.append(count * 0.4 + 18)  # Slightly larger
            company_text.append(node)
            company_hover.append(f"<b>{node}</b><br>Movies produced: {count}<br>Directors worked with: {len(neighbors)}")
            company_ids.append(node)
    
    # Create director trace - blue tones
    director_trace = go.Scatter(
        x=director_x,
        y=director_y,
        mode='markers+text',
        marker=dict(
            size=director_sizes,
            color=['#1a5276' if d_id == highlighted_node else '#2980b9' for d_id in director_ids],  # Dark blue/highlighted, medium blue/normal
            line=dict(width=2, color='white'),  # White border for better contrast
            opacity=0.85,  # Slight transparency
            symbol='circle',
            gradient=dict(  # Add gradient effect
                type='radial',
                color='white'
            )
        ),
        text=director_text,
        textposition="middle right",
        textfont=dict(
            family="Arial, sans-serif",
            size=12, 
            color='#222222'
        ),
        hoverinfo='text',
        hovertext=director_hover,
        name='Directors',
        customdata=director_ids
    )
    
    # Create company trace - green tones
    company_trace = go.Scatter(
        x=company_x,
        y=company_y,
        mode='markers+text',
        marker=dict(
            size=company_sizes,
            color=['#006400' if c_id == highlighted_node else '#16a085' for c_id in company_ids],  # Dark green/highlighted, teal/normal
            line=dict(width=2, color='white'),  # White border
            opacity=0.85,  # Slight transparency
            symbol='diamond',  # Different shape for companies
            gradient=dict(  # Add gradient effect
                type='radial',
                color='white'
            )
        ),
        text=company_text,
        textposition="middle left",
        textfont=dict(
            family="Arial, sans-serif",
            size=12, 
            color='#222222'
        ),
        hoverinfo='text',
        hovertext=company_hover,
        name='Production Companies',
        customdata=company_ids
    )
    
    # Create analysis data for the sidebar
    director_collab_count = {director: len(list(G.neighbors(director))) for director in G.nodes() if G.nodes[director]['type'] == 'director'}
    company_collab_count = {company: len(list(G.neighbors(company))) for company in G.nodes() if G.nodes[company]['type'] == 'company'}
    
    top_directors_by_collab = sorted(director_collab_count.items(), key=lambda x: x[1], reverse=True)[:5]
    top_companies_by_collab = sorted(company_collab_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Find strong collaborations
    collaborations = network_data['collaborations']
    top_directors = network_data['top_directors']
    top_companies = network_data['top_companies']
    
    strong_collabs = []
    for (director, company), weight in collaborations.items():
        if director in top_directors and company in top_companies and weight >= 2:
            strong_collabs.append((director, company, weight))
    
    strong_collabs = sorted(strong_collabs, key=lambda x: x[2], reverse=True)[:5]
    
    # Create the figure
    fig = go.Figure(data=[edge_trace, highlighted_edge_trace, director_trace, company_trace],
                 layout=go.Layout(
                    title={
                        'text': 'Director-Production Company Network', 
                        'font': {'size': 24, 'color': '#222222'}
                    },
                    showlegend=True,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=60),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        font=dict(color='#222222')
                    ),
                    annotations=[
                        dict(
                            text="Hover over nodes to see connections",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            font=dict(color='#222222')
                        )
                    ],
                    paper_bgcolor='#e8f0f9',  # Light grey-blue background
                    plot_bgcolor='#e8f0f9'    # Light grey-blue background
                )
            )
    
    # Add analysis text - more concise for dashboard integration
    if strong_collabs:
        analysis_text = "<b>Network Insights</b><br><br>"
        analysis_text += "<b>Top Collaborations:</b><br>" + "<br>".join([f"{d} & {c}: {w} films" for d, c, w in strong_collabs])
        
        # Add annotation with adjusted position for dashboard layout
        fig.add_annotation(
            x=1.05,  # Position closer to the network
            y=0.5,
            xref="paper",
            yref="paper",
            text=analysis_text,
            showarrow=False,
            font=dict(size=12, color="#222222"),
            align="left",
            bordercolor="#2980b9",
            borderwidth=1.5,
            borderpad=8,
            bgcolor="rgba(236, 240, 241, 0.9)",
            opacity=0.9
        )
    
    return fig

def create_network_visualization(df, max_directors=10, max_companies=10):
    """Prepare and return a director-company network visualization figure"""
    # Process the JSON columns if needed
    if 'production_companies' in df.columns:
        sample = df['production_companies'].iloc[0] if not df['production_companies'].empty else None
        if isinstance(sample, str) and not isinstance(sample, list):
            df = process_movie_data(df, ['production_companies'])
    
    # Generate network data
    network_data = director_company_network(df, max_directors=max_directors, max_companies=max_companies)
    
    # Create the network figure
    fig = create_network_figure(network_data)
    
    return fig
