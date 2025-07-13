"""
    При инициализации проекта — первичном запуске базы данных —
    из этого набора файлов подтянутся все необходимые свединия
    о фестиваля: транзакции, концерты, артисты, программы, маршруты
    и т.д.
"""

############################################################################
####            Базовые параметры фестиваля                            #####
############################################################################

## Параметры фестиваля (Агрегированные данныне по дням, количеству концертов и т.д.)
#FESTIVAL_PARAMS_PATH = 'data/fest_days.xlsx'

## История всех покупок
TRANSACTIONS_PATH = 'data/GoodOperations.xlsx'
# TRANSACTIONS_PATH = 'data/GoodOperetions-OneDay.xlsx'

## Концерты фестиваля
CONCERTS_PATH = 'data/ConcertList-good.xlsx'

## Участие артистов в концертах
ARTISTS_PATH = 'data/ArtistDetails-good.xlsx'

## Авторы и произведения в концертах
PROGRAMM_PATH = 'data/show_details.xlsx'

## Список залов
HALLS_LIST_PATH = 'data/HallList-good.xlsx'


############################################################################
####            Маршруты и перемещения                                 #####
############################################################################

## Маршруты фестиваля
ROUTES_PATH = 'data/Routes-good.xlsx'

## Таблица переходов между залами
# HALLS_TRANSITIONS_PATH = 'data/HallsTime-good.xlsx'

## Матрица не совместимости концертов
# MATRIX_UNCOMB_PATH = 'data/MatrixUncomb.xlsx'

## Матрица повторности концертов
# MATRIX_DOUBLED_PATH = 'data/MatrixDoubled.xlsx'