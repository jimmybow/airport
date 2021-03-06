# -*- coding: utf-8 -*-
"""
Created on Fri Jun 30 09:36:25 2017

@author: jimmybow
"""

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from dplython import *
from flask import Flask
import os

del(diamonds)

airports = pd.read_csv('airports.csv')
LDD = pd.read_csv('LDD.csv')
ff1 = pd.read_csv('ff1.csv')
ff2 = pd.read_csv('ff2.csv')

ffk = pd.concat( [ff1, ff2], axis = 1)
del(ff1)
del(ff2)

da = (
DplyFrame(ffk) 
>> group_by(X['Flight date'])
>> summarize( counts = X.d.size, d=X.d.max())
>> arrange(X.d)
>> X.reset_index().drop('index', 1)
)
### 圓餅圖

layoutS = dict(title = '飛航目標之計數',
              dragmode = "pan" ,
              showlegend = False,
              width=600,
              height=350,
              margin=dict(
               l=0,
               r=50,
               b=50,
               t=50,
               pad=4
                 )
              )
              
layoutD = dict(title = '飛航來源之計數',
              dragmode = "pan" ,
              showlegend = False,
              width=600,
              height=350,
              margin=dict(
               l=0,
               r=50,
               b=50,
               t=50,
               pad=4
                 )
              )              

############

aplo = pd.concat( [ffk['Source Airport'], 
                   ffk['Destination Airport']  ] ).drop_duplicates().rename('aplo')  
aplo = pd.DataFrame(aplo)

airports2 = pd.merge(airports, LDD, how='left', left_on = 'Code',  right_on = "IATA")
airLL = pd.merge(aplo, airports2, how='left', left_on = 'aplo',  right_on = "IATA")

aps = [ dict(
        type = 'scattergeo',
        locationmode = 'USA-states',
        lon = airLL.Longitude,
        lat = airLL.Latitude,
        hoverinfo = 'text',
        text = airLL.Description,
        mode = 'markers',
        marker = dict( 
            size=2, 
            color='rgb(255, 0, 0)',
            line = dict(
                width=3,
                color='rgba(68, 68, 68, 0)'
            )
        ))]
        

maxf = (
DplyFrame(ffk)    
>> group_by(X['Source Airport'], X['Destination Airport']) 
>> summarize(cc = X.d.size )
>> ungroup()
>> summarize(m = X.cc.max())
>> X.loc[0][0]                       
)

server = Flask(__name__)
server.secret_key = os.environ.get('secret_key', 'secret')
app = dash.Dash(name = __name__, server = server)
app.config.supress_callback_exceptions = True

app.layout = html.Pre([
    '\n',
    html.Div(style={'width': '3%', 'display': 'inline-block'}),        
    html.Div(dcc.RangeSlider(
        id='time-slider', 
        count=1,
        min=0,
        max=len(da)-1,
        step=1,
        value=[0, 6],
        marks={i: da['Flight date'][i].replace('2014/','') for i in range(len(da))}
    ), style={'width': '80%', 'display': 'inline-block', 'padding': '20px 20px 20px 20px'}),    
    '\n\n',
    html.Div([html.Div(style={'width': '55%', 'display': 'inline-block', 'padding': '20px 20px 20px 20px'  }),
             html.Font(id = 'outt',
                       style={ 'display': 'inline-block', 
                       'padding': '20px 20px 20px 20px',
                        'font-size':20,
                        'color':'#0000FF'}
                       )  ]),       
    html.Div([
    html.Div(dcc.Graph(id='graph-with-slider'),
             style={'display': 'inline-block', 'padding': '20px 0px 20px 20px'}),
    html.Div([dcc.Graph(id='Line-S', figure = dict(data = go.Pie(), layout=layoutS) ),
              dcc.Graph(id='Line-D', figure = dict(data = go.Pie(), layout=layoutD) ) ],
              style={'width': '30%', 'display': 'inline-block', 'padding': '20px 20px 20px 0px'})
    ], style={'padding': '0px 0px'})   
])
    

