import numpy as np
import re
from . import utils
from scipy.interpolate import interp1d
import copy
from . import trial
from . import session

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


"""
Read method will read in the ascii file and extract the data
"file_name" will take in the name of the file you are trying
to extract data from

mode: d or u
d = "defualt"
u = user defined

"default" will use the default start and end times given in the file
"user defined" will take in "start_msg" and "end_msg" to use as the

start and end marker
"start_msg" will use regular expression to identify the user inputed

message markers
ex. r"TRIAL \d START"

"end_msg" will use regular expression to identify the user inputed end
message makers
ex. r"TRIAL \d END"
"""


def read(filename, mode="d", start_msg=r"TRIAL \d{1,2} START",
         end_msg=r"TRIAL \d{1,2} END", autoepoch=False):
    # TODO parse info
    if not filename.endswith(".asc"):
        # Raise an error for checking file name extension
        pass
    if not mode == "d" or not mode == "u":
        # raise exception invalid mode
        pass

    with open(filename) as f:
        start_time = ""
        end_time = ""
        flag = False
        events = []
        events_dict = {}
        timestamps_list = []
        messages_dict = {}
        trial_markers = {"start": [], "end": []}
        pupil_size_list = []
        movement_list = [[], []]
        rate_list = {}

        # Default Mode
        if mode == "d":
            for num, line in enumerate(f, 1):
                elements = line.split()

                if line.startswith("START"):
                    start_time, trial_markers, end_time = find_start(elements, start_time, trial_markers, end_time)

                # to only get END messages
                # adds to trial_markers, messages_dict, timestamps_list
                if line.startswith("END"):
                    end_time, trial_markers, messages_dict, flag, start_time = find_end(elements, end_time, trial_markers, messages_dict, flag, start_time)

                if start_time:
                    if line.startswith(start_time):
                        flag = True

                # check for start
                if flag is True:
                    # will get pupil size, timestamps, and movements
                    if is_number(elements[0]):
                        timestamps_list, pupil_size_list, movement_list = tpm_read(timestamps_list, pupil_size_list, movement_list, elements)

                    # Gets all messages between START and END
                    elif elements[0] == "MSG":
                        messages_dict[int(elements[1])] = elements[2:]

                    # Gets all events between START and END
                    elif not is_number(elements[1]):
                        events_dict = event_read(events_dict, elements)

                # finds all the END messages that is outputed
                # if end_time:
                #     if line.startswith("MSG"):
                #         if elements[1] in messages_dict:
                #             messages_dict[int(elements[1])].append(elements[2:])
                #         else:
                #             messages_dict[int(elements[1])] = elements[2:]
        # User Defined Mode
        elif mode == "u":
            # initializes the regular expressions for start and end markers
            start_msg = re.compile(start_msg)
            end_msg = re.compile(end_msg)
            for num, line in enumerate(f, 1):
                elements = line.split()
                # finds start time using user defined marker
                if re.search(start_msg, line[2:]):
                    start_time, trial_markers, end_time = find_start(elements, start_time, trial_markers, end_time)
                    flag = True
                    continue

                # to only get END messages using user defined marker
                # adds to trial_markers, messages_dict, timestamps_list
                if re.search(end_msg, line[2:]):
                    #print(elements)
                    end_time, trial_markers, messages_dict, flag, start_time = find_end(elements, end_time, trial_markers, messages_dict, flag, start_time)
                    flag = False
                    continue

                # check for start marker
                if flag is True:
                    # will get pupil size, timestamps, and movements
                    if is_number(elements[0]):
                        timestamps_list, pupil_size_list, movement_list = tpm_read(timestamps_list, pupil_size_list, movement_list, elements)
                    # Gets messages between START and END markers
                    elif elements[0] == "MSG":
                        messages_dict[elements[1]] = elements[2:]
                    # Gets all events between START and END markers
                    elif not is_number(elements[1]):
                        events_dict = event_read(events_dict, elements)

                # finds all the END messages that is outputed
                # if end_time:
                #     if line.startswith("MSG"):
                #         if elements[1] in messages_dict:
                #             messages_dict[int(elements[1])].append(elements[2:])
                #         else:
                #             messages_dict[int(elements[1])] = elements[2:]



    # convert list to numpy array
    timestamps = np.array(timestamps_list)
    pupil_size = np.array(pupil_size_list)
    movement = np.array(movement_list)
    return Data(timestamps, pupil_size, movement, 500, {}, messages_dict,
                events_dict, trial_markers)

#find start times
def find_start(elements, start_time, trial_markers, end_time):
    start_time = elements[1]
    trial_markers["start"].append(int(elements[1]))
    end_time = ""  # to end "END message input"
    return start_time, trial_markers, end_time

#find end times
def find_end(elements, end_time, trial_markers, messages_dict, flag, start_time):
    end_time = elements[1]
    trial_markers["end"].append(int(elements[1]))
    messages_dict[int(elements[1])] = elements[2:]
    flag = False
    start_time = ""
    return end_time, trial_markers, messages_dict, flag, start_time

#gets timestamps, pupil size, and movement(x,y) from file
def tpm_read(timestamps_list, pupil_size_list, movement_list, elements):
    if(elements[1] == "."):
        timestamps_list.append(int(elements[0]))
        pupil_size_list.append(np.nan)
        movement_list[0].append(np.nan)  # x-axis
        movement_list[1].append(np.nan)
    else:
        timestamps_list.append(int(elements[0]))
        pupil_size_list.append(float(elements[1]))
        movement_list[0].append(float(elements[2]))  # x-axis
        movement_list[1].append(float(elements[3]))  # y-axis
    return timestamps_list, pupil_size_list, movement_list
