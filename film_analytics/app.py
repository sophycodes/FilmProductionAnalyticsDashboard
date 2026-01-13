
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from utils.financial import create_budget_revenue_scatter_with_roi_analysis
from utils.location import calculate_marketshare, create_location_heatmap, create_market_share_pie, location_production_dashboard
from utils.time_date import create_date_heatmap, create_runtime_plot
from utils.genre import prepare_genre_metrics, create_genre_figure
from utils.director import create_director_figure, director_company_network, create_network_figure, create_enhanced_network_figure
from utils.data_processing import process_movie_data

PLOT_WIDTH = 1200  # Global constant for plot widths

# Load dataset
try:
    df = pd.read_csv('/Users/sophyfigaroa/Documents/Pomona College/Spring 2025/CS180_DataVisualization/Final Project Film Production Analytics/data/movie_dataset.csv')
    df_clean = process_movie_data(df)
    print(f"Loaded dataset with {len(df_clean)} records")
except FileNotFoundError:
    print("Dataset not found. Please check the file path.")
    # Create a sample dataset or exit

# Initialize the Dash app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)  # Add this parameter
app.title = "Film Industry Analytics Dashboard"
server = app.server

# Define the tab layout
app.layout = dbc.Container([
    html.H1("Film Industry Analytics Dashboard", className="text-center my-4"),
    
    dcc.Tabs(id="tabs", value="tab-financial", children=[
        dcc.Tab(label="Financial Analysis", value="tab-financial"),
        dcc.Tab(label="Location Analysis", value="tab-location"),
        dcc.Tab(label="Time Analysis", value="tab-time"),
        dcc.Tab(label="Genre Analysis", value="tab-genre"),
        dcc.Tab(label="Director Analysis", value="tab-director"),
        dcc.Tab(label="Network Analysis", value="tab-network"),  # Add this new tab
    ]),
    
    html.Div(id="tab-content", className="mt-4")
], fluid=True)

# Callback to handle tab switching
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value")
)
def render_tab_content(tab):
    if tab == "tab-financial":
        return financial_layout()
    elif tab == "tab-location":
        return location_layout()
    elif tab == "tab-time":
        return time_layout()
    elif tab == "tab-genre":
        return genre_layout()
    elif tab == "tab-director":
        return director_layout()
    elif tab == "tab-network":
        return network_layout()
    
    # Default case
    return financial_layout()

# Define the financial tab layout 
def financial_layout():
    return html.Div([
        html.H2("Film Financials Analysis"),
        dcc.Graph(
            id='financial-plot',
            config={'displayModeBar': True}
        ),
        html.Div(id='financial-selected-data')
    ], style={
        'backgroundColor': 'white',  # White background for the entire tab
        'padding': '20px',
        'borderRadius': '5px'
    })

# Callback for selected data in financial plot 
@app.callback(
    Output('financial-selected-data', 'children'),
    Input('financial-plot', 'selectedData')
)
def display_financial_selected_data(selectedData):
    if selectedData is None:
        return "Select data points from the scatter plot to see details here."
    
    points = selectedData['points']
    titles = []

    for pt in points:
        custom = pt.get('customdata')
        if isinstance(custom, (list, tuple)) and custom:
            titles.append(custom[0])

    if titles:
        return html.Ul([html.Li(title) for title in titles])
    else:
        return "No valid movie titles selected."

# Callback for hover interaction in financial plot
@app.callback(
    Output('financial-plot', 'figure'),
    Input('financial-plot', 'hoverData')
)
def update_financial_figure_on_hover(hoverData):
    fig = create_budget_revenue_scatter_with_roi_analysis(df_clean)

    hovered_bracket = None
    if hoverData and 'points' in hoverData:
        point_data = hoverData['points'][0]
        custom = point_data.get('customdata')
        if isinstance(custom, (list, tuple)) and len(custom) >= 2:
            hovered_bracket = str(custom[1])

    bar_traces = list(fig.select_traces(selector=dict(type='bar')))
    if hovered_bracket and bar_traces:
        trace = bar_traces[0]
        bar_x = trace.x
        trace.marker.color = [
            'dodgerblue' if str(x) == hovered_bracket else 'lightgray'
            for x in bar_x
        ]
        trace.opacity = 0.9

    return fig

