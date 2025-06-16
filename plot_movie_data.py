import json
from collections import defaultdict
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd

# Load your JSON data
with open('movie_data.json') as f:
    movies = json.load(f)

# Step 1: Collect all owners and all dates
owners = {"David", "Dave", "Noah", "Reid", "Seth", "Jordan", "Thomas", "Jon Reid"}
owner_colors = {
    "David":     "#00FFFF",  # Electric Blue
    "Dave":      "#FFA500",  # Bright Orange
    "Noah":      "#39FF14",  # Neon Green
    "Reid":      "#FF00FF",  # Magenta
    "Seth":      "#00BFFF",  # Deep Sky Blue
    "Jordan":    "#FFD700",  # Gold
    "Thomas":    "#8A2BE2",  # Blue Violet
    "Jon Reid":  "#FF4500",  # Orange Red
}

###
### Line plot
###
data = defaultdict(lambda: defaultdict(int))  # data[date][owner] = revenue
all_dates = set()

for movie in movies:
    owner = movie["owner"]
    owners.add(owner)
    for date_str, gross in movie["daily_total_gross"]:
        data[date_str][owner] += gross
        all_dates.add(date_str)

# Step 2: Create full date range from min to max
all_dates = pd.date_range(start="2025-05-08", end=max(pd.to_datetime(list(all_dates))))

# Step 3: Build a DataFrame per owner and forward-fill
df_list = []

for owner in owners:
    # Build a series with just that owner's data
    owner_data = {pd.to_datetime(date): data[date][owner] for date in data if owner in data[date]}
    series = pd.Series(owner_data)

    # Reindex to full date range and ffill
    series = series.reindex(all_dates).fillna(0).cumsum().ffill()
    # Store to list
    df_owner = pd.DataFrame({
        "date": series.index,
        "owner": owner,
        "total_gross": series.values
    })
    df_list.append(df_owner)

# Combine all owners' data
df = pd.concat(df_list)

latest_date = df["date"].max()
gross_by_owner = (
    df[df["date"] == latest_date]
    .groupby("owner")["total_gross"]
    .sum()
    .sort_values(ascending=False)
)

sorted_owners = gross_by_owner.index.tolist()

# Make sure owner is a categorical type so Plotly respects the order
df["owner"] = pd.Categorical(df["owner"], categories=sorted_owners, ordered=True)
###
###

###
### BAR CHART# Build the owner -> worldwide_gross sum
###
gross_by_owner = defaultdict(int)

for movie in movies:
    owner = movie["owner"]
    gross_by_owner[owner] += int(movie.get("worldwide_gross", 0))

# Create bar chart dataframe
bar_df = pd.DataFrame([
    {"owner": owner, "worldwide_gross": gross}
    for owner, gross in gross_by_owner.items()
])

# Match owner order to line chart sorting
bar_df["owner"] = pd.Categorical(bar_df["owner"], categories=sorted_owners, ordered=True)
bar_df = bar_df.sort_values(by='worldwide_gross', ascending=False).reset_index(drop=True)
print(gross_by_owner)
print(sorted_owners)
print(bar_df)
###
###



fig = px.line(df, x="date", y="total_gross", color="owner",
              title="Domestic Box Office per Owner Over Time",
              category_orders={"owner": sorted_owners},
              markers=True,
            #   template="plotly_dark",
              color_discrete_map=owner_colors)
max_date_plus_2 = (df["date"].max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
fig.update_traces(line=dict(width=4),
    marker=dict(size=10))  # <--- Thicker lines
fig.update_layout(xaxis_title="Date", yaxis_title="Box Office ($)")
fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="black",
    paper_bgcolor="black",
    xaxis=dict(range=["2025-05-08", max_date_plus_2]),
    legend=dict(
        bgcolor="rgba(0, 0, 0, 0)",  # fully transparent
        borderwidth=1,
        font=dict(color="white")
    )
)
fig.write_html("owner_domestic_line_plot.html")

bar_fig = px.bar(bar_df, x="owner", y="worldwide_gross",
                 color="owner",
                 color_discrete_map=owner_colors,
                 template="plotly_dark",
                 title="Worldwide Gross per Owner")

bar_fig.update_traces(marker_line_width=0)
bar_fig.update_layout(
    font=dict(color="white"),
    plot_bgcolor="black",
    paper_bgcolor="black",
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        borderwidth=0
    ),
    hoverlabel=dict(
        font=dict(color="white"),
        bgcolor="black",
        bordercolor="white"
    )
)
bar_fig.write_html("owner_international_bar_plot.html")

# Create subplot layout: 1 row, 2 columns
combined_fig = make_subplots(rows=2, cols=1, subplot_titles=(
    "Domestic Box Office per Owner Over Time", "Worldwide Box Office per Owner"))

# Add line traces (from fig)
for trace in fig.data:
    combined_fig.add_trace(trace, row=1, col=1)

# Add bar traces (from bar_fig)
for trace in bar_fig.data:
    combined_fig.add_trace(trace, row=2, col=1)

for annotation in combined_fig['layout']['annotations']:
    annotation['font'] = dict(size=25)  # You can set different sizes here if needed
# Update layout
combined_fig.update_layout(
    template="plotly_dark",
    showlegend=True,
    plot_bgcolor="black",
    paper_bgcolor="black",
    font=dict(color="white", size=22)
)

combined_fig.write_html("owner_box_office_plots.html")
combined_fig.show()