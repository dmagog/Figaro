from typing import Optional
from sqlmodel import SQLModel, Field

class Route(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    Sostav: str
    Days: int
    Concerts: int
    Halls: int
    Genre: Optional[str] = None
    ShowTime: float
    TransTime: float
    WaitTime: float
    Costs: float
    Musician: Optional[str] = None
    Composer: Optional[str] = None
    programm: Optional[str] = None
    FamilyConc: Optional[int] = None
    TransTime_percent: Optional[float] = Field(default=None, alias="TransTime_%")
    WaitTime_percent: Optional[float] = Field(default=None, alias="WaitTime_%")
    TransTime_Score: Optional[float] = None
    WaitTime_Score: Optional[float] = None
    Trans_Wait_percent: Optional[float] = Field(default=None, alias="Trans-Wait_%")
    Density: Optional[float] = None
    HallChanges: Optional[int] = None
    Top5Authors: Optional[int] = None
    Top5AuthorsShare: Optional[float] = None
    RareAuthorsShare: Optional[float] = None
    RecommendedArtistsRatio: Optional[float] = None
    RecommendedPiecesRatio: Optional[float] = None
    ComfortScore: Optional[float] = None
    ComfortLevel: Optional[str] = None
    RareAuthorsShare_qnorm: Optional[float] = None
    RecommendedPiecesRatio_qnorm: Optional[float] = None
    RecommendedArtistsRatio_qnorm: Optional[float] = None
    AvgWorksPerConcert: Optional[float] = None
    DepthScore: Optional[float] = None
    GenreDiversityScore: Optional[float] = None
    IntellectScore: Optional[float] = None
    IntellectCategory: Optional[str] = None
    IntellectScoreLabel: Optional[str] = None
    AuthorBalance: Optional[float] = None
    ComfortScoreLabel: Optional[str] = None
    AuthorBalanceLabel: Optional[str] = None
    Top5AuthorsShareLabel: Optional[str] = None
    RareAuthorsShareLabel: Optional[str] = None
    GMM_Cluster: Optional[int] = None 