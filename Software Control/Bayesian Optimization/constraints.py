# Import summit
import summit.domain as domain

# Set up the strategy, passing in the optimisation domain and transform
class constraints:

    RAE = domain.ContinuousVariable("RAE", "RAE", [1, 4])
    electrolyte = domain.ContinuousVariable("Electrolyte", "Electrolyte", [1, 3])
    acid = domain.ContinuousVariable("Acid", "Acid", [1, 4])
    acid_type = domain.ContinuousVariable("acid_type", "acid_type", [0, 1])
    charge = domain.ContinuousVariable("Charge", "Charge", [2, 6])
    current = domain.ContinuousVariable("Current", "Current", [4, 10])
    area = domain.ContinuousVariable("UHPLC_Area", "Area", [0, 2000], is_objective = True)

    vars = [RAE, acid, electrolyte, acid_type, charge, current, area]
    dom = domain.Domain(vars)

    def getDomain(self):
        return self.dom

    def getCols(self):
        domdict = self.dom.to_dict()
        Names = []

        for i in range(len(domdict)):
            Names.append(domdict[i].get('name'))
        return Names