import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import dash
from dash import dcc, html, Input, Output


def create_budget_revenue_scatter_with_roi_analysis(
    df,
    max_points = 100
    ):
    """
    Create an interactive visualization with a scatterplot of movies (budget vs revenue)
    combined with the standard ROI and success rate analysis by budget bracket
    """
    if 'budget' in df.columns:
        # Filter out rows with missing or non-positive budget/revenue values
        valid_mask = (df['budget'] > 0) & (~df['budget'].isna()) & (df['revenue'] > 0) & (~df['revenue'].isna())
        df_valid = df[valid_mask].copy()
        
        # Convert budget and revenue to millions
        df_valid['budget_millions'] = df_valid['budget'] / 1000000
        df_valid['revenue_millions'] = df_valid['revenue'] / 1000000
        
        df_valid['Budget_Bracket'] = pd.cut(
            df_valid['budget_millions'], 
            bins=[0, 10, 20, 30, 50, 100, 150, 200, 1000],
            labels=['0-10M', '10-20M', '20-30M', '30-50M', '50-100M', '100-150M', '150-200M', '200M+']
        ).astype(str)

        # Calculate success indicators
        df_valid['broke_even'] = df_valid['revenue'] > df_valid['budget']
        df_valid['is_successful'] = df_valid['revenue'] > (df_valid['budget'] * 2)
        
        # Calculate color indicator for scatter plot
        df_valid['success_category'] = 'Loss'
        df_valid.loc[df_valid['broke_even'], 'success_category'] = 'Break Even'
        df_valid.loc[df_valid['is_successful'], 'success_category'] = 'Success'
        
        # Calculate statistics by budget bracket
        budget_analysis = df_valid.groupby('Budget_Bracket', observed=False).agg({
            'budget_millions': 'mean',
            'revenue_millions': 'mean',
            'roi': 'mean',
            'title': 'count'
        }).reset_index()
        
        # Calculate success rates per budget bracket
        success_rate = df_valid.groupby('Budget_Bracket', observed=False)['is_successful'].mean() * 100
        budget_analysis['Success_Rate'] = success_rate.values
        
        broke_even_rate = df_valid.groupby('Budget_Bracket', observed=False)['broke_even'].mean() * 100
        budget_analysis['Broke_Even_Rate'] = broke_even_rate.values
        
        # Rename title column to Count
        budget_analysis = budget_analysis.rename(columns={'title': 'Count'})
        
        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.6, 0.4],
            subplot_titles=(
                "Movie Budget vs. Revenue (by Success Category)", 
                "Average ROI by Budget Range"
            ),
            specs=[[{"type": "scatter"}], [{"type": "bar"}]]
        )
        
        # Add scatterplot of budget vs revenue (subplot 1)
        color_map = {'Loss': 'red', 'Break Even': 'orange', 'Success': 'green'}
        
        # Add scatterplot for each success category
        for category, color in color_map.items():
            category_data = df_valid[df_valid['success_category'] == category]

            # Limit number of points to avoid overplotting
            if len(category_data) > max_points:
                category_data = category_data.sample(max_points, random_state=42)

            
            if not category_data.empty:
                # Create hover text for this category only
                hover_text = []
                for _, row in category_data.iterrows():
                    genre_text = ""
                    if 'genres' in row and isinstance(row['genres'], list) and len(row['genres']) > 0:
                        genre_text = f"<br>Genres: {', '.join(row['genres'])}"
                        
                    # Add budget bracket to hover text
                    text = (
                        f"<b>{row['title']}</b><br>" +
                        f"Budget Range: <b>{row['Budget_Bracket']}</b><br>" +
                        f"Year: {int(row['release_year']) if 'release_year' in row and not pd.isna(row['release_year']) else 'Unknown'}<br>" +
                        f"Budget: ${row['budget_millions']:.1f}M<br>" +
                        f"Revenue: ${row['revenue_millions']:.1f}M<br>" +
                        f"ROI: {row['roi']:.1f}%" +
                        genre_text
                    )
                    hover_text.append(text)
                
                # Store budget bracket for each point to enable visual highlighting
                # Modify the scatter trace for better hover functionality
                fig.add_trace(
                    go.Scatter(
                        x=category_data['budget_millions'],
                        y=category_data['revenue_millions'],
                        mode='markers',
                        marker=dict(
                            size=6,
                            opacity=0.5,
                            color=color,
                            line=dict(width=0.5, color='gray')
                        ),
                        name=category,
                        hovertemplate=
                        "<b>%{customdata[0]}</b><br>" +
                        "Budget Range: <b>%{customdata[1]}</b><br>" +
                        "Budget: $%{x:.1f}M<br>" +
                        "Revenue: $%{y:.1f}M<br>" +
                        "ROI: %{customdata[2]:.1f}%<extra></extra>",
                        customdata=np.column_stack((
                            category_data['title'], 
                            category_data['Budget_Bracket'], 
                            category_data['roi']
                        ))
                    ),
                    row=1, col=1
                )
        
        # Add reference lines for break-even and success threshold
        max_val = max(df_valid['budget_millions'].max(), df_valid['revenue_millions'].max()) * 1.1
        
        # Break-even line (y = x)
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode='lines',
                line=dict(color='orange', width=2, dash='dash'),
                name='Break Even (Revenue = Budget)',
                hoverinfo='name'
            ),
            row=1, col=1
        )
        
        # Success threshold line (y = 2x)
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val * 2],
                mode='lines',
                line=dict(color='green', width=2, dash='dash'),
                name='Success (Revenue = 2× Budget)',
                hoverinfo='name'
            ),
            row=1, col=1
        )
        
        # Add ROI bars with capped values (subplot 2)
        budget_analysis['roi_capped'] = budget_analysis['roi'].clip(upper=500)
        
        fig.add_trace(
            go.Bar(
                x=budget_analysis['Budget_Bracket'],
                y=budget_analysis['roi_capped'],
                name='Average ROI',
                marker_color='lightblue',
                opacity=0.7,
                customdata=budget_analysis['roi'],
                hovertemplate='<b>%{x}</b><br>Average ROI: %{customdata:.1f}%<br>Displayed: %{y:.1f}%<extra></extra>'
            ),
            row=2, col=1,
            secondary_y=False
        )
        
        fig.update_layout(
            height=1000,
            width=1150,
            template='plotly_white',
            font=dict(family="Segoe UI, sans-serif", size=12, color="#333"),
            hovermode='closest',
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            ),
            legend=dict(
                title="Success Category",
                orientation="v",
                yanchor="top",
                y=0.95,
                xanchor="right",
                x=1.3,
                bgcolor="rgba(255,255,255,0.8)",  # Semi-transparent background
                bordercolor="rgba(0,0,0,0.1)",    # Light border
                borderwidth=1
            ),
            margin=dict(t=100, b=60, l=80, r=200),
            paper_bgcolor="white",        # Keep outer area white
            plot_bgcolor="#e5ecf6" 
        )
        
        # Add line to show ROI cap at 500%
        fig.add_shape(
            type="line",
            x0=-0.5, x1=7.5, y0=500, y1=500,
            line=dict(color="gray", dash="dot"),
            row=2, col=1
        )

        # ROI explanation box/legend as an annotation
        fig.add_annotation(
            x=1.3,  # Positioned to the right of the chart
            y=0.10,  # Positioned in the middle of the second subplot
            xref="paper",
            yref="paper",
            showarrow=False,
            text="<b>ROI Legend</b><br><br>" +
                 "ROI (Return on Investment)<br>" +
                 "Formula: (Revenue - Budget) / Budget<br><br>" +
                 "<b>Example:</b><br>" +
                 "Budget: $10M<br>" +
                 "Revenue: $25M<br>" +
                 "ROI: (25M - 10M) / 10M = 150%",
            align="left",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1
        )

        # Update scatter plot axes (log scales for better visibility)
        fig.update_xaxes(
            title_text="Budget ($ Millions)",
            type="log",
            row=1, col=1, 
            gridcolor="white" 
        )
        
        fig.update_yaxes(
            title_text="Revenue ($ Millions)",
            type="log",
            row=1, col=1, 
            gridcolor="white" 
        )
        
        # Update ROI chart axes
        fig.update_xaxes(
            title_text="Budget Range",
            tickangle=0,
            categoryorder='array',
            categoryarray=['0-10M', '10-20M', '20-30M', '30-50M', '50-100M', '100-150M', '150-200M', '200M+'],
            row=2, col=1, 
            gridcolor="white" 
        )
        
        fig.update_yaxes(
            title_text="Average ROI (%) - Capped at 500%",
            range=[0, 500],
            row=2, col=1,
            secondary_y=False, 
            gridcolor="white" 
        )
        
        fig.update_yaxes(
            title_text="Success Rate (%)",
            range=[0, 100],
            row=2, col=1,
            secondary_y=True
        )
        
        
        # Enable highlighting across subplots
        fig.update_layout(
            clickmode='event+select',
            hovermode='closest',
            dragmode='select',
            # Enable highlighting when hovering
            hoverdistance=100,
        )
            
            
        return fig
    
    # Return empty figure if budget column not found
    return go.Figure()


