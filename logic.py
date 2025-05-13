import numpy as np


def calc_prob():

    # regular | god
    prob_pack = [0.9995, 0.0005] 
    ## Common | Uncommon | Rare | Rare EX | Full Art | Full Art EX/Support | Immersive | Gold Crown | One shiny star | Two shiny star
    prob_1to3_reg = [100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    prob_4_reg = [0.0, 89.0, 4.952, 1.666, 2.572, 0.5, 0.222, 0.04, 0.714, 0.333]
    prob_5_reg = [0.0, 56.0, 19.810, 6.664, 10.288, 2.0, 0.888, 2.857, 1.333, 0.160]
    prob_1to5_g = [0.0, 0.0, 0.0, 0.0, 28.571, 33.333, 2.380, 2.380, 23.809, 9.523]

    p_prob = np.array([prob_1to3_reg, prob_4_reg, prob_5_reg]).T / 100.0
    p_god = np.array(prob_1to5_g).T / 100.0

    return prob_pack[0] * p_prob + np.array([prob_pack[1] * p_god]*3).T