def location_layout():
    # Get market share data once
    market_share_data = calculate_marketshare(df_clean)
    # Create the figure
    location_fig = location_production_dashboard(market_share_data)
    
    return dbc.Container([  # Changed from html.Div to dbc.Container
        html.H2("Global Film Production Analysis"),
        dcc.Graph(
            id='location-graph',
            figure=location_fig
        ),
        html.Div([
            html.P("This visualization shows film production distribution across countries and their respective market shares based on revenue.")
        ], className="mt-4")
    ], fluid=True)  # Added fluid=True to match other layouts


def time_layout():
    """Layout for the Time Analysis tab"""
    # Get the figures
    heatmap_fig = create_date_heatmap(df_clean)
    runtime_fig = create_runtime_plot(df_clean)
    
    return dbc.Container([
        html.H2("Film Release Timing Analysis", className="mb-4"),
        
        # Description
        dbc.Row([
            dbc.Col(
                html.P("This visualization shows how release timing affects movie performance and runtime trends over time.")
            )
        ], className="mb-3"),
        
        # MODIFY THIS SECTION - Change from side-by-side to stacked
        dbc.Row([
            # First visualization
            dbc.Col([
                html.H4("Release Day Heatmap", className="text-center"),
                dcc.Graph(
                    id='release-heatmap',
                    figure=heatmap_fig,
                    style={'height': '700px'}
                )
            ], md=12),  # Full width now (12/12 columns)
        ]),
        
        # Add a new row for the second visualization
        dbc.Row([
            # Second visualization
            dbc.Col([
                html.H4("Runtime Trends by Genre", className="text-center mt-4"),  # Added mt-4 for top margin
                dcc.Graph(
                    id='runtime-plot',
                    figure=runtime_fig,
                    style={'height': '700px'}
                )
            ], md=12)  # Full width
        ]),
   
    ], fluid=True)
    
# Updated genre_layout function
def genre_layout():
    """Layout for the Genre Analysis tab"""
    return dbc.Container([
        html.H2("Movie Genre Analysis", className="mb-4"),
        
        # Description
        dbc.Row([
            dbc.Col(
                html.P("This visualization shows how different genres compare in terms of ratings, revenue, and budget.")
            )
        ], className="mb-3"),
        
        # Controls in a separate row at the top
        dbc.Row([
            html.H4("Genre Ratings", className="text-center mb-3"),
            dbc.Col([
                html.Label("Sort by:"),
                dcc.Dropdown(
                    id='genre-sort-dropdown',
                    options=[
                        {'label': 'Average Rating', 'value': 'vote_average'},
                        {'label': 'Average Revenue $', 'value': 'revenue'},
                        {'label': 'Average Budget $', 'value': 'budget'}
                    ],
                    value='vote_average',
                    clearable=False
                )
            ], width=4)  # Using width=4 instead of md=3 for consistency
        ], className="mb-2"),
        
        # Visualization row (full width)
        dbc.Row([
            dbc.Col([
                dcc.Loading(
                    id="genre-loading-graph",
                    type="default",
                    children=dcc.Graph(
                        id='genre-bar-chart',
                        style={'height': '700px'}
                    )
                )
            ], md=12)  # Full width (12/12 columns)
        ])
    ], fluid=True)

# Add callbacks for the genre tab
@app.callback(
    Output('genre-bar-chart', 'figure'),
    [Input('genre-sort-dropdown', 'value')]
)
def update_genre_visualization(sort_by):
    # Create the figure and get top genres
    fig, top_genres = create_genre_figure(df_clean, sort_by)
    
    return fig

def director_layout():
    """Layout for the Director Analysis tab showing director metrics"""
    
    return dbc.Container([
        html.H2("Director Analysis", className="mb-4"),
        
        # Description row
        dbc.Row([
            dbc.Col(
                html.P("This visualization shows top directors by various metrics such as rating, revenue, and budget.")
            )
        ], className="mb-3"),
        
        # Visualization with dropdown
        dbc.Row([
            dbc.Col([
                html.H4("Top Directors by Metrics", className="text-center mb-3"),
                # Sort dropdown
                dbc.Row([
                    dbc.Col([
                        html.Label("Sort by:"),
                        dcc.Dropdown(
                            id='director-sort-dropdown',
                            options=[
                                {'label': 'Average Rating', 'value': 'vote_average'},
                                {'label': 'Average Revenue $', 'value': 'revenue'},
                                {'label': 'Average Budget $', 'value': 'budget'}
                            ],
                            value='vote_average',
                            clearable=False
                        )
                    ], width=4)
                ], className="mb-2"),
                # Bar chart - now larger since it's the only visualization
                dcc.Graph(
                    id='director-bar-chart',
                    style={'height': '700px'}
                )
            ], md=12)
        ]),
        
    ], fluid=True)
    
    
