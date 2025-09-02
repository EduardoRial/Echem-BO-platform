import asyncio

class Rack():

    def __init__(self):
        self.xdim                = 4
        self.ydim                = 12
        self.xzero               = 101
        self.yzero               = 42
        self.xdistance           = 18
        self.ydistance           = 18
        self.groundlevelheight   = 50
    
    def get_vialpos(self, VialNumber = 0):
        VialNumber = int(VialNumber)
        if (VialNumber) < (self.xdim*self.ydim):
            if (VialNumber == 0):
                return [0,0]
            
            else:
                x = VialNumber % self.xdim
                y = (VialNumber//self.xdim)
                return [x,y]
        else:
             raise Exception("Vial index out of range")

    def get_vialXYpos(self, vialpos = [0,0]):

        if ((vialpos[0] > self.xdim) or (vialpos[1] > self.ydim)):
            raise Exception("Vial index out of range")
        
        else:
            xpos = (vialpos[0] * self.xdistance) + self.xzero
            ypos = (vialpos[1] * self.ydistance) + self.yzero
            return [xpos,ypos]
    
    def FindVial(self, Vial):
        return (self.get_vialXYpos(self.get_vialpos(Vial)))
rack = Rack()