#gets events from file
def event_read(events_dict, elements):
    # events.append(elements[0])
    # checks if event already exists
    event_name = f"{elements[0]} {elements[1]}"
    if event_name not in events_dict:
        events_dict[event_name] = []

    event_list_variable = elements[2:]
    temp_list = []
    for var in event_list_variable:
        if var == ".":
            var = np.nan
            temp_list.append(var)
        else:
            temp_list.append(float(var))
    event_list_variable = temp_list

    temp_list = list(map(float,temp_list))
    events_dict[event_name].append(temp_list)
    return events_dict


"""
The remove_eye_blinks method replaces the eyeblinks (NAS) with interpolated data, with a buffer of 50 data points and linear spline to do interpolation. ### Linear interpolation is what is supported right now.

"""
def pupil_size_remove_eye_blinks(abra_obj, buffer=50, interpolate='linear', inplace=False):
    # Creating a buffeir
    pupilsize_ = np.copy(abra_obj.pupil_size)
    blink_times = np.isnan(pupilsize_)
    for j in range(len(blink_times)):
        if blink_times[j]==True:
            pupilsize_[j-buffer:j+buffer]=np.nan

    # Interpolate
    if interpolate=='linear':
        interp_pupil_size = utils.linear_interpolate(pupilsize_)
        if inplace == True:
            abra_obj.pupil_size = interp_pupil_size
        elif inplace == False:
            tmp_obj = copy.deepcopy(abra_obj)
            tmp_obj.pupil_size = interp_pupil_size
            return tmp_obj
    else:
        print("We haven't implement anyother interpolation methods yet")
        return False

"""
time locking into a particular event.
"""

"""
The Data class for the data structure
"""
class Data:

    def __init__(self, timestamps, pupil_size, movement, sample_rate,
                 calibration, messages, events, trial_markers):
        self.timestamps = timestamps
        self.pupil_size = pupil_size
        self.movement = movement
        self.sample_rate = sample_rate
        self.calibration = calibration
        self.messages = messages
        self.events = events
        self.trial_markers = trial_markers


    """
    This function splits the pupil size and timestamp data into its respective trials and returns an array of trial class objects
    """
    def create_session(self, conditions=None):
        t_Mark = self.trial_markers
        t_Time = self.timestamps
        start = t_Mark['start']
        end  = t_Mark['end']

        # All trial start and end markers in array ([start,end])
        trial_IDX = []
        for i in range(len(start)):
            temp = []
            st = start[i]
            en = end[i]
            temp.append(st)
            temp.append(en)
            trial_IDX.append(temp)

        # Get the pupil size in the events between the starting and ending markers
        trial_pupil = []
        trial_mov_x = []
        trial_mov_y = []
        trial_stamp = []
        for i in range(len(trial_IDX)):
            st = trial_IDX[i][0]
            en = trial_IDX[i][1]

            # Find the indexes to call the pupil size within the timestamps for a trial
            idx = np.where((self.timestamps >= st) & (self.timestamps <= en))[0]

            # Add the pupil sizes for each timestamp
            temp_pupil = []
            temp_movex = []
            temp_movey = []
            temp_stamp = []
            for k in idx:
                temp_pupil.append(self.pupil_size[k])
                temp_stamp.append(self.timestamps[k])
                temp_movex.append(self.movement[0][k])
                temp_movey.append(self.movement[1][k])
            trial_pupil.append(np.array(temp_pupil))
            trial_mov_x.append(np.array(temp_movex))
            trial_mov_y.append(np.array(temp_movey))
            trial_stamp.append(np.array(temp_stamp))

        # Create a list of new trials with each pupil_size
        trials = []
        for i in range(len(trial_IDX)):
            t = trial.Trial(trial_stamp[i], trial_pupil[i], trial_mov_x[i], trial_mov_y[i])
            trials.append(t)

        # Check for conditions
        num_trials = len(trials)
        if conditions is not None:
            if (len(conditions) != num_trials):
                raise ValueError('Condition length must be equal to the number of trials: ', num_trials)

        return session.Session(np.array(trials), conditions)


    def create_epochs(self, event_timestamps, conditions=None, pre_event=200, post_event=200, pupil_baseline=None):
        # Create an empty array for storing the epoch information
        win_size = int((pre_event+post_event)*self.sample_rate/1000)
        all_epochs = []
        # Iterate timestamp events get each epoch pupil size
        for i in range(len(event_timestamps)):
            start = event_timestamps[i]-pre_event
            end = event_timestamps[i]+post_event
            idx = (self.timestamps >= (event_timestamps[i]-pre_event)) & (self.timestamps <= (event_timestamps[i]+post_event))

            if np.sum(idx) != win_size:
                non_zero_idx = np.nonzero(idx)
                # Explicitly set all values beyond window size to False
                # Enforcing the length to be the defined window size
                idx[non_zero_idx[0][0]+win_size:]=False
            epoch_pupil = self.pupil_size[idx]
            epoch_movex = self.movement[0][idx]
            epoch_movey = self.movement[1][idx]
            # Do baselining using the mean and standard deviation of the mean and variance
            if pupil_baseline:
                baseline_idx = (self.timestamps >= (event_timestamps[i]-pre_event+pupil_baseline[0])) & (self.timestamps <= (event_timestamps[i]-pre_event+pupil_baseline[1]))
                baseline_period = self.pupil_size[baseline_idx]
                baseline_mean = np.mean(baseline_period)
                baseline_std = np.std(baseline_period)
                epoch_pupil = (epoch_pupil - baseline_mean)/baseline_std

            t = trial.Trial(self.timestamps[idx], epoch_pupil, epoch_movex, epoch_movey)
            all_epochs.append(t)

        epochs = session.Epochs(all_epochs, conditions)
        return epochs

        def check_pupil_data(self, data_check):
            vis = Visualization(data_check)
            vis.mainloop()
            return vis
