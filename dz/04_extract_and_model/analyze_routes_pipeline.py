
import pandas as pd

def analyze_route(route_ids, i, GoodShows_indexed, ShowDetails_indexed, ArtistDetails_indexed,
                  HallsTime, RouteRange, RouteAuthors, RouteSpetialArtist):
    route_shows = GoodShows_indexed.loc[route_ids]
    show_details = ShowDetails_indexed.loc[route_ids]
    artist_details = ArtistDetails_indexed.loc[route_ids]

    RouteRange.at[i, 'Sostav'] = route_ids
    RouteRange.at[i, 'Days'] = route_shows['ShowDate'].dt.date.nunique()
    RouteRange.at[i, 'Concerts'] = len(route_ids)
    RouteRange.at[i, 'Halls'] = route_shows['HallName'].nunique()
    RouteRange.at[i, 'Genre'] = route_shows['Genre'].nunique()
    RouteRange.at[i, 'ShowTime'] = route_shows['ShowLong'].sum()
    RouteRange.at[i, 'Costs'] = route_shows['Price'].sum()
    RouteRange.at[i, 'Musician'] = artist_details['Artists'].nunique()
    RouteRange.at[i, 'Composer'] = show_details['Author'].nunique()
    RouteRange.at[i, 'programm'] = show_details['Programm'].nunique()
    RouteRange.at[i, 'FamilyConc'] = route_shows['Family'].sum()

    halls = route_shows['HallName'].reset_index(drop=True)
    trans_times = sum(
        HallsTime[halls.iloc[j]][halls.iloc[j+1]]
        for j in range(len(halls) - 1)
    )
    RouteRange.at[i, 'TransTime'] = trans_times

    start_times = route_shows['ShowDate'].reset_index(drop=True)
    durations = route_shows['ShowLong'].reset_index(drop=True)
    waits = start_times.shift(-1) - (start_times + durations)
    RouteRange.at[i, 'WaitTime'] = waits[:-1].sum()

    authors = show_details['Author'].value_counts()
    RouteAuthors.loc[i, authors.index] = authors.values

    artists = artist_details['Artists'].value_counts()
    RouteSpetialArtist.loc[i, artists.index] = artists.values

# ===== Основной код пайплайна =====

# Предполагается, что переменные GoodRoute, GoodShows, ShowDetails, ArtistDetails, HallsTime, AuthorStats, ArtistStats уже определены

num_routes = len(GoodRoute)

# Индексируем данные
GoodShows_indexed = GoodShows.set_index("ShowNum")
ShowDetails_indexed = ShowDetails
ArtistDetails_indexed = ArtistDetails

# Инициализация таблиц
RouteRange = pd.DataFrame(index=range(num_routes), columns=[
    'Sostav', 'Days', 'Concerts', 'Halls', 'Genre',
    'ShowTime', 'TransTime', 'WaitTime', 'Costs',
    'Musician', 'Composer', 'programm', 'FamilyConc'
])
RouteRange[:] = 0

RouteAuthors = pd.DataFrame(0, index=RouteRange.index, columns=AuthorStats.index)
RouteSpetialArtist = pd.DataFrame(0, index=RouteRange.index, columns=ArtistStats.index)

# Обработка маршрутов
for i, route in enumerate(GoodRoute):
    if i % 1000 == 0:
        print(f"Обработка маршрута {i}/{num_routes}")
    analyze_route(route, i, GoodShows_indexed, ShowDetails_indexed, ArtistDetails_indexed,
                  HallsTime, RouteRange, RouteAuthors, RouteSpetialArtist)

# Пример сохранения
RouteRange.to_csv("RouteRange.csv", index=False)
RouteAuthors.to_csv("RouteAuthors.csv")
RouteSpetialArtist.to_csv("RouteSpetialArtist.csv")
