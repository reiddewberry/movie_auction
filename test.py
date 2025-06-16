import plotly.express as px

fig = px.line(x=[1, 2, 3], y=[4, 5, 6])
fig.write_image("owner_revenue_plot.png", width=1000, height=600, scale=1)