from functools import partial
import struct
import pandas as pd
from datetime import datetime
import numpy as np

def cwa_timestamp_to_datetime(time):
    # Timestamps are packed into a 32-bit value: (MSB) YYYYYYMM MMDDDDDh hhhhmmmm mmssssss (LSB)
    years = ((time >> 26) & 0x1F) + 2000  # first 2 bits are "0b". Year has a 2000 year offset
    months = ((time >> 22) & 0xF)
    days = ((time >> 17) & 0x1F)
    hours = ((time >> 12) & 0x1F)
    minutes = ((time >> 6) & 0x3F)
    seconds = (time & 0x3F)

    dt = datetime(
        year=years,
        month=months,
        day=days,
        hour=hours,
        minute=minutes,
        second=seconds
    )

    return dt

def edit_cwa_header(filename = "D:/CWA-DATA.CWA", start_time = None, end_time = None):
    if end_time == -1:
        end_time = 0xFFFFFFFF
    with open(filename, 'rb') as f:
        # Read all bytes and modify the known indices of the start and end times.
        bytes = bytearray(f.read())
        if not start_time == None:
            bytes[13:17] = start_time.to_bytes(4, byteorder='little')
        if not end_time == None:
            bytes[17:21] = end_time.to_bytes(4, byteorder='little')

    return bytes

def unpack_samples(num_axes_bps, raw_bytes, sample_count):

    num_axes = num_axes_bps >> 4
    packing_format = num_axes_bps & 0x0F
    samples = []

    if packing_format == 2:
        total_values = sample_count * num_axes
        fmt = f"<{total_values}h"

        # Read current chunk of acc and gyr values
        unpacked_values = struct.unpack(fmt, raw_bytes[:total_values * 2])

        # Group values into X, Y, Z coordinates
        # note these are Gxyz/Axyz for 6 axis
        for i in range(0, len(unpacked_values), num_axes):
            samples.append(unpacked_values[i:i+num_axes])

    elif packing_format == 0:
        raise Exception("Packing format is 0, this needs implementing.")

    else:
        raise Exception("Packing format is not 2 or 0, perhaps your file is corrupt.")

    return samples

def scale_samples(samples, light_scale):
    n = light_scale >> 13
    acc_divider = 1 << (8 + n)  # Equivalent to 2**(8 + n)

    n = (light_scale >> 10) & 0x07
    max_dps = 8000 / (1 << n)
    gyr_divider = 32768.0 / max_dps

    scaled_samples = []
    for sample in samples:
        if len(sample) == 6:
            scaled = (
                sample[0] / gyr_divider,  # Gyro X
                sample[1] / gyr_divider,  # Gyro Y
                sample[2] / gyr_divider,  # Gyro Z
                sample[3] / acc_divider,  # Accel X
                sample[4] / acc_divider,  # Accel Y
                sample[5] / acc_divider   # Accel Z
            )
            scaled_samples.append(scaled)
        elif len(sample) == 3:
            scaled = (
                sample[0] / acc_divider,  # Accel X
                sample[1] / acc_divider,  # Accel Y
                sample[2] / acc_divider   # Accel Z
            )
            scaled_samples.append(scaled)
        else:
            raise Exception("3- and 9-axis CWA files not supported yet.")

    return scaled_samples

