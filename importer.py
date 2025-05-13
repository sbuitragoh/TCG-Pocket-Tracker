import pandas as pd

def read_json_file(file_path: str = 'a3-celestial-guardians.json') -> pd.DataFrame:
    df = pd.read_json(file_path)
    return df

def clean_db(data: pd.DataFrame) -> pd.DataFrame:
    data_copy = data.copy()
    data_copy = data_copy.drop(columns=['subtype', 'health', 'attacks', 'retreatCost', 'weakness', 
                                        'abilities', 'evolvesFrom'])
    return data_copy

def grouped_data(data: pd.DataFrame, by: str) -> list[pd.DataFrame]:
    data_copy = data.copy()
    rarities = data_copy[by].unique()
    df_grouped = [data_copy[data_copy[by] == rarity].reset_index() for rarity in rarities]
    return df_grouped

