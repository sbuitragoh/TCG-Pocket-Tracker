import polars as pl
from src.utils import resource_path


def read_json_file(file_path: str = 'sets/a3-celestial-guardians.json') -> pl.DataFrame:
    df = pl.read_json(resource_path(file_path))
    df = df.drop(['health', 'attacks', 'retreatCost', 'weakness',
                                        'abilities', 'evolvesFrom'])
    return df


def grouped_data(data: pl.DataFrame, by: str) -> list[pl.DataFrame]:
    data_copy = data.copy()
    rarities = data_copy[by].unique()
    df_grouped = [data_copy[data_copy[by] == rarity].reset_index()
                  for rarity in rarities]
    return df_grouped
