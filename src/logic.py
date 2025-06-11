import numpy as np
import json
import polars as pl

_PROB_PACK = [0.9995, 0.0005]
_TYPE_CARDS = [
    "Common",
    "Uncommon",
    "Rare",
    "Rare EX",
    "Full Art",
    "Full Art EX Support",
    "Special Full Art",
    "Immersive",
    "One shiny star",
    "Two shiny star",
    "Gold Crown"
]

with open("utils/prob_set.json", "r") as f:
    _DICT_DATA = pl.from_dicts(json.load(f))


def calc_prob(current_set):
    prob_imp = (
        np.array(_DICT_DATA.row(by_predicate=(pl.col("set") == current_set))[1]) / 100
    )
    prob_matrix = _PROB_PACK[0] * prob_imp[:, :-1] + _PROB_PACK[1] * prob_imp[:, -1:]

    return dict(zip(_TYPE_CARDS, prob_matrix.tolist()))