# Add callbacks for the director tab
@app.callback(
    Output('director-bar-chart', 'figure'),
    [Input('director-sort-dropdown', 'value')]
)
def update_genre_visualization(sort_by):
    # Create the figure and get top genres
    fig = create_director_figure(df_clean, sort_by)

    return fig


def network_layout():
    """Layout for the Network Analysis tab"""
    
    # Create an empty figure for initial load
    empty_fig = go.Figure().update_layout(
        title="Click 'Update Network' to generate the visualization",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='#e8f0f9',
        paper_bgcolor='#e8f0f9',
        height=700,
        width=1100,  # Add fixed width here too
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return dbc.Container([
        html.H2("Director-Studio Network Analysis", className="mb-4"),
        
        # Description row
        dbc.Row([
            dbc.Col(
                html.P("This visualization shows the collaboration network between directors and production companies.")
            )
        ], className="mb-3"),
        
        # Network controls
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.Label("Number of Directors:"),
                        dcc.Slider(
                            id='network-director-slider',
                            min=5,
                            max=30,
                            step=5,
                            value=10,
                            marks={i: str(i) for i in range(5, 35, 5)}
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Number of Studios:"),
                        dcc.Slider(
                            id='network-company-slider',
                            min=5,
                            max=30,
                            step=5,
                            value=10,
                            marks={i: str(i) for i in range(5, 35, 5)}
                        )
                    ], md=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Button(
                            'Update Network', 
                            id='network-update-button',
                            n_clicks=0,
                            className="btn btn-primary mt-3 mb-3"
                        )
                    ], width="auto", className="mx-auto")
                ])
            ], md=12)
        ], className="mb-3"),
        
        # Network graph with consistent sizing
        dbc.Row([
            dbc.Col([
                html.Div(
                    dcc.Loading(
                        id="network-loading",
                        type="circle",
                        children=dcc.Graph(
                            id='network-graph',
                            figure=empty_fig,
                            style={
                                'height': '700px',
                                'width': '100%'  # Use 100% width for responsiveness
                            },
                            config={
                                'displayModeBar': True,
                                'responsive': True  # Make graph responsive
                            }
                        )
                    ),
                    style={
                        'min-height': '750px',  # Add some extra space for loading spinner
                        'width': '100%'
                    }
                )
            ], md=12)
        ]),
        
        # Hidden storage for network data
        dcc.Store(id='network-data-store')
        
    ], fluid=True)


