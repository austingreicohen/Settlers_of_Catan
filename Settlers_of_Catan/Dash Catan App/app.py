#!/usr/bin/env python
# coding: utf-8

# In[1]:


#Standard Imports

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pathlib
import flask
import os

#Define path for raw data and assets

dirname=os.path.dirname
path = os.path.dirname(os.path.realpath('file'))

#import raw data and perform relevant transformations

raw_data = pd.read_excel("Definitive_Catan_Standings_June2020.xlsx",sheet_name = "Raw Player Detail")

raw_data.fillna(0,inplace=True)

cols = [i for i in raw_data.columns if i not in ['Player']]

for col in cols:
    raw_data[col] = pd.to_numeric(raw_data[col])

game_data = pd.read_excel("Definitive_Catan_Standings_June2020.xlsx",sheet_name = "Raw Game Log")

pd.to_datetime(game_data.Date,errors='coerce')

mean_duration = np.mean(game_data.Hours.dropna())

game_data.Hours.fillna(mean_duration,inplace=True)

game_data.fillna(0,inplace=True)

#merge player and game data

full_data =pd.merge(game_data,raw_data,left_on='Game ID',right_on='Game ID')    

#transform data into a player win rate df (not including legacy games)

player_played_df = full_data.pivot_table(index='Player',values='Game ID',aggfunc=pd.Series.nunique)

player_played_df.reset_index(inplace=True)

player_played_df=player_played_df[['Player','Game ID']]

player_played_df.columns = ['Player','Number of Games']

player_result_percentage_df = full_data[full_data['Result']==1].pivot_table(index='Player',values='Game ID',aggfunc=pd.Series.nunique)
    
player_result_percentage_df.reset_index(inplace=True)

player_result_percentage_df=player_result_percentage_df[['Player','Game ID']]

player_result_percentage_df.columns = ['Winner','Number of Wins']

player_result_percentage_df = pd.merge(player_played_df,player_result_percentage_df,left_on = 'Player',right_on='Winner')
    
player_result_percentage_df["Percentage"] = player_result_percentage_df["Number of Wins"]/player_result_percentage_df["Number of Games"]

#pull standings (including legacy)

standings = pd.read_excel("Definitive_Catan_Standings_June2020.xlsx",sheet_name = "Standings")

standings = standings.iloc[:,0:9]

#Create df of drinking data, limited to those who drink

x_drink = full_data[full_data['>2 Beers?']==1].Player.value_counts()
y_drink = full_data[full_data.Player.isin(x_drink.index)].Player.value_counts()

drinkers = pd.DataFrame({'drink': x_drink,'total':y_drink})
drinkers['percentage'] = drinkers.drink/drinkers.total

#check final dataframe

full_data.info()


# In[6]:



#Full Dashboard

import dash
from dash.dependencies import Output
import dash_core_components as dcc
import dash_html_components as html
import plotly
import plotly.graph_objs as go
from dash.dependencies import Input, Output


#Define App

app = dash.Dash(__name__)

#Give aliases to dataframes for easier call backs

df = full_data

df_player = player_result_percentage_df[['Player','Percentage']]

#App Design

server = app.server

