import gzip
import numpy as np
import os
import pandas as pd
from pathlib import Path
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor

def download_fits(collection, index, fits_type, model):
    # define urls
    general_directory = "https://portal.nersc.gov/cfs/m4385/sims/RomanPIT-SNANA/2024-08-05_x108_3SNrates/"
    data_directory = f"{general_directory}ROMAN_{collection}_DATA-{index}/"
    
    # generate a list of urls to download FITS files
    links = generate_urls(data_directory, fits_type, model)
    
    # define folders used to store data
    fits_dir_name = "fits_dump"
    path_to_fits_dump = Path.cwd() / fits_dir_name
    path_to_index_dir = path_to_fits_dump / collection / index
    path_to_index_dir.mkdir(parents=True, exist_ok=True)
    
    # download files
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(download_and_unzip, fits_file, path_to_index_dir, fits_type) for fits_file in links]
        for future in futures:
            future.result()

def generate_urls(data_directory, fits_type, model):
    # create an empty list that will contain urls to the FITS files for download
    urls = []
    
    # define parameters
    roman_model = "ROMAN_NONIaMODEL" if model == "NONIa" else "ROMAN_SNIaMODEL"
    model_range = range(1, 9) if model == "NONIa" else range(0, 1)
    simulation_range = range(1, 5)
    
    # create urls and append to list
    for model_number in model_range:
        for simulation in simulation_range:
            if fits_type != "SPEC":
                filename = f"{data_directory}{roman_model}{model_number}-000{simulation}_{fits_type}.FITS.gz"
            else:
                filename = f"{data_directory}{roman_model}{model_number}-000{simulation}_{fits_type}.FITS"
            urls.append(filename)
    
    return urls

def download_and_unzip(fits_file, path_to_index_dir, fits_type):
    fits_filename = fits_file.split("/")[-1]
    
    # define paths
    if fits_type == "SPEC":
        fits_file_output_path = path_to_index_dir / fits_filename
    else:
        fits_gz_filename = fits_filename
        fits_filename = fits_gz_filename[:-3]
        fits_file_output_path = path_to_index_dir / fits_filename
    
    if fits_file_output_path.is_file():
        print(f"{fits_filename} already exists.")
        return
    
    # download the file
    response = requests.get(fits_file)
    response.raise_for_status()
    
    # save the file
    temp_file_path = path_to_index_dir / fits_filename if fits_type == "SPEC" else path_to_index_dir / fits_gz_filename
    with open(temp_file_path, 'wb') as temp_file:
        temp_file.write(response.content)
    
    # unzip if necessary
    if fits_type != "SPEC":
        unzip_gz(temp_file_path, fits_file_output_path)
        os.remove(temp_file_path)

def unzip_gz(fits_gz_filename, fits_file_output_path):
    # unpack the FITS.gz file
    with gzip.open(fits_gz_filename, 'rb') as f_in:
        with open(fits_file_output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

def get_hdu(hdul, name):
    # define header
    if name.lower() == "primary":
        hdr = hdul[0].header
    else:
        hdr = hdul[1].header
    
    # create a list of keywords and values
    keywords = list(hdr.keys())
    values = list(hdr.values())
    
    # create a DataFrame object
    df = pd.DataFrame({
        'Keyword': keywords,
        'Value': values
    })
    
    return df

def get_data(hdul):
    # define data
    data = hdul[1].data
    
    # create a list of keywords and values
    keywords = list(hdul[1].data.columns.names)
    
    # create a DataFrame object
    df = pd.DataFrame(data, columns=keywords)
    
    return df
