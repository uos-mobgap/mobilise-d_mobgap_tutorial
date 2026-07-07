# %% [markdown]
# # MobGap Tutorial Experimental (CWA -> pipeline via mobgap.data.load_cwa_as_dataset)
# 
# This recreates `mobilise-d_mobgap_tutorial/mobgap_tutorial_johnny.py`, but loads `.cwa`
# files directly with `mobgap.data.load_cwa_as_dataset` instead of converting to MATLAB first.
# 
# The plotting and pipeline sections follow the John Mitchell's tutorial as closely as possible.
# Differences:
# - Sensor columns use MobGap names (`acc_x`, `gyr_x`, ...) rather than `accel_x`, `gyro_x`, ...
# - Acceleration is in m/s^2 (MobGap convention), not in g
# - No intermediate `.mat` files are written, the CWA file goes straight into a dataset
# - **Resampling:** this path uses MobGap's `Resample` (`scipy.signal.resample`), not the linear `numpy.interp` re-gridding in `get_cwa_data(resample=True)`. Pipeline outputs may therefore differ from `MobGap_Tutorial.ipynb` even on the same `.cwa` file. See `reports/cwa-to-mobgap-paths.md` §5. To skip MobGap's resampling step entirely, pass `resample_hz=None`.

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
# Now let's load the CWA file with MobGap's built-in loader.
# 
# `load_cwa_as_dataset` wraps the Open Movement reader, converts units/column names to MobGap
# conventions, and returns a dataset that can be passed into MobGap pipeline.
# 
# We pass `resample_hz=100` below to match the nominal AX3 rate. That applies MobGap's Fourier
# resampler — it does **not** replicate Johnny's tutorial, which always re-grids with linear
# interpolation via `get_cwa_data(resample=True)`.

# %%
from datetime import datetime, timezone
from IPython.display import display

from mobgap.data import load_cwa_as_dataset

if len(cwa_files) > 1:
    print("Error, more than 1 \".cwa\" file in your folder, make sure you just have your file from today in there!")
elif len(cwa_files) == 0:
    raise FileNotFoundError("No .cwa file found in the current folder.")
else:
    participant_metadata = {
        "cohort": "HA",
        "height_m": 183 / 100,
        "sensor_height_m": 111 / 100,
        
        # optional
        "age": 26,
        "weight": 80.4,
        "gender": "M",
        "handedness": "R",
        "subject_id": 1,
    }

    # resample_hz=100: MobGap Fourier resampling (scipy), not get_cwa_data linear interp.
    # use resample_hz=None to keep the Open Movement decoder output unchanged.
    dataset = load_cwa_as_dataset(
        cwa_files[0],
        participant_metadata,
        recording_metadata={"measurement_condition": "laboratory"},
        include_time_index=True,  # utc unix seconds for plotting
        resample_hz=100,
    )

    datapoint = dataset[0]
    samples = datapoint.data_ss

# note that we use display to make things look nice in notebooks, rather than print.
# If you want to see why, try replacing the following "display" with "print"...
display(samples.head(10))

# %% [markdown]
# Great! Now let's plot the data to see what this actually looks like. If you want, you can also see what the other axes look like by swapping out "acc_x" for:
# - acc_y
# - acc_z
# - gyr_x
# - gyr_y
# - gyr_z
# 
# As seen in the table above. The index is UTC Unix time in seconds (not a pandas `DatetimeIndex`, which can segfault on some HPC module stacks). For readable time axes, convert with `datetime.fromtimestamp` when plotting (see below).

# %%
samples["acc_x"].plot(figsize=(20, 5))

# %% [markdown]
# We can be a bit smarter with our plots. If we use matplotlib, we can select a specific region of the data to plot. In the cell below, enter a start and end index (start_id and end_id) that you'd like to see and run the cell to see "acc_x" plotted against time so that we can see exactly when this data was recorded. Again we can change "acc_x" to any of the columns to see them plotted over time.

# %%
import matplotlib.pyplot as plt
from datetime import datetime, timezone

start_id = 0
end_id = 1000

samples_to_plot = samples.iloc[start_id:end_id]
time_axis = [datetime.fromtimestamp(t, tz=timezone.utc) for t in samples_to_plot.index]

plt.figure(figsize=(20, 5))
plt.plot(time_axis, samples_to_plot["acc_x"])
plt.show()

# %% [markdown]
# In Johnny's tutorial we converted timestamps to Unix time and built MATLAB structs before running MobGap.
# With `load_cwa_as_dataset` that conversion happens internally, so we can skip straight to inspecting
# the recording start time and sampling rate.

# %%
start_time_unix = datapoint.recording_metadata["cwa_start_time"]
start_date_time = datetime.fromtimestamp(start_time_unix, tz=timezone.utc).strftime("%d-%b-%Y %H:%M:%S")
print(start_date_time)

# %% [markdown]
# Next we'll check our sample rate.
# 
# These sensors record 100 samples per second — 100 Hz. Printing `100` here does not mean the
# waveform was re-gridded the same way as in Johnny's tutorial; see the resampling note above.

# %%
fs = datapoint.sampling_rate_hz
print(fs)

# %% [markdown]
# Skipping `.mat` files step since the dataset is in already in the format expected by MobGap pipeline.

# %%
print(dataset)

# %%
from mobgap.pipeline import MobilisedPipelineHealthy

pipeline = MobilisedPipelineHealthy()
pipeline = pipeline.safe_run(dataset)
print("Pipeline finished running!")

# %%
display(pipeline.aggregated_parameters_)

# %%
display(pipeline.per_wb_parameters_.head(5))

# %%
plt.figure(figsize=(4, 3))
plt.hist(pipeline.per_wb_parameters_["cadence_spm"], bins=10)
plt.show()

# %%




