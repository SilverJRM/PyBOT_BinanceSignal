import requests

response = requests.get('https://api.ipify.org')
ip_address = response.text

print('Your IP address is:', ip_address)