app.layout = html.Div([
    
    #Header Div
    html.Div(
        [
            html.H3(
                "Catan Dashboard",
                style ={"margin-bottom": "0px",'textAlign':'center'},
            ),
            html.H5(
                "2017-2020",style={"textAlign":'center'}
            ),
        ]
    ),
    
    #Summary Div
    
    html.Div([
    html.Div([
      html.Div([ 
        html.Div([
            html.H6(id="winner_name"), html.P("The Top Performing Player is "+
            standings.loc[standings['Win Percentage']==standings['Win Percentage'].max(),'Player'].head(1).astype('string'),
                                              style={"textAlign":'center'}
            )],
            id="winner_name_id",
            className="pretty_container four columns",
        ),
        html.Div([
            html.H6(id="adjusted_winner_name"), html.P("The Top Performing Player Adjusted for Game Size is "+
            standings.loc[standings['Game Size Adj (+/-)']==standings['Game Size Adj (+/-)'].max(),'Player'].head(1).astype('string'),
                                              style={"textAlign":'center'}
            )],
            id="adjusted_winner_name_id",
            className="pretty_container four columns",
        ),
         html.Div([
            html.H6(id="Totals"), html.P("We have spent "+str(round(df.Hours.sum(),2))+" hours playing Catan across "+str(df['Game ID'].max())+" games",
                                         style={"textAlign":'center'}
            )],
            id="totals_tile_id",
            className="pretty_container four columns",
        ),
    ],
        id='info-container',
        className='row container-display',
        ),
    ],
    id='top-row',
        className='pretty_container twelve columns',
    ),
    ],
        className="row flex-display",
    ),
   
    #Graph Div
    
    #Overview Scatter Plot
    
    html.Div([
    
    dcc.Graph(id='scatter',figure= go.Figure(data=go.Scatter(
    x=full_data['Date'],
    y=full_data['Hours'],
    mode='markers',
    marker=dict(size=2*full_data['# Players'],color=full_data['High Key Rating, 1-10'],colorscale='Viridis',
        showscale=True),
    ),
    layout=dict(
        title=dict(text="Overview Graph",x=0.5,xanchor='center'),
        legend=dict(orientation="h"),
        xaxis_title="Date",
        yaxis_title="Game Duration (Hours)"
        )
    )),
    html.P("Size = Number of Players",style={"textAlign":'center'}),
    html.P("Color = Key",style={"textAlign":'center'}),   
    
    #Player Win Percentage Input and Graph    
        
    dcc.Dropdown(id="input",
        options =[{'label': i,'value': i} for i in df_player.Player],
        value = ['Austin','Ben'],
                multi=True),
         
    dcc.Graph(id="output-graph"),
   
   #Game Stats Graph     
        
   html.Div([
    
    html.Div([ 
        
        html.Div([
            html.H5("Games by Selected Metric",style={"textAlign":'center'})],
            className='pretty_container'),
            
        html.Div([    
        
            dcc.Dropdown(id="game_input",
                options = [{'label': i, 'value': i} for i in ['Location','Winner','High Key Rating, 1-10','Player']],
                value = 'Player')],
        className='pretty_container'),
        
        html.Div([
            
            html.Div([
                
            dcc.Graph(id='game-graph')],className='pretty_container six columns'),
            
            html.Div([
                
             dcc.Graph(id='game-percent-graph')],className='pretty_container six columns')
    ],
        className ='row container-display')
    ],
        className = 'pretty_container twelve columns')
   ],
       className='row flex-display'),
   
    #Drinking Data Graph    
        
    dcc.Graph(id="drinkers",figure={'data':[{'x':drinkers.index,'y':drinkers.percentage,'type':'bar'}],
                                   'layout':dict(xaxis={'title':'Player'},
                                                 yaxis={'title':'Percentage of Games Played Drinking','tickformat':".2%"},
                                                 title=dict(text='Percentage Played Drinking (if >0%)'))})
])
],
    
id="mainContainer",
    style={"display": "flex", "flex-direction": "column"}
)
                     
#Callback Functions
    
#Win Percentage Selector    
    
@app.callback(
    Output(component_id='output-graph', component_property='figure'),
    [Input(component_id='input',component_property='value')])
def update_value(value):
    
    filtered_df = df_player[df_player['Player'].isin(value)]
    
    return ({
        'data': [ {'x':filtered_df['Player'], 'y':filtered_df['Percentage'],'type':'bar','name':value}],
        'layout': dict(xaxis={'title':'Player'},
                       yaxis={'title':'Win Percentage','tickformat':".2%"},
                       title= dict(text="Win Percentages Excluding Legacy Games",x=0.5,xanchor='center'))
        
    })

#Game Stats Number of Games Graph Selector

@app.callback(
    Output(component_id='game-graph', component_property='figure'),
    [Input(component_id='game_input',component_property='value')])

def update_game_value(value):
    
    pivoted = full_data.pivot_table(index=value,values='Game ID',aggfunc=pd.Series.nunique)
    
    pivoted.reset_index(inplace=True)

    pivoted=pivoted[[value,'Game ID']]

    pivoted.columns = [value,'Number of Games']
    
    return ({
        'data': [{'x':pivoted[value],'y':pivoted['Number of Games'],'type':'bar','name':'Games by'+value
                 }],
        'layout': dict(xaxis={'title':'Games by '+value},yaxis={'title':'Number of Games'})
    })

#Game Stats Percentage of Games Graph Selector

@app.callback(
    Output(component_id='game-percent-graph', component_property='figure'),
    [Input(component_id='game_input',component_property='value')])

def update_game_percent_value(value):
    
    pivoted = full_data.pivot_table(index=value,values='Game ID',aggfunc=pd.Series.nunique)
    
    pivoted.reset_index(inplace=True)

    pivoted=pivoted[[value,'Game ID']]

    pivoted.columns = [value,'Number of Games']
    
    return ({
        'data': [{'x':pivoted[value],'y':pivoted['Number of Games']/df['Game ID'].max(),'type':'bar','name':'Games by'+value
                 }],
        'layout': dict(xaxis={'title':'Percentage of Games by '+value},yaxis={'title':'Percentage of Games','tickformat':".2%"})
    })

#Run App

if __name__ == '__main__':
    app.run_server(debug=False)    
    


# In[ ]:




