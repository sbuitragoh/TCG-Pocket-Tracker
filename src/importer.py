import pandas as pd
from src.utils import resource_path


def read_json_file(file_path: str = 'sets/a3-celestial-guardians.json') -> pd.DataFrame:
    df = pd.read_json(resource_path(file_path))
    return df


def clean_db(data: pd.DataFrame) -> pd.DataFrame:
    data_copy = data.copy()
    data_copy = data_copy.drop(columns=['health', 'attacks', 'retreatCost', 'weakness',
                                        'abilities', 'evolvesFrom'])
    return data_copy


def grouped_data(data: pd.DataFrame, by: str) -> list[pd.DataFrame]:
    data_copy = data.copy()
    rarities = data_copy[by].unique()
    df_grouped = [data_copy[data_copy[by] == rarity].reset_index()
                  for rarity in rarities]
    return df_grouped
