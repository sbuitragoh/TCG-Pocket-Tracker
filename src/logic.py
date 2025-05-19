import numpy as np
import json

def calc_prob(current_set):
    
    # regular | god
    prob_pack = [0.9995, 0.0005]
    # Common | Uncommon | Rare | Rare EX | Full Art | Full Art EX Support | Special Full Art | Immersive | Gold Crown | One shiny star | Two shiny star
    with open('utils/prob_set.json', 'r') as f:
        data = json.load(f)

    for d in data:
        if d['set'] == current_set:
            prob_imp = np.array(d['prob'])

    
    p_prob = prob_imp[:, 0:-1] / 100
    p_god = np.reshape(prob_imp[:, -1] / 100, (-1, 1))
    prob_matrix = prob_pack[0] * p_prob + np.tile(p_god, (1,3))
    
    prob_dict = {
        'Common':prob_matrix[0],
        'Uncommon':prob_matrix[1],
        'Rare':prob_matrix[2],
        'Rare EX':prob_matrix[3],
        'Full Art':prob_matrix[4],
        'Full Art EX Support':prob_matrix[5],
        'Special Full Art':prob_matrix[6],
        'Immersive':prob_matrix[7],
        'Gold Crown':prob_matrix[8],
        'One shiny star':prob_matrix[9],
        'Two shiny star':prob_matrix[10]
    }
    return prob_dict
