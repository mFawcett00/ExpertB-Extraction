import truststore
truststore.inject_into_ssl()  # trust the Windows cert store (Inchcape TLS proxy); see Troubleshooting
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
client = SecretClient(
    vault_url="https://azatmeukeyvault1dev.vault.azure.net/",
    credential=DefaultAzureCredential(),
)
value = client.get_secret("DIP-RPA-DEFAULT-TOKEN").value
print("OK, got:", value)