import numpy as np


def calc_prob():
    
    # regular | god
    prob_pack = [0.9995, 0.0005]
    # Common | Uncommon | Rare | Rare EX | Full Art | Full Art EX/Support | Special Full Art | Immersive | Gold Crown | One shiny star | Two shiny star
    prob_1to3_reg = [100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    prob_4_reg = [0.0, 89.0, 4.952, 1.666, 2.572,
                  0.325, 0.175, 0.222, 0.04, 0.714, 0.333]
    prob_5_reg = [0.0, 56.0, 19.810, 6.664, 10.288,
                  1.29, 0.71, 0.888, 2.857, 1.333, 0.160]
    prob_1to5_g = [0.0, 0.0, 0.0, 0.0, 28.571,
                   21.433, 11.9, 2.380, 2.380, 23.809, 9.523]

    p_prob = np.array([prob_1to3_reg, prob_4_reg, prob_5_reg]).T / 100.0
    p_god = np.array(prob_1to5_g).T / 100.0
    prob_matrix = prob_pack[0] * p_prob + np.array([prob_pack[1] * p_god]*3).T
    
    prob_dict = {
        'Common':prob_matrix[0],
        'Uncommon':prob_matrix[1],
        'Rare':prob_matrix[2],
        'Rare EX':prob_matrix[3],
        'Full Art':prob_matrix[4],
        'Full Art EX/Support':prob_matrix[5],
        'Special Full Art':prob_matrix[6],
        'Immersive':prob_matrix[7],
        'Gold Crown':prob_matrix[8],
        'One shiny star':prob_matrix[9],
        'Two shiny star':prob_matrix[10]
    }
    return prob_dict
