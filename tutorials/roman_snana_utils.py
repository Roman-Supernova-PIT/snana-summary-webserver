import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nested_pandas as npd
from astropy.io import fits
from astropy.time import Time
from get_fits import download_fits, get_hdu, get_data
from pathlib import Path
from roman_snana_api import Roman_SNANA_Summary

def nest_df(phot_fits_path, head_fits_path):
    # create dataframe for PHOT and HEAD .FITS
    phot_df = df(fits.open(phot_fits_path))
    head_df = df(fits.open(head_fits_path))
    
    nested_phot = []

    # obtain relevant photometric data for each observation
    for index, row in head_df.iterrows():
        phot_subset = get_phot_subset(row, phot_df) 
        nested_phot.append(phot_subset)
        
    # create nested dataframe
    nf = npd.NestedFrame(head_df)
    nested = npd.NestedFrame(nf).add_nested(nested_phot, "PHOT_OBS")
        
    return nested

def df(hdul):
    # extract tabular data
    rows = hdul[1].data
    rows = np.array(rows, dtype=rows.dtype.newbyteorder('<'))
    columns = hdul[1].columns.names
    
    # create dataframe and format columns
    df = pd.DataFrame(rows, columns=columns)
    for col in df.select_dtypes([object]).columns:
        df[col] = df[col].apply(
            lambda x: x.decode('utf-8').strip() if isinstance(x, bytes) else x.strip() if isinstance(x, str) else x
        )
        
    return df

def get_phot_subset(row, phot_df):
    min_idx = row['PTROBS_MIN'] - 1
    max_idx = row['PTROBS_MAX']
    return phot_df.iloc[min_idx:max_idx]

def plot_lcs(photometric_data):
    filter_colors = {"J": "#4daf4a", "H": "#ff7f00", "Y": "#377eb8", "F": "#984ea3", "R": "#e41a1c", "Z": "#a65628"}

    # extract unique filter names from "BAND" in the nested DataFrame
    bands = photometric_data["BAND"].unique()

    plt.figure(figsize=(10, 6))
    for band in bands:
        color = filter_colors.get(band, "gray")  # uses "gray" if band not in predefined colors

        # filter data
        band_data = photometric_data[photometric_data["BAND"] == band]

        # plot light curves with errors
        plt.errorbar(
            band_data["MJD"],
            band_data["FLUXCAL"],
            yerr=band_data["FLUXCALERR"],
            fmt="-o",
            color=color,
            label=f"{band}",
            alpha=0.7,
        )

    # add labels, legend and title
    plt.xlabel("MJD")
    plt.ylabel("Flux")
    plt.title("Light Curve by Filter")
    plt.legend(title="Filters")
    plt.grid(True)
    plt.show()

def plot_lc(photometric_data, band_name: str):
    filter_colors = {"J": "#4daf4a", "H": "#ff7f00", "Y": "#377eb8", "F": "#984ea3", "R": "#e41a1c", "Z": "#a65628"}
    
    # filter data based on specified band
    color = filter_colors.get(band_name, "gray") # uses "gray" if band not in predefined colors
    band_data = photometric_data[photometric_data["BAND"] == band_name]

    # plot light curve with errors
    plt.figure(figsize=(10, 6))
    plt.errorbar(
        band_data["MJD"],
        band_data["FLUXCAL"],
        yerr=band_data["FLUXCALERR"],
        fmt="-o",
        color=color,
        label=band_name,
        alpha=0.7,
    )

    # add labels, legend and title
    plt.xlabel("MJD")
    plt.ylabel("Flux")
    plt.title("Light Curve for a Single Band")
    plt.legend(title="Filter")
    plt.grid(True)
    plt.show()
    
def days_between_obs(phot_data, band_name=None):
    """
    Plot a histogram of the days between observations for a specific band or for all observations if no band is specified.

    Parameters:
        phot_data (pd.DataFrame): The photometric data containing "MJD" and "BAND" columns.
        band_name (str, optional): The name of the band to filter the data (e.g., "Y", "J", etc.). If None, use all bands.

    Returns:
        None
    """
    # filter data for the specified band
    phot_data["BAND"] = phot_data["BAND"].astype(str)
    band_data = phot_data[phot_data["BAND"] == band_name]

    if band_name:
        band_data = phot_data[phot_data["BAND"] == band_name]
        if band_data.empty:
            print(f"No data available for band '{band_name}'.")
            return
    else:
        band_data = phot_data

    # ensure chronological order
    band_data = band_data.sort_values(by="MJD")

    # calculate differences in MJD only for this band
    mjd_values = band_data["MJD"]
    mjd_differences = mjd_values.diff().dropna()

    # plot histogram
    plt.figure(figsize=(10, 6))
    plt.hist(mjd_differences, bins=100, color='blue', alpha=0.7, edgecolor='black')
    plt.xlabel("Days Between Observations")
    plt.ylabel("Frequency")
    plt.title(f"Histogram of Days Between Observations{' for Band ' + band_name if band_name else ''}")
    plt.grid(True)
    plt.show()
