# Import summit
from summit.strategies import TSEMO
import constraints_edu_new as constraints

class TSEMO_iteration:
    con = constraints.constraints()
    strategy = TSEMO(con.getDomain(), n_spectral_points = 4000)
    
    def suggest_next(self, previous):
        next_experiment = TSEMO_iteration.strategy.suggest_experiments(1,prev_res=previous)
        return next_experiment