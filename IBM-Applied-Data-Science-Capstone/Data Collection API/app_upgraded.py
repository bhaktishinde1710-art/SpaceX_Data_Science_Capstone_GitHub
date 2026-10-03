
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

df = pd.read_csv("final_spacex_dataset.csv")          # copy the CSV next to app.py
df["Block"] = df["Block"].astype(int).astype(str)     # booster block as the category
max_p = int(df["PayloadMass"].max()); min_p = int(df["PayloadMass"].min())

app = Dash(__name__)
app.layout = html.Div([
    html.H1("SpaceX Falcon 9 Launch Records Dashboard", style={"textAlign": "center"}),
    dcc.Dropdown(id="site-dropdown",
                 options=[{"label": "All Sites", "value": "ALL"}] +
                         [{"label": s, "value": s} for s in sorted(df["LaunchSite"].unique())],
                 value="ALL", placeholder="Select a Launch Site", searchable=True),
    dcc.Graph(id="success-pie"),
    html.P("Payload range (kg):"),
    dcc.RangeSlider(id="payload-slider", min=0, max=max_p, step=1000,
                    marks={i: str(i) for i in range(0, max_p + 1, 2500)}, value=[min_p, max_p]),
    dcc.Graph(id="success-payload-scatter"),
])

@app.callback(Output("success-pie", "figure"), Input("site-dropdown", "value"))
def pie(site):
    if site == "ALL":
        d = df[df["Class"] == 1].groupby("LaunchSite").size().reset_index(name="Successes")
        return px.pie(d, names="LaunchSite", values="Successes", title="Total successful launches by site")
    d = df[df["LaunchSite"] == site]["Class"].map({1: "Success", 0: "Failure"}).value_counts().reset_index()
    d.columns = ["Outcome", "Count"]
    return px.pie(d, names="Outcome", values="Count", title=f"Landing outcomes at {site}")

@app.callback(Output("success-payload-scatter", "figure"),
              [Input("site-dropdown", "value"), Input("payload-slider", "value")])
def scatter(site, rng):
    d = df[(df["PayloadMass"] >= rng[0]) & (df["PayloadMass"] <= rng[1])]
    if site != "ALL":
        d = d[d["LaunchSite"] == site]
    return px.scatter(d, x="PayloadMass", y="Class", color="Block",
                      title="Payload mass vs landing outcome (coloured by booster block)",
                      labels={"Class": "Landing outcome (1 = success)"})

if __name__ == "__main__":
    app.run(debug=True)
