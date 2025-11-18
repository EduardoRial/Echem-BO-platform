import os
import time
import TSEMO_iter as TSEMO_iter
import pandas as pd
import numpy as np
import constraints_edu_MO as constraints
from summit import DataSet
import random, numpy as np, torch

SEED = 996 #any number
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


# Specify file paths
output_file_path = 'xnewtrue1.csv'
monitor_file_path = 'ynewtrue1.csv'
result_file_path = 'results_electro_1_MO.csv'

def convert_results_to_init(results):
    return (pd.concat([results.iloc[:,7:13], results.iloc[:,0:2]], axis = 1))

# init file path depreciated in future version
init_file_path = 'init.csv'

con = constraints.constraints()

#init = pd.read_csv(init_file_path, sep = ",", header = None)
#initfiltered = pd.concat([init.iloc[:,1:6], init.iloc[:,0]], axis = 1)
initfiltered = convert_results_to_init(pd.read_csv(result_file_path,sep = ",", header = None))
print(initfiltered)
initfiltered.columns = con.getCols()
print(initfiltered)
maxiter = 60
iter = TSEMO_iter.TSEMO_iteration()


line = iter.suggest_next(DataSet.from_df(initfiltered))
print(line[line.data_columns])

with open(output_file_path, 'w') as output_file:
    output_file.write(line[line.data_columns].iloc[:,0:5].to_csv(sep = ',', header = None, index = None).replace('\r', ''))
print(line[line.data_columns].to_csv(sep = ',', header = None, index = None).replace('\r', ''))

# Open the output file for writing
    # Read each line from the input file
for i in range(maxiter):
    # Wait for the monitor file to be modified
    current_time = os.path.getmtime(monitor_file_path)
    while True:
        time.sleep(1)
        if os.path.getmtime(monitor_file_path) > current_time:

            #write results of previous experiment to results file
            outputs = pd.read_csv(monitor_file_path, sep = ';', header = None)
            outputs = outputs.iloc[:,0:13]
            print(outputs)
            outputs_str = outputs.to_csv(sep = ",",index=False, header = False)
            outputs_str = outputs_str.replace('\n', '')

            result = outputs_str
            try:
                with open(result_file_path, 'a') as result_file:
                    result_file.write(result)
            except:
                with open(result_file_path, 'a') as result_file:
                    result_file.write('0,0,0,0,0,0,0,0,0,0,0')
             
            print("")                       
            print(i)
            print("Result:")
            print(result)
            print("")

            #read in all previous results and suggest new experiment
            results = pd.read_csv(result_file_path, sep = ',', header = None)
            resline = pd.concat([results.iloc[:,7:13], results.iloc[:,0:2]], axis = 1)
            resline.columns = con.getCols()

            line = iter.suggest_next(DataSet.from_df(resline))

            with open(output_file_path, 'w') as output_file:
                output_file.write(line[line.data_columns].iloc[:,0:5].to_csv(sep = ',', header = None, index = None).replace('\r', ''))
            print(line[line.data_columns].to_csv(sep = ',', header = None, index = None).replace('\r', ''))
            time.sleep(30)
            break
print("Done")