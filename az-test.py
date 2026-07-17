from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient

VAULT_URL = "https://azatmeukeyvault1dev.vault.azure.net/"

client = SecretClient(vault_url=VAULT_URL, credential=AzureCliCredential())

# read one secret (test secret)
token = client.get_secret("KV-RPA-LATAM-EXPERT-B-USER").value
print(token)

# list secret names
#for prop in client.list_properties_of_secrets():
#    print(prop.name)

# write / update a secret
#client.set_secret("KV-RPA-LATAM-EXPERT-B-USER", "MEVANGELISTA")