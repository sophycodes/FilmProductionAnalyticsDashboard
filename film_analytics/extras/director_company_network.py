import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math
import random
import networkx as nx
from collections import Counter
import json
import os
from data_cleaning import process_movie_data

# Specify the path to your dataset here
DATASET_PATH = '/Users/sophyfigaroa/Documents/CS180_DataVisualization/Final Project Film Production Analytics/data/movie_dataset.csv'


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

# Create the Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    html.H1("Director-Production Company Network", 
            style={'textAlign': 'center', 'color': '#111111', 'marginBottom': '20px'}),
    
    # Status indicator for dataset
    html.Div([
        html.Div(id='dataset-status', 
                 style={'padding': '10px', 'backgroundColor': '#e8f0f9', 'border': '1px solid #2980b9', 'borderRadius': '5px'})
    ], style={'width': '80%', 'margin': '0 auto', 'padding': '10px', 'textAlign': 'center'}),
    
    # Controls for network parameters
    html.Div([
        html.Label("Number of Directors:"),
        dcc.Slider(
            id='director-slider',
            min=5,
            max=30,
            step=5,
            value=10,
            marks={i: str(i) for i in range(5, 35, 5)}
        ),
        html.Label("Number of Production Companies:"),
        dcc.Slider(
            id='company-slider',
            min=5,
            max=30,
            step=5,
            value=10,
            marks={i: str(i) for i in range(5, 35, 5)}
        ),
        html.Button('Update Network', id='update-button', n_clicks=0,
                   style={'margin': '10px', 'background-color': '#2980b9', 'color': 'white', 'border': 'none', 'padding': '10px 15px'}),
    ], style={'width': '80%', 'margin': '0 auto', 'padding': '10px'}),
    
    dcc.Graph(
        id='network-graph',
        style={'height': '700px'},
        config={'displayModeBar': True}
    ),
    
    # Store to keep network data across callbacks
    dcc.Store(id='network-data-store')
])

# Callback to display dataset status
@app.callback(
    Output('dataset-status', 'children'),
    Input('network-graph', 'id')  # Dummy input to trigger on page load
)
def check_dataset_status(_):
    if os.path.exists(DATASET_PATH):
        try:
            df = pd.read_csv(DATASET_PATH)
            return f"Dataset loaded: {DATASET_PATH} ({len(df)} records)"
        except Exception as e:
            return f"Error loading dataset: {str(e)}"
    else:
        return f"Dataset not found at: {DATASET_PATH}"

# Callback to update the network data
@app.callback(
    Output('network-data-store', 'data'),
    [Input('update-button', 'n_clicks')],
    [State('director-slider', 'value'),
     State('company-slider', 'value')]
)
def update_network_data(n_clicks, max_directors, max_companies):
    try:
        # Load the dataset from the specified path
        df = pd.read_csv(DATASET_PATH)
        print(f"Successfully loaded dataset from {DATASET_PATH} with {len(df)} records")
    except Exception as e:
        print(f"Error loading data from {DATASET_PATH}: {e}")
        # Fallback to a sample dataset
        df = pd.DataFrame({
            'director': ['James Cameron', 'James Cameron', 'Christopher Nolan', 'Steven Spielberg', 
                        'Martin Scorsese', 'Quentin Tarantino', 'Stanley Kubrick', 'Alfred Hitchcock'],
            'production_companies': [
                '[{"name": "Twentieth Century Fox"}, {"name": "Lightstorm Entertainment"}]',
                '[{"name": "Paramount Pictures"}]',
                '[{"name": "Warner Bros."}, {"name": "Legendary Pictures"}]',
                '[{"name": "Universal Pictures"}, {"name": "Amblin Entertainment"}]',
                '[{"name": "Paramount Pictures"}, {"name": "Warner Bros."}]',
                '[{"name": "Miramax"}, {"name": "A Band Apart"}]',
                '[{"name": "Warner Bros."}, {"name": "Stanley Kubrick Productions"}]',
                '[{"name": "Universal Pictures"}, {"name": "Alfred Hitchcock Productions"}]'
            ]
        })
    
    # Process the JSON columns
    df = process_movie_data(df)
    
    # Generate network data
    network_data = director_company_network(df, max_directors=max_directors, max_companies=max_companies)
    
    # Convert any non-serializable objects (like sets) to lists
    network_data['directors'] = list(network_data['directors'])
    network_data['companies'] = list(network_data['companies'])
    
    # Can't serialize NetworkX graph to JSON, so extract necessary data
    serializable_data = {
        'nodes': [],
        'edges': [],
        'pos': {},
        'directors': network_data['directors'],
        'companies': network_data['companies'],
        'collaborations': {str(k): v for k, v in network_data['collaborations'].items()},
        'top_directors': network_data['top_directors'],
        'top_companies': network_data['top_companies']
    }
    
    # Extract node data
    G = network_data['G']
    for node, attrs in G.nodes(data=True):
        serializable_data['nodes'].append({
            'id': node,
            'type': attrs['type'],
            'count': attrs['count']
        })
        serializable_data['pos'][node] = list(network_data['pos'][node])
    
    # Extract edge data
    for u, v, attrs in G.edges(data=True):
        serializable_data['edges'].append({
            'source': u,
            'target': v,
            'weight': attrs.get('weight', 1)
        })
    
    return serializable_data

# Callback to update graph on hover and initial load
@app.callback(
    Output('network-graph', 'figure'),
    [Input('network-data-store', 'data'),
     Input('network-graph', 'hoverData')]
)
def update_graph(network_data, hover_data):
    if not network_data:
        # Return empty figure if no data
        return go.Figure().update_layout(
            title=f"No data loaded. Check if the dataset path is correct: {DATASET_PATH}",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
    
    # Recreate graph from serialized data
    G = nx.Graph()
    
    # Add nodes
    for node_data in network_data['nodes']:
        G.add_node(node_data['id'], type=node_data['type'], count=node_data['count'])
    
    # Add edges
    for edge_data in network_data['edges']:
        G.add_edge(edge_data['source'], edge_data['target'], weight=edge_data['weight'])
    
    # Convert positions back to tuples
    pos = {node: tuple(pos_list) for node, pos_list in network_data['pos'].items()}
    
    # Parse the collaborations back into tuples
    collaborations = {}
    for k, v in network_data['collaborations'].items():
        try:
            # Remove parentheses and split by comma
            k = k.strip('()')
            parts = k.split(',')
            if len(parts) == 2:
                # Clean up parts (remove quotes, etc.)
                dir_part = parts[0].strip().strip("'")
                co_part = parts[1].strip().strip("'")
                collaborations[(dir_part, co_part)] = v
        except:
            continue
    
    # Reconstruct network data
    reconstructed_data = {
        'G': G,
        'pos': pos,
        'directors': network_data['directors'],
        'companies': network_data['companies'],
        'collaborations': collaborations,
        'top_directors': network_data['top_directors'],
        'top_companies': network_data['top_companies']
    }
    
    # Default: no node highlighted
    highlighted_node = None
    
    # If user is hovering over a node, get its ID
    if hover_data and 'points' in hover_data:
        for point in hover_data['points']:
            if 'customdata' in point:
                highlighted_node = point['customdata']
                break
    
    # Create figure with highlights
    fig = create_network_figure(reconstructed_data, highlighted_node)
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)