def get_cwa_data(filename = None, resample = True, prints = 0):
    # Based on: https://github.com/openmovementproject/openmovement/blob/master/Docs/ax3/ax3-technical.md

    data_dict = {}

    with open(filename, 'rb') as f:
        f.seek(1024) # skip the header

        for chunk in iter(partial(f.read, 512), b''):
            # skip impartial chunks
            if len(chunk) < 512:
                break

            data_format = "<" + \
                            "H" + "H" + "H" + "I" + "I" + "I" + "H" + "H" + "B" + "B" + \
                            "B" + "B" + "h" + "H" + "480s" + "H"

            data_names = [
                "packetHeader", "packetLength", "deviceFractional", "sessionId", "sequenceID",
                "timestamp", "lightScale", "temperature", "events", "battery", "sampleRate",
                "numAxesBPS", "timestampOffset", "sampleCount", "rawSampleData", "checksum"
            ]

            data_values = struct.unpack(data_format, chunk)
            packet = dict(zip(data_names, data_values))
            packet_header_str = chunk[0:2].decode('ascii', errors='ignore')
            packet["timestamp"] = cwa_timestamp_to_datetime(packet["timestamp"])

            # use multiple timing variables to calculate the actual time including offsets and fractional seconds.
            raw_rate = packet["sampleRate"]
            sampling_rate_hz = 3200 / (1 << (15 - (raw_rate & 0x0F)))
            if (packet["deviceFractional"] & 0x8000) != 0:
                time_fraction_ticks = (packet["deviceFractional"] & 0x7FFF) * 2
                fractional_seconds = time_fraction_ticks / 65536.0

                adjusted_offset = packet["timestampOffset"] + int((time_fraction_ticks * sampling_rate_hz) // 65536)
            else:
                fractional_seconds = 0.0
                adjusted_offset = packet["timestampOffset"]

            packet["timestamp"] = packet["timestamp"] + pd.to_timedelta(fractional_seconds, unit="s")

            unscaled_samples = unpack_samples(packet["numAxesBPS"], packet["rawSampleData"], packet["sampleCount"])
            samples = scale_samples(unscaled_samples, packet["lightScale"])

            if prints > 1:
                print("################ DATA PACKET ################")
                print("Packet Header: ", packet_header_str)
                print("Packet Length: ", packet["packetLength"])
                print("Sequence ID:   ", packet["sequenceID"])
                print("Raw Timestamp: ", packet["timestamp"])
                print("timestampOffset", packet["timestampOffset"])
                print("adjusted_offset", adjusted_offset)
                print("Sampling Rate: ", f"{sampling_rate_hz} Hz")
                print("sampleCount:   ", packet["sampleCount"])
                #print(samples)

            data_dict.update({
                packet["sequenceID"]: {
                    "timestamp": packet["timestamp"],
                    "fractional_seconds": fractional_seconds,
                    "adjusted_offset": adjusted_offset,
                    "sampleRate": sampling_rate_hz,
                    "sampleCount": packet["sampleCount"],
                    "samples": samples
                }
            })

    # convert the dict to a dataframe, transpose to get samples as columns, then explode to get one row per sample (rather than per timestamp). Index not reset here because needed for sub-second timing
    data_df = pd.DataFrame.from_dict(data_dict).T.explode("samples")

    # get sample number within packet and use to determine timestamp
    data_df["sample_index_in_packet"] = data_df.groupby(data_df.index).cumcount()
    data_df["timestamp"] = (pd.to_datetime(data_df["timestamp"]) +
                            pd.to_timedelta((data_df["sample_index_in_packet"] - data_df["adjusted_offset"]) / data_df["sampleRate"], unit="s"))

    # reset index because we've got our timings
    data_df = data_df.reset_index(drop=True)

    # check how many axes needed to expand samples into (order matters)
    if len(data_df["samples"].iloc[0]) == 6:
        columns = ["gyro_x", "gyro_y", "gyro_z", "accel_x", "accel_y", "accel_z"]
    elif len(data_df["samples"].iloc[0]) == 3:
        columns = ["accel_x", "accel_y", "accel_z"]
    else:
        raise Exception("Weird number of axes or 9 axis which is not supported.")

    # distribute samples across the columns and drop unneccessary columns
    data_df[columns] = pd.DataFrame(data_df["samples"].tolist(), index=data_df.index)
    data_df = data_df.drop(["samples", "sample_index_in_packet", "sampleRate", "sampleCount", "fractional_seconds", "adjusted_offset"], axis = 1)

    if resample:
        # resample at 100Hz
        #data_df = data_df.set_index("timestamp")
        #data_df = data_df.resample("10ms").mean().interpolate(method="linear")
        #data_df = data_df.reset_index(drop=False)

        data_df = data_df.sort_values("timestamp").reset_index(drop=True)

        raw_seconds = data_df["timestamp"].astype(np.int64) / 1e9

        start_seconds = raw_seconds.iloc[0]
        end_seconds = raw_seconds.iloc[-1]

        grid_seconds = np.arange(start_seconds, end_seconds, 0.01)

        resampled_payload = {
            "timestamp": pd.to_datetime(grid_seconds * 1e9, unit="ns")
        }

        for col in columns:
            resampled_payload[col] = np.interp(grid_seconds, raw_seconds, data_df[col])

        data_df = pd.DataFrame(resampled_payload)

    # reorder columns for convenience
    data_df = data_df.reindex(columns = ['timestamp', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'])

    if prints > 0:
        print(data_df.head(5))


    return data_df