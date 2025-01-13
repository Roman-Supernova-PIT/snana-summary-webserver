import requests
import pandas as pd

class Roman_SNANA_Summary:
    """A client for interacting with SNANA ROMAN PIT sim summary information.

    ----
    """
    
    def __init__(self):
        self.base_url = "https://roman-snpit-snana-strategy.lbl.gov" 
        self.session = requests.Session()

    def get_campaigns(self):
        """Get the names of the available campaigns.

        Returns:
            A pandas DataFrame with names of the available campaigns.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                client.get_campaigns()
        """
        
        request = f"{self.base_url}/campaigns/"
        
        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            campaign_name = list(data['campaigns'].keys())[0]
            table_data = {
                "Campaign Name": [campaign_name]
            }
            campaign_table = pd.DataFrame(table_data)
            return campaign_table

        except requests.exceptions.RequestException as e:
            print(f"Error fetching campaigns: {e}")
            return None

    def get_collections(self, campaign):
        """Get the names of the collections available for a particular campaign.

        Args:
            campaign (str):
                The name of the campaign.

        Returns:
            A pandas DataFrame with names of the available collections.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                client.get_collections(campaign)
        """
        
        request = f"{self.base_url}/collections/{campaign}"
        
        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            collections = data['collections']
            table = pd.DataFrame(collections, columns=['Collections'])
            return table

        except requests.exceptions.RequestException as e:
            print(f"Error fetching collections: {e}")
            return None

    def get_survey_info_keys(self, campaign, collection):
        """Get the keys available in `surveyinfo` for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of keys in `surveyinfo` for a particular campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                client.get_summarydata_keys(campaign, collection)
        """
        
        request = f"{self.base_url}/surveyinfo/{campaign}/{collection}"
        
        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            keys = list(data.keys())
            return keys

        except requests.exceptions.RequestException as e:
            print(f"Error fetching survey info keys: {e}")
            return None

    def get_survey_info(self, campaign, collection, key):
        """Get the value of a specified key in `surveyinfo` for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            key (str):
                The name of the key.

        Returns:
            A pandas DataFrame containing the value(s) of a specified key in `surveyinfo` for a particular campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                key = "OUTDIR" # swap 'OUTDIR' with any of the sub-dictionary keys
                client.get_survey_info(campaign, collection, key)
        """
        
        request = f"{self.base_url}/surveyinfo/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            value = data.get(key, None)
            if isinstance(value, (str, int, float)):
                return pd.DataFrame({key: [value]})
            else:
                return pd.DataFrame(value)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching survey info: {e}")
            return None

    def get_tiers(self, campaign, collection):
        """Get the tiers available for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of the tiers available for a particular campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                client.get_tiers(campaign, collection)
        """
        
        request = f"{self.base_url}/tiers/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            return data

        except requests.exceptions.RequestException as e:
            print(f"Error fetching tiers: {e}")
            return None

    def get_instrument_info_keys(self, campaign, collection):
        """Get the keys available in `instrinfo` (instrument info) for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of keys in `surveyinfo` that contain information about the simulated instrument that SNANA used.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                client.get_instrument_info_keys(campaign, collection)
        """
        
        request = f"{self.base_url}/instrinfo/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            keys = list(data.keys())
            return keys

        except requests.exceptions.RequestException as e:
            print(f"Error fetching instrument info keys: {e}")
            return None

    def get_instrument_info(self, campaign, collection, key):
        """Get the value of a specified key in `instrinfo` (instrument info) for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            key (str):
                The name of the key.

        Returns:
            A pandas DataFrame containing the value(s) of a specified key in `instrinfo` for a particular campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                key = "PARAMS" # swap 'PARAMS' with any of the sub-dictionary keys
                client.get_instrument_info(campaign, collection, key)
        """
        
        request = f"{self.base_url}/instrinfo/{campaign}/{collection}"
        
        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            df = pd.DataFrame.from_dict(data[key], orient='index', columns=[key])
            return df

        except requests.exceptions.RequestException as e:
            print(f"Error fetching instrument info for {key}: {e}")
            return None

    def get_analysisinfo_keys(self, campaign, collection):
        """Get the keys available in `analysisinfo` for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of keys in `analysisinfo` that define what SNANA did.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                client.get_analysisinfo_keys(campaign, collection)
        """
        
        request = f"{self.base_url}/analysisinfo/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()

            keys = list(data.keys())
            return keys

        except requests.exceptions.RequestException as e:
            print(f"Error fetching analysis info keys: {e}")
            return None

    def get_analysisinfo(self, campaign, collection, key):
        """Get the value of a specified key in `analysisinfo` for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            key (str):
                The name of the key.

        Returns:
            dict[str]:
                A dictionary containing the value(s) of a specified key in `analysisinfo` for a particular campaign and collection.
                
        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                key = "prescales" # swap 'prescales' with any of the sub-dictionary keys
                client.get_analysisinfo(campaign, collection, key)
        """
        
        request = f"{self.base_url}/analysisinfo/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            return data[key]                

        except requests.exceptions.RequestException as e:
            print(f"Error fetching analysis info: {e}")
            return None

    def get_sim_names(self, campaign, collection):
        """Get the names of the simulations available for a particular campaign and collection.

        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of names of the simulations available.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                sim = "2TIER_RATE0 a00-t00-z00"
                client.get_sim_names(campaign, collection)
        """
        
        request = f"{self.base_url}/surveys/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            keys = list(data.keys())
            return keys             

        except requests.exceptions.RequestException as e:
            print(f"Error fetching sim names: {e}")
            return None

    def get_sim_keys(self, campaign, collection, sim):
        """Get the keys available for a particular simulation, campaign, and collection.
        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            sim (str):
                The name of the simulation.

        Returns:
            list[str]:
                A list of keys for a particular simulation contained withing a campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                sim = "2TIER_RATE0 a00-t00-z00"
                client.get_sim_keys(campaign, collection, sim)
        """
        
        request = f"{self.base_url}/surveys/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            survey_keys = data[sim].keys()
            return survey_keys             

        except requests.exceptions.RequestException as e:
            print(f"Error fetching sim keys: {e}")
            return None

    def get_sim_info(self, campaign, collection, sim, key):
        """Get the value of a specified key for a particular simulation, campaign, and collection.
        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            sim (str):
                The name of the simulation.
            key (str):
                The name of the key.

        Returns:
            dict[str]:
                A dictionary containing the value(s) of a specified key for a particular simulation, campaign, and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                sim = "2TIER_RATE0 a00-t00-z00"
                key = "gentypemap" # swap 'gentypemap' with any of the sub-dictionary keys
                client.get_sim_info(campaign, collection, sim, key)
        """
        
        request = f"{self.base_url}/surveys/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            return data[sim][key]             

        except requests.exceptions.RequestException as e:
            print(f"Error fetching sim info: {e}")
            return None
        
    def get_summarydata_keys(self, campaign, collection):
        """Get the keys available in `summarydata` for a particular campaign and collection.
        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.

        Returns:
            list[str]:
                A list of keys for a particular simulation contained withing a campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                client.get_summarydata_keys(campaign, collection)
        """
        
        request = f"{self.base_url}/summarydata/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            keys = list(data.keys())
            return keys             

        except requests.exceptions.RequestException as e:
            print(f"Error fetching summary data keys: {e}")
            return None

    def get_summarydata(self, campaign, collection, key):
        """Get the value of a specified key in `summarydata` for a particular campaign and collection.
        Args:
            campaign (str):
                The name of the campaign.
            collection (str):
                The name of the collection.
            key (str):
                The name of the key.

        Returns:
            String:
                The value(s) of a specified key for a particular campaign and collection.

        Example:

            .. code-block:: python

                client = Roman_SNANA_Summary()
                campaign = "2024-08-05_x108_3SNrates"
                collection = "2TIER_RATE0"
                key = "status" # swap 'status' with any of the sub-dictionary keys
                client.get_summarydata(campaign, collection, key)
        """
        
        request = f"{self.base_url}/summarydata/{campaign}/{collection}"

        try:
            response = self.session.get(request)
            response.raise_for_status()
            data = response.json()
            return data[key]             

        except requests.exceptions.RequestException as e:
            print(f"Error fetching summary data keys: {e}")
            return None
