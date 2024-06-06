import pandas as pd
from dash import Dash, Input, Output, dcc, html
import geopandas as gpd
import dash_leaflet as dl
import json
import plotly.express as px


data = pd.read_csv("result.csv")
line_data = pd.read_csv("lin_graph.csv")


def prepare_pie_data(category):
    pie_data = data[['City', category]].copy()
    pie_data[category] = pd.to_numeric(pie_data[category], errors='coerce')
    pie_data = pie_data[pie_data[category] > 0]
    pie_data = pie_data.rename(columns={category: 'Value'})
    return pie_data


def prepare_line_data(category):
    line_data_filtered = line_data[['rok', category]].copy()
    line_data_filtered[category] = pd.to_numeric(line_data_filtered[category], errors='coerce')
    line_data_filtered = line_data_filtered.groupby('rok').sum().reset_index()
    line_data_filtered = line_data_filtered.rename(columns={category: 'Value'})
    return line_data_filtered

world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

cz = pd.read_csv('czech.csv')
cities_gdf = gpd.GeoDataFrame(cz, geometry=gpd.points_from_xy(cz['vyska'], cz['sirka']))

czech_republic = world[world.name == 'Czechia']

geojson_czech_republic = json.loads(czech_republic.to_json())
geojson_cities = json.loads(cities_gdf.to_json())

categories = data.columns[1:]  # Категории начинаются со второго столбца
categories = categories[1:]  # Исключаем столбец 'City'

external_stylesheets = [
    {
        "href": (
            "https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;700&display=swap"
        ),
        "rel": "stylesheet",
    },
]
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Zpracování otevřených dat z úředních desek"

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H1(
                    children="Filtrace úředních desek obcí ČR", className="header-title"
                ),
                html.P(
                    children=(
                        "Webová stránka pro filtrování a zobrazování frekvencí kategorií z úředních desek obcí ČR."
                        " Vizualizace dat na mapě a přehled informací dle obcí."
                    ),
                    className="header-description",
                ),
            ],
            className="header",
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.Div(children="Kategorie", className="menu-title"),
                        dcc.Dropdown(
                            id="category-filter",
                            options=[
                                {"label": category, "value": category}
                                for category in categories
                            ],
                            value=categories[0],  # Устанавливаем первую категорию по умолчанию
                            clearable=False,
                            className="dropdown",
                        ),
                    ]
                ),
            ],
            className="menu",
        ),
        html.Div(
            children=[
                html.Div(
                    children=dcc.Graph(
                        id="pie-chart",
                        config={"displayModeBar": False},
                    ),
                    className="card",
                ),
            ],
            className="wrapper",
        ),
        html.Div(  # Добавляем линейный график
            children=[
                html.Div(
                    children=dcc.Graph(
                        id="line-chart",
                        config={"displayModeBar": False},
                    ),
                    className="card",
                ),
            ],
            className="wrapper",
        ),
        html.Div(
            children=dl.Map(
                children=[
                    dl.TileLayer(),
                    dl.GeoJSON(data=geojson_czech_republic, id="czech-republic"),
                    dl.LayerGroup(
                        id="cities"
                    )
                ],
                center=[49.8175, 15.4730],  
                zoom=7,  
                style={'height': '700px', 'width': '100%'},  
                id="world-map-chart"
            ),
            className="card"
        ),
        
    ]
)

@app.callback(
    Output("pie-chart", "figure"),
    Output("line-chart", "figure"),
    Output("cities", "children"),
    Input("category-filter", "value"),
)
def update_charts_and_map(category):
    pie_data = prepare_pie_data(category)
    line_data_filtered = prepare_line_data(category)
    
    pie_chart_figure = px.pie(pie_data, values='Value', names='City', title=f'Rozdělení kategorie "{category}" přes městy')
    pie_chart_figure.update_traces(
        textinfo='none',
        hovertemplate='<b>Město:</b> %{label}<br><b>Počet výskytů:</b> %{value}<extra></extra>'
    )
    
    line_chart_figure = px.line(line_data_filtered, x='rok', y='Value', title=f'Počet výskytů kategorie "{category}" podle let')
    line_chart_figure.update_traces(
        hovertemplate='<b>Rok:</b> %{x}<br><b>Počet výskytů:</b> %{y}<extra></extra>'
    )
    
    # Обновляем данные для карты
    filtered_cities = cities_gdf[cities_gdf['mesto'].isin(pie_data['City'])]
    
    # Объединяем данные с pie_data для получения значений категории
    filtered_cities = filtered_cities.merge(pie_data, left_on='mesto', right_on='City', how='left')
    
    markers = [
        dl.Marker(
            position=[row.geometry.y, row.geometry.x],
            title=row['mesto'],
            children=[
                dl.Tooltip(f"Město: {row['mesto']}\nPočet výskytů: {row['Value']}")  # Добавляем статистику по категории
            ]
        ) for idx, row in filtered_cities.iterrows()
    ]
    
    return pie_chart_figure, line_chart_figure, markers

if __name__ == "__main__":
    app.run_server(debug=True)
