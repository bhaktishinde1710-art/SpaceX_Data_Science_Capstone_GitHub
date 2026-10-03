# ============================================================
# ADD-ON FOR YOUR CAPSTONE: Folium markers + proximity, and upgraded Dash app
# Run AFTER your main script (needs data/final_spacex_dataset.csv).
# ============================================================
import math
import pandas as pd
import folium
from folium.plugins import MarkerCluster, MousePosition

df = pd.read_csv("data/final_spacex_dataset.csv")

# ---------- A. Folium: launch sites + success/failure markers ----------
sites = (df.groupby("LaunchSite")[["Latitude", "Longitude"]].first().reset_index())
m = folium.Map(location=[sites.Latitude.mean(), sites.Longitude.mean()], zoom_start=4)

# circle + label for each launch site
for _, r in sites.iterrows():
    folium.Circle([r.Latitude, r.Longitude], radius=1000, color="#d35400", fill=True).add_to(m)
    folium.Marker([r.Latitude, r.Longitude],
                  icon=folium.DivIcon(html=f'<div style="font-size:12px;color:#d35400;font-weight:bold">{r.LaunchSite}</div>')
                  ).add_to(m)

# one green (success) / red (failure) marker per launch, clustered
cluster = MarkerCluster().add_to(m)
for _, r in df.iterrows():
    folium.Marker([r.Latitude, r.Longitude],
                  icon=folium.Icon(color="green" if r.Class == 1 else "red"),
                  popup=f"{r.LaunchSite} | flight {r.FlightNumber} | {'Success' if r.Class == 1 else 'Failure'}"
                  ).add_to(cluster)

MousePosition().add_to(m)          # hover over the map: lat/lon shows at the bottom-right
m.save("outputs/folium_markers.html")
print("Saved outputs/folium_markers.html -> screenshot it for 'all sites' and 'success/failure' slots")

# ---------- B. Proximity analysis ----------
# Fill these by hovering over the map (MousePosition, bottom-right of the map) on the nearest
# coastline / railway / highway / city point for EACH site, then paste the lat/lon.
# The CCAFS values are only a starting point - VERIFY them on the map.
PROX = {

    "CCAFS SLC 40": {
        "coastline": (28.56409, -80.56806),
        "railway": (28.57217, -80.58528),
        "highway": (28.56385, -80.57088),
        "city": (28.10469, -80.64784)
    },

    "KSC LC 39A": {
        "coastline": (28.60283, -80.58815),
        "railway": (28.57314, -80.65398),
        "highway": (28.57307, -80.65553),
        "city": (28.10469, -80.64784)
    },

    "VAFB SLC 4E": {
        "coastline": (34.63470, -120.62531),
        "railway": (34.63585, -120.62401),
        "highway": (34.70480, -120.56940),
        "city": (34.64253, -120.47331)
    }
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

rows = []
pm = folium.Map(location=[sites.Latitude.mean(), sites.Longitude.mean()], zoom_start=4)
for _, s in sites.iterrows():
    pts = PROX.get(s.LaunchSite, {})
    row = {"Launch site": s.LaunchSite}
    folium.Marker([s.Latitude, s.Longitude], popup=s.LaunchSite).add_to(pm)
    for name in ["coastline", "railway", "highway", "city"]:
        pt = pts.get(name)
        if pt is None:
            row[name + " (km)"] = None
            continue
        dist = haversine(s.Latitude, s.Longitude, *pt)
        row[name + " (km)"] = round(dist, 2)
        folium.Marker(pt, icon=folium.DivIcon(
            html=f'<div style="font-size:11px;color:#1d4ed8;font-weight:bold">{dist:.2f} km</div>')).add_to(pm)
        folium.PolyLine([[s.Latitude, s.Longitude], list(pt)], weight=2, color="#1d4ed8").add_to(pm)
    rows.append(row)

pm.save("outputs/folium_proximity.html")
prox_table = pd.DataFrame(rows)
print(prox_table.to_string(index=False))      # copy these numbers into the report table
prox_table.to_csv("outputs/proximity_distances.csv", index=False)

# ============================================================
# C. UPGRADED DASH APP  (save as app.py in Plotly Dash/dashboard and run: python app.py)
# ============================================================
DASH_APP = r'''
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
'''
open("app_upgraded.py", "w").write(DASH_APP)
print("Wrote app_upgraded.py -> move it to Plotly Dash/dashboard/app.py, copy the CSV there, then run it")