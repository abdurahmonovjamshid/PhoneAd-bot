
import requests

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot_token = '6329228284:AAHUQcqbN3Cs8ndat8ILnuhSpMedn03mOX4'

# Replace 'CHAT_ID' with the ID of the chat from which you want to retrieve messages
user_id = '6868629518'

def get_chat_info(user_id):
    # Define the API endpoint URL
    url = f"https://api.telegram.org/bot{bot_token}/getChat"

    # Define the request payload
    payload = {
        'chat_id': user_id
    }

    # Send the POST request to retrieve the chat information
    response = requests.post(url, json=payload)

    # Check the response status code
    if response.status_code == 200:
        chat_info = response.json()
        print("Chat information:", chat_info)
    else:
        print("Failed to retrieve chat information. Error:", response.text)

# Call the get_chat_info function
get_chat_info(user_id)