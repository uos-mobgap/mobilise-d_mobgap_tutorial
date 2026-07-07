# %% [markdown]
# # MobGap Tutorial
# 
# The data we captured today is stored in a ".cwa" file. This is a compressed, space efficient format where values are represented in bytes that must be transformed into readable values. Luckily, we've built some functions to do this.
# 
# First, let's get a list of all the ".cwa" files in the current folder. Make sure your file is in the same folder as this script and run the code below.

# %%
import os
def get_paths_with_extension(extension):
    paths = []
    dataset_folder = os.path.join(os.getcwd())

    for root, dirs, files in os.walk(dataset_folder):
        for file in files:
            if file.lower().endswith(extension):
                path = os.path.join(root, file)
                if not ".venv" in path:
                    paths.append(path)
    
    return paths

cwa_files = get_paths_with_extension(".cwa")

print("Here is the list of all our \".cwa\" files:")
print(cwa_files)

# %% [markdown]
# Now let's run the following cell, which imports some functions from our "functions.py" file and uses them to read the data from the ".cwa" file.
# 
# Then, we'll plot this data to see what we're working with.

# %%
from functions import *
import pandas as pd

if len(cwa_files) > 1:
    print("Error, more than 1 \".cwa\" file in your folder, make sure you just have your file from today in there!")
else:
    samples = get_cwa_data(cwa_files[0], resample = True, prints = 0)

# note that we use display to make things look nice in notebooks, rather than print.
# If you want to see why, try replacing the following "display" with "print"...
display(samples.head(10))

# %% [markdown]
# Great! Now let's plot the data to see what this actually looks like. If you want, you can also see what the other axes look like by swapping out "accel_x" for:
# - accel_y
# - accel_z
# - gyro_x
# - gyro_y
# - gyro_z
# 
# As seen in the table above. You can even plot the "timestamp" if you like but it'll just be a straight line.

# %%
samples["accel_x"].plot(figsize = (20, 5)) # note that figsize contains the x and y sizes for the figure. Have a play with these to see what happens.

# %% [markdown]
# We can be a bit smarter with our plots. If we use matplotlib, we can select a specific region of the data to plot. In the cell below, enter a start and end index (start_id and end_id) that you'd like to see and run the cell to see "accel_x" plotted against timestamp so that we can see exactly when this data was recorded. Again we can change "accel_x" to any of the columns to see them plotted over time.

# %%
import matplotlib.pyplot as plt    # we'll use matplotlib for this plot

start_id = 0    # the first point we want to plot - feel free to change
end_id = 1000   # the last point we want to plot - feel free to change

samples_to_plot = samples.iloc[start_id:end_id] # here we make a copy of our table, but use iloc to get just the values from the start_id to the end_id

plt.figure(figsize=(20, 5))                                   # first, we tell matplotlib how big the figure will be.
plt.plot(samples_to_plot["timestamp"], samples_to_plot["accel_x"]) # next, we plot the x and y axes as columns from our table
plt.show()                                                    # finally, we show the figure

# %% [markdown]
# Now, don't worry too much about these following cells. Basically, we currently have our time in <b>human-readable time</b>, but MobGap needs the time in <b>unix time</b>.
# 
# Unix time is the number of seconds since the <b>unix epoch</b> which was 1-1-1970.
# 
# Run the cell below and see what this looks like. It should be an array of times starting at about 1.8 billion seconds.

# %%
reformatted_time = samples["timestamp"].astype('int64') // 10**9  # convert nanoseconds to seconds
reformatted_time = reformatted_time.values.reshape(-1, 1).astype(float)

display(reformatted_time)

# %% [markdown]
# Now we'll look at the start time by getting the first item in the timestamp column from our data, and formatting it as <b>day-mon-year hh:mm:ss</b>.
# 
# You should see today's date, and the time that we started recording.

# %%
start_date_time = samples["timestamp"].iloc[0].strftime('%d-%b-%Y %H:%M:%S')
print(start_date_time)

# %% [markdown]
# Next we'll set our sample rate.
# 
# These sensors record 100 samples per second - 100 Hz.

# %%
fs = 100
#fs = len(samples)/(reformatted_time[-1][0] - reformatted_time[0][0])
print(fs)

# %%
data = {
    "TimeMeasure1": {
        "Test1": {
            "Trial1": {
                "SU": {
                    "LowerBack": {
                        "Fs": {
                            "Acc": fs,
                            "Gyr": fs
                        },
                        "Acc": samples[["accel_x", "accel_y", "accel_z"]].values.astype(float),
                        "Gyr": samples[["gyro_x", "gyro_y", "gyro_z"]].values.astype(float),
                        "Timestamp": reformatted_time
                    }
                }, 
                "StartDateTime": start_date_time,
                "TimeZone": "Europe/UK"
            }
        }
    }
}

data = {"data": data}

# %%
gender = "M"
handedness = "R"
age = 26
weight = 80.4
height = 183
sensor_height = 111

infoForAlgo = {
    "TimeMeasure1": {
        "Subject_ID": "1",
        "Cohort": "HA",
        "Gender": gender,
        "Handedness": handedness,
        "Age": age,
        "Weight": weight,
        "Height": height,
        "SensorHeight": sensor_height,
        "WalkingAid_01": 0,
        "WalkingAid_Side": "",
        "WalkingAid_Description": "",
        "SensorType_SU": "AX6",
        "SensorAttachment_SU": "Body-Worn"
    }
}

infoForAlgo = {"infoForAlgo": infoForAlgo}

# %%
current_dir = os.getcwd()                                   # get current working directory (cwd)
target_dir = os.path.join(current_dir, r'Dataset/HA/1')     # define the target directory relative to the current directory
if not os.path.exists(target_dir):                          # check if the folders already exist
   os.makedirs(target_dir)                                  # if they dont, make the folders

# %%
from scipy.io import savemat

savemat(os.path.join(target_dir, "infoForAlgo.mat"), infoForAlgo, do_compression=False)
savemat(os.path.join(target_dir, "data.mat"), data, do_compression=False)

# %%
from mobgap.data import GenericMobilisedDataset

mat_files = get_paths_with_extension(".mat")
mat_files = [file for file in mat_files if file.endswith("data.mat")]
print(mat_files)
dataset = GenericMobilisedDataset(
    paths_list = mat_files,
    test_level_names = ["TimeMeasure", "Test", "Trial"], # This is the structure (without numbers) of the data inside the data.mat struct.
    measurement_condition = "laboratory",
    parent_folders_as_metadata=["dataset", "cohort", "subject"] # these are the column headings for the metadata, the columns get populated with the folder names.
)

print(dataset)

# %%
from mobgap.pipeline import MobilisedPipelineHealthy

pipeline = MobilisedPipelineHealthy()
pipeline = pipeline.safe_run(dataset)
print("Pipeline finished running!")

# %%
display(pipeline.aggregated_parameters_) # all parameters across all walking bouts

# %%
display(pipeline.per_wb_parameters_.head(5))     # first 5 per-walking-bout parameters

# %%
plt.figure(figsize = (4, 3))
plt.hist(pipeline.per_wb_parameters_["cadence_spm"], bins = 10)
plt.show()

# %%



