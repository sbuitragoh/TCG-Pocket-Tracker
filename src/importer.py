import polars as pl
from src.utils import resource_path


def read_json_file(file_path: str = 'sets/a3-celestial-guardians.json') -> pl.DataFrame:
    df = pl.read_json(resource_path(file_path))
    df = df.drop(['health', 'attacks', 'retreatCost', 'weakness',
                                        'abilities', 'evolvesFrom'])
    return df