layout = dict(
           title = '航空路線圖',
           showlegend = False,
           autosize = False,
           width=900,
           height=800,
           margin=dict(
              l=20,
              r=20,
              b=50,
              t=50,
              pad=4
           ),
           geo = dict(
              projection=dict( type='azimuthal equal area' ),
              showland = True,
              showlakes = True,
              showcountries = True,
              scope='north america',
              landcolor = 'rgb(243, 243, 243)',
              countrycolor = 'rgb(204, 204, 204)'
           )
    )

@app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('time-slider', 'value')])
def update_fig(index_time):
    s = index_time[0]+1
    e = index_time[1]+1
    
    ff = (
    DplyFrame(ffk)
    >> sift(X.d >= s, X.d <= e)     
    >> group_by(X['Source Airport'], X['Destination Airport']) 
    >> mutate(cnt = X.d.size )                       
    >> X.drop_duplicates(['Source Airport','Destination Airport']) 
    )
#ff.cnt.isin([np.nan]).sum()  # 無遺失值
            
    flight_paths = []
    for i in range( len( ff ) ):
        flight_paths.append(
            dict(
                type = 'scattergeo',
                locationmode = 'USA-states',
                lon = [ ff.Longitude_s.iloc[i], ff.Longitude_d.iloc[i] ],
                lat = [ ff.Latitude_s.iloc[i], ff.Latitude_d.iloc[i] ],
                mode = 'lines',
                line = dict(
                    width = 1,
                    color = 'red',
                ),
                opacity = float(ff.cnt.iloc[i])/float(maxf),
            )
        )
    
    return dict( data =  flight_paths + aps, layout=layout )

@app.callback(
    Output('outt', 'children'),
    [Input('graph-with-slider', 'hoverData')])
def display_hover_data0(Data):
    r = ''
    if str(type(Data))!="<class 'NoneType'>":
        n = Data['points'][0]['pointNumber']
        r = airLL.iloc[int(n)]['Name']
    return r

@app.callback(
    Output('Line-S', 'figure'),
    [Input('graph-with-slider', 'hoverData'),
     Input('time-slider', 'value')           ])
def display_hover_data1(Data, index_time):
    
    s = index_time[0]+1
    e = index_time[1]+1
    data = go.Pie()
    
    if str(type(Data))!="<class 'NoneType'>":
        n = Data['points'][0]['pointNumber']
        iata = airLL.iloc[n]['IATA'] 
        dd = (
        DplyFrame(ffk) 
        >> sift( X['Source Airport'] == iata, X.d >= s, X.d <= e)
        >> group_by(X['Destination Airport'])
        >> summarize( counts = X.d.size)
        )
    
        dd = pd.merge(dd, airLL, how='left', left_on = 'Destination Airport',  right_on = "IATA")
    
        trace = go.Pie(
            labels = dd['Description'],
            values = dd.counts, 
            hoverinfo='label+percent', 
            textinfo='value',
        ) 
        data = [trace]
        
    return dict(data = data, layout = layoutS)

@app.callback(
    Output('Line-D', 'figure'),
    [Input('graph-with-slider', 'hoverData'),
     Input('time-slider', 'value')           ])
def display_hover_data2(Data, index_time):
    
    s = index_time[0]+1
    e = index_time[1]+1
    data = go.Pie()
    
    if str(type(Data))!="<class 'NoneType'>":
        n = Data['points'][0]['pointNumber']
        iata = airLL.iloc[n]['IATA']
        dd = (
        DplyFrame(ffk) 
        >> sift( X['Destination Airport'] == iata, X.d >= s, X.d <= e)
        >> group_by(X['Source Airport'])
        >> summarize( counts = X.d.size)
        )
        
        dd = pd.merge(dd, airLL, how='left', left_on = 'Source Airport',  right_on = "IATA")
        
        trace = go.Pie(
            labels = dd['Description'],
            values = dd.counts, 
            hoverinfo='label+percent', 
            textinfo='value',
        ) 
        data = [trace]
        
    return dict(data = data, layout = layoutD)
