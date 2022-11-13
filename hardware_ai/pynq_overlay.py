#!/usr/bin/env python
# coding: utf-8

import random
from queue import Queue
import pandas as pd
import numpy as np
from scipy import stats, signal 
from tensorflow.keras.models import load_model #import model
from joblib import load #import standard scalar weights
import time

class Process:
    def __init__(self):
        self.raw_buffer = []
        self.i = 0
        self.scaler = load('./hardware_ai/cg4002/scaler_final.joblib')
        self.model = load_model('./hardware_ai/cg4002/detection_final.h5')

    def process(self, raw):
        self.raw_buffer.append(raw)
        
        #buffer fills until 10 packet
        if len(self.raw_buffer) < 10:
            return ""
        
        #convert raw data into a dataframe for manipulation
        data = pd.DataFrame(columns=['acceleration_x', 'acceleration_y', 'acceleration_z', 'gyro_x', 'gyro_y', 'gyro_z'])
        for i in range(len(self.raw_buffer)):
            list_row = [self.raw_buffer[i][1]/100, self.raw_buffer[i][2]/100, self.raw_buffer[i][3]/100, self.raw_buffer[i][4], self.raw_buffer[i][5], self.raw_buffer[i][6]]
            data.loc[len(data)] = list_row
        self.raw_buffer.clear()
              
        #feature extraction
        final_data = self.combine_rows(data.values.tolist())
        final_data = pd.DataFrame(data=np.array(final_data).T,  columns = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"])
        final_data = self.extract_raw_data_features(final_data)
        final_data = np.array([self.create_featureslist(final_data)])
        
        #scales the raw data with model scalars
        final_data = self.scaler.transform(final_data.tolist())
        
        #predicts action
        output = self.model.predict([final_data]).tolist()[0]
        prediction = output.index(max(output))

        #returns classified action
        if prediction == 0:
            return "reload"
        if prediction == 1:
            return "shield"
        if prediction == 2:
            return "grenade"
        if prediction == 3:
            return "logout"
    
    def raw_queue(self, raw_data):
        if len(self.raw_buffer) < 10:
            self.raw_buffer.append(raw_data)
            return ""
        if len(self.raw_buffer) >= 10:
            pkt = self.raw_buffer
            self.raw_buffer.clear()
            return pkt  

    def combine_rows(self, data):
        combined_raw = []
        new_data = []
        for col in range(6):
            for row in range(len(data)):
                combined_raw.append(data[row][col])
            new_data.append(combined_raw)
            combined_raw = []
        return new_data
    
    def extract_raw_data_features(self, data):
        new_features = []
        for col in ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z"]:
            features = []
            f_n = np.array(data[col])
            feature = self.extract_raw_data_features_per_row(f_n)
            new_features.append(feature)
        return new_features

    def compute_mean(self, data):
        return np.mean(data)

    def compute_variance(self, data):
        return np.var(data)

    def compute_median_absolute_deviation(self, data):
        return stats.median_absolute_deviation(data)

    def compute_root_mean_square(self, data):
        def compose(*fs):
            def wrapped(x):
                for f in fs[::-1]:
                    x = f(x)
                return x
            return wrapped
        rms = compose(np.sqrt, np.mean, np.square)
        return rms(data)

    def compute_interquartile_range(self, data):
        return stats.iqr(data)

    def compute_percentile_75(self, data):
        return np.percentile(data, 75)

    def compute_kurtosis(self, data):
        return stats.kurtosis(data)

    def compute_min_max(self, data):
        return np.max(data) - np.min(data)

    def compute_signal_magnitude_area(self, data):
        return np.sum(data) / len(data)

    def compute_zero_crossing_rate(self, data):
        return ((data[:-1] * data[1:]) < 0).sum()

    def compute_spectral_centroid(self, data):
        spectrum = np.abs(np.fft.rfft(data))
        normalized_spectrum = spectrum / np.sum(spectrum)  
        normalized_frequencies = np.linspace(0, 1, len(spectrum))
        spectral_centroid = np.sum(normalized_frequencies * normalized_spectrum)
        return spectral_centroid

    def compute_spectral_entropy(self, data):
        freqs, power_density = signal.welch(data)
        return stats.entropy(power_density)

    def compute_spectral_energy(self, data):
        freqs, power_density = signal.welch(data)
        return np.sum(np.square(power_density))

    def compute_principle_frequency(self, data):
        freqs, power_density = signal.welch(data)
        return freqs[np.argmax(np.square(power_density))]
    
    def create_featureslist(self, final_data):
        new_data = []
        for row in range(np.array(final_data).shape[0]):
            for col in range(np.array(final_data).shape[1]):
                new_data.append(final_data[row][col])
        return new_data
        
    def extract_raw_data_features_per_row(self, f_n):
        f1_mean = self.compute_mean(f_n)
        f1_var = self.compute_variance(f_n)
        f1_mad = self.compute_median_absolute_deviation(f_n)
        f1_rms = self.compute_root_mean_square(f_n)
        f1_iqr = self.compute_interquartile_range(f_n)
        f1_per75 = self.compute_percentile_75(f_n)
        f1_kurtosis = self.compute_kurtosis(f_n)
        f1_min_max = self.compute_min_max(f_n)
        f1_sma = self.compute_signal_magnitude_area(f_n)
        f1_zcr = self.compute_zero_crossing_rate(f_n)
        f1_sc = self.compute_spectral_centroid(f_n)
        f1_entropy = self.compute_spectral_entropy(f_n)
        f1_energy = self.compute_spectral_energy(f_n)
        f1_pfreq = self.compute_principle_frequency(f_n)
        return f1_mean, f1_var, f1_mad, f1_rms, f1_iqr, f1_per75, f1_kurtosis, f1_min_max, f1_sma, f1_zcr, f1_sc, f1_entropy, f1_energy, f1_pfreq
    

