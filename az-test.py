from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

VAULT_URL = "https://azatmeukeyvault1dev.vault.azure.net/"

client = SecretClient(vault_url=VAULT_URL, credential=DefaultAzureCredential())

# read one secret (test secret)
token = client.get_secret("DIP-RPA-DEFAULT-TOKEN").value
print(token)

# list secret names
for prop in client.list_properties_of_secrets():
    print(prop.name)

# write / update a secret
#client.set_secret("DIP-RPA-DEFAULT-TOKEN", "new-value-123")