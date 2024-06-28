import requests

def get_collections():
    # define api request
    request = "https://roman-snpit-snana-strategy.lbl.gov/collections"
    
    # make the api request and return output
    response = requests.get(request)
    data = response.json()
    collections = data['collections']
    return collections

def get_indices(collection):
    # define api request
    request = f"https://roman-snpit-snana-strategy.lbl.gov/summarydata/{collection}"
    
    # make the api request and return output
    response = requests.get(request)
    data = response.json()
    surveys = data['surveys']
    keys = [k.split(' ', 1)[1] if ' ' in k else '' for k, v in surveys.items()]
    return keys
    
    