@app.callback(
    Output('network-graph', 'figure'),
    [Input('network-data-store', 'data'),
     Input('network-graph', 'hoverData')],
    [State('network-graph', 'figure'),
     State('network-graph', 'relayoutData')]
)
def update_network_graph(network_data, hover_data, current_figure, relayout_data):
    import networkx as nx
    import plotly.graph_objects as go
    
    # Extract highlighted node from hover data
    highlighted_node = None
    if hover_data and 'points' in hover_data:
        for point in hover_data['points']:
            if 'customdata' in point:
                highlighted_node = point['customdata']
                break
    
    # If we have a current figure and just need to update highlights
    if current_figure and 'data' in current_figure and len(current_figure['data']) >= 4:
        try:
            # Create a copy of the current figure
            fig = go.Figure(current_figure)
            
            # Find trace indices
            director_trace_idx = None
            company_trace_idx = None
            edge_trace_idx = None
            highlighted_edge_trace_idx = None
            
            # Check attributes safely
            for i, trace in enumerate(fig.data):
                if hasattr(trace, 'name'):
                    if trace.name == 'Directors':
                        director_trace_idx = i
                    elif trace.name == 'Production Companies':
                        company_trace_idx = i
                elif i == 0:  # Regular edges are typically the first trace
                    edge_trace_idx = i
                elif i == 1:  # Highlighted edges are typically the second trace
                    highlighted_edge_trace_idx = i
            
            # Update director colors
            if director_trace_idx is not None and hasattr(fig.data[director_trace_idx], 'customdata'):
                colors = []
                for d_id in fig.data[director_trace_idx].customdata:
                    if d_id == highlighted_node:
                        colors.append('#1a5276')
                    else:
                        colors.append('#2980b9')
                fig.data[director_trace_idx].marker.color = colors
            
            # Update company colors
            if company_trace_idx is not None and hasattr(fig.data[company_trace_idx], 'customdata'):
                colors = []
                for c_id in fig.data[company_trace_idx].customdata:
                    if c_id == highlighted_node:
                        colors.append('#006400')
                    else:
                        colors.append('#16a085')
                fig.data[company_trace_idx].marker.color = colors
            
            # Update highlighted edges
            if highlighted_edge_trace_idx is not None:
                # If no highlighted node, clear the highlighted edges
                if not highlighted_node:
                    fig.data[highlighted_edge_trace_idx].x = []
                    fig.data[highlighted_edge_trace_idx].y = []
                else:
                    # Reconstruct graph to find edges
                    G = nx.Graph()
                    
                    # Add nodes
                    for node_data in network_data['nodes']:
                        G.add_node(node_data['id'], type=node_data['type'], count=node_data['count'])
                    
                    # Add edges
                    for edge_data in network_data['edges']:
                        G.add_edge(edge_data['source'], edge_data['target'], weight=edge_data['weight'])
                    
                    # Convert positions back to tuples
                    pos = {node: tuple(pos_list) for node, pos_list in network_data['pos'].items()}
                    
                    # Prepare highlighted edge data
                    highlighted_edges_x = []
                    highlighted_edges_y = []
                    
                    # Process edges
                    for edge in G.edges():
                        node1, node2 = edge
                        if node1 == highlighted_node or node2 == highlighted_node:
                            x0, y0 = pos[node1]
                            x1, y1 = pos[node2]
                            highlighted_edges_x.extend([x0, x1, None])
                            highlighted_edges_y.extend([y0, y1, None])
                    
                    # Update the highlighted edge trace
                    fig.data[highlighted_edge_trace_idx].x = highlighted_edges_x
                    fig.data[highlighted_edge_trace_idx].y = highlighted_edges_y
            
            # Maintain consistent size and preserve the zoom level
            fig.update_layout(
                height=700,
                width=1100,
                autosize=False,
                margin=dict(l=20, r=20, t=60, b=20),
                transition_duration=0
            )
            
            # Preserve the zoom level
            if relayout_data and 'xaxis.range[0]' in relayout_data:
                fig.update_layout(
                    xaxis=dict(
                        range=[relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
                    ),
                    yaxis=dict(
                        range=[relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]']]
                    )
                )
            
            return fig
        except Exception as e:
            print(f"Error updating figure: {e}")
            # If there's an error in the update, fall back to creating a new figure
            pass
    
    # Create a complete new figure
    # Reconstruct graph from serialized data
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
    
    # Create figure with highlights
    fig = create_enhanced_network_figure(reconstructed_data, highlighted_node)
    
    # Set consistent size and layout parameters
    fig.update_layout(
        height=700,
        width=1100,  # Fixed width
        autosize=False,
        margin=dict(l=20, r=20, t=60, b=20),
        transition_duration=0,  # Disable animations for smoother interactions
        hovermode='closest',
        plot_bgcolor='#e8f0f9',  # Match the empty figure background
        paper_bgcolor='#e8f0f9'  # Match the empty figure background
    )
    
    # Preserve the zoom level from previous interactions
    if relayout_data and 'xaxis.range[0]' in relayout_data:
        fig.update_layout(
            xaxis=dict(
                range=[relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']]
            ),
            yaxis=dict(
                range=[relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]']]
            )
        )
    
    return fig


# Callback to update the network data
@app.callback(
    Output('network-data-store', 'data'),
    Input('network-update-button', 'n_clicks'),
    State('network-director-slider', 'value'),
    State('network-company-slider', 'value'),
    prevent_initial_call=False  # Changed to False to run on initial page load
)
def update_network_data(n_clicks, max_directors, max_companies):
    # Set default values if this is the initial call
    max_directors = max_directors or 5
    max_companies = max_companies or 5
    
    # Generate network data
    network_data = director_company_network(df_clean, max_directors=max_directors, max_companies=max_companies)
    
    # Convert sets to lists for JSON serialization
    network_data['directors'] = list(network_data['directors'])
    network_data['companies'] = list(network_data['companies'])
    
    # Prepare serializable data for JSON storage
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

# Run the app
if __name__ == '__main__':
    app.run(debug=True)