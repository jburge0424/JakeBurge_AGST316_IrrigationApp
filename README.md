# 💧 Irrigation Scheduling App

A Streamlit web app that analyzes daily weather data and generates
customized irrigation recommendations. Built for AGST 316 at the
University of Nebraska–Lincoln.

## Features

- Upload any weather CSV with daily precipitation and ET data
- Interactive Plotly charts (hover, zoom, pan)
- **Adjustable deficit threshold** — tune when irrigation is triggered
- **Adjustable application amount** — set how much to apply per event
- **Manual irrigation log** — record irrigation you've already applied
  and have it factored into the schedule
- Daily decision viewer for any day in the dataset
- Downloadable CSV of the full irrigation schedule

## Required CSV columns

`Month`, `Date`, `Year`, `Time`, `Temperature_High_F`, `Temperature_Low_F`,
`Relative_Humidity_%`, `Soil_Temperature_4_inch_deep`, `Wind_Speed_mi_per_hr`,
`Solar_Radiation_Lang`, `Precipitation_inches`, `ET_inches`

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Hosted on [Streamlit Community Cloud](https://streamlit.io/cloud).
Connect this GitHub repo and point it at `app.py`.
