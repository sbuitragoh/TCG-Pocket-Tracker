import sys
import os
import polars as pl


def resource_path(relative_path):
    """Get absolute path to resource, works for dev, PyInstaller, and external folders."""
    
    path = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(path):
        return path

    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def ensure_row_index(df: pl.DataFrame, name: str = "row_idx") -> pl.DataFrame:
    return df if name in df.columns else df.with_row_index(name=name)

def safe_str(value):
    if isinstance(value, pl.Series):
        return str(value.item()) if value.len() > 0 else ""
    return str(value) if value is not None else ""

def get_set_df(df:pl.DataFrame) -> pl.DataFrame:
    set_rarities = ['Common', 'Uncommon', 'Rare', 'Rare EX']
    df = ensure_row_index(df)
    return df.filter(pl.col('rarity').is_in(set_rarities))
