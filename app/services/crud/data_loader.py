# data_loader.py
from sqlmodel import Session, select
from models import Hall, Concert, Artist, Author, Composition, ConcertArtistLink, ConcertCompositionLink, Purchase
from datetime import datetime, timedelta
import pandas as pd


def get_or_create(session, model, **kwargs):
    instance = session.exec(select(model).filter_by(**kwargs)).first()
    if instance:
        return instance
    instance = model(**kwargs)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def load_halls(session: Session, df_halls: pd.DataFrame):
    print(f"Загружаем {len(df_halls)} залов из Excel")
    for _, row in df_halls.iterrows():
        # Обрабатываем NaN значения
        address = row.get("Adress")
        if pd.isna(address):
            address = None
            
        latitude = row.get("Lat")
        if pd.isna(latitude):
            latitude = None
            
        longitude = row.get("Lon")
        if pd.isna(longitude):
            longitude = None
            
        get_or_create(
            session,
            Hall,
            name=row["HallName"],
            concert_count=row.get("count", 0),
            address=address,
            latitude=latitude,
            longitude=longitude,
        )
    count = session.exec(select(Hall)).all()
    print(f"В базе теперь {len(count)} залов")


def load_concerts(session: Session, df_concerts: pd.DataFrame):
    print(f"Загружаем {len(df_concerts)} концертов из Excel")
    for _, row in df_concerts.iterrows():
        hall = get_or_create(session, Hall, name=row["HallName"])
        
        # Обрабатываем NaN значения
        genre = row.get("Genre")
        if pd.isna(genre):
            genre = None
            
        price = row.get("Price")
        if pd.isna(price):
            price = None
            
        link = row.get("link")
        if pd.isna(link):
            link = None
        
        concert = get_or_create(
            session,
            Concert,
            external_id=row["ShowId"],
            name=row["ShowName"],
            datetime=pd.to_datetime(row["ShowDate"]),
            duration=pd.to_timedelta(row["ShowLong"]),
            genre=genre,
            price=price,
            is_family_friendly=bool(row.get("Family", False)),
            tickets_available=bool(row.get("Tickets", False)),
            link=link,
            hall_id=hall.id,
        )
    count = session.exec(select(Concert)).all()
    print(f"В базе теперь {len(count)} концертов")


def load_artists(session: Session, df_artists: pd.DataFrame):
    print(f"Загружаем {len(df_artists.drop_duplicates(['ShowNum', 'Artists']))} артистов из Excel")
    for _, row in df_artists.drop_duplicates(["ShowNum", "Artists"]).iterrows():
        artist = get_or_create(
            session,
            Artist,
            name=row["Artists"],
            is_special=bool(row.get("Spetial", False))
        )
        concert = session.exec(select(Concert).where(Concert.external_id == row["ShowNum"])).first()
        if concert:
            link = get_or_create(
                session,
                ConcertArtistLink,
                concert_id=concert.id,
                artist_id=artist.id
            )
    count = session.exec(select(Artist)).all()
    print(f"В базе теперь {len(count)} артистов")


def load_compositions(session: Session, df_details: pd.DataFrame):
    print(f"Загружаем {len(df_details.drop_duplicates(['ShowNum', 'Author', 'Programm']))} композиций из Excel")
    for _, row in df_details.drop_duplicates(["ShowNum", "Author", "Programm"]).iterrows():
        author = get_or_create(session, Author, name=row["Author"])
        composition = get_or_create(
            session,
            Composition,
            name=row["Programm"],
            author_id=author.id
        )
        concert = session.exec(select(Concert).where(Concert.external_id == row["ShowNum"])).first()
        if concert:
            link = get_or_create(
                session,
                ConcertCompositionLink,
                concert_id=concert.id,
                composition_id=composition.id
            )
    count = session.exec(select(Composition)).all()
    print(f"В базе теперь {len(count)} композиций")



def load_purchases(session: Session, df_ops: pd.DataFrame):
    print(f"Загружаем {len(df_ops.drop_duplicates(['OpId']))} покупок из Excel")
    for _, row in df_ops.drop_duplicates(["OpId"]).iterrows():
        # Обрабатываем NaN значения
        price = row.get("Price")
        if pd.isna(price):
            price = None
            
        concert = session.exec(select(Concert).where(Concert.external_id == row["ShowId"])).first()
        if concert:
            get_or_create(
                session,
                Purchase,
                external_op_id=row["OpId"],
                user_external_id=str(row["ClientId"]),
                concert_id=concert.id,
                purchased_at=pd.to_datetime(row["OpDate"]),
                price=price
            )
    count = session.exec(select(Purchase)).all()
    print(f"В базе теперь {len(count)} покупок")