import asyncio
import json
import os
import aiohttp
import apiCreds
import tweepy.asynchronous
import tweepy.errors

# ---------- VARS ----------

api_data = []
loop_count = 0
service_issues = {}
sleep_interval = 60
tweepy_client = tweepy.asynchronous.AsyncClient(apiCreds.twitterBearerToken, apiCreds.twitterApiKey, apiCreds.twitterApiKeySecret, apiCreds.twitterAccessToken, apiCreds.twitterAccessTokenSecret)
lol_server_regions = [
    {"code":"br1", "name":"Brazil"},
    {"code":"eun1", "name":"Europe: North"},
    {"code":"euw1", "name":"Europe: West"}, 
    {"code":"jp1", "name":"Japan"}, 
    {"code":"kr", "name":"Korea"}, 
    {"code":"la1", "name":"Latin America: North"}, 
    {"code":"la2", "name":"Latin America: South"}, 
    {"code":"na1", "name":"North America"}, 
    {"code":"oc1", "name":"Oceania"}, 
    {"code":"pbe1", "name":"Public Test Environment"}, 
    {"code":"ph2", "name":"Philippines"}, 
    {"code":"ru", "name":"Russia"}, 
    {"code":"sg2", "name":"Singapore, Malaysia, & Indonesia"}, 
    {"code":"th2", "name":"Thailand"}, 
    {"code":"tr1", "name":"Turkey"}, 
    {"code":"vn2", "name":"Vietnam"}
]

# ---------- FUNCTIONS ----------

def clearConsole():
    if os.name == 'nt':
        # windows
        os.system('cls')
    else:
        # OSX/Linux
        os.system('clear')

async def get_region_data():
    async with aiohttp.ClientSession() as session:
        # Create tasks for async
        tasks = []
        for region in lol_server_regions:
            tasks.append(asyncio.create_task(session.get(f'https://{region["code"]}.api.riotgames.com/lol/status/v4/platform-data?api_key={apiCreds.riotApiKey}', timeout=5)))

        # Run http get requests for api data
        try:
            responses = await asyncio.gather(*tasks)
            for iteration, response in enumerate(responses):
                if response.status == 200:
                    api_data.append(await response.json())
                else:
                    print(f'Error getting data from {lol_server_regions[iteration]["name"]} api server. (Error Code: {response.status})')
        except aiohttp.ClientConnectionError as e:
            print(f'Connection Error: {e}')
        except Exception as e:
            print(e)

def get_service_issues():
    for region in api_data:
        for incident in region["incidents"]:
            # if issue id exists
            if incident["id"] in service_issues:
                # update last seen
                service_issues[incident["id"]]["last_seen"] = loop_count
                # if region isn't listed, then add it
                for issue_region in service_issues[incident["id"]]["regions"]:
                    if region["id"] not in service_issues[incident["id"]]["regions"]:
                        service_issues[incident["id"]]["regions"].append(region["id"])
                        service_issues[incident["id"]]["regions_plain_text"].append(region["name"])
            else:
                # issue id doesn't exist. add to list
                service_issues[incident["id"]] = {"regions":[region["id"]],"regions_plain_text":[region["name"]],"title":incident["titles"][0]["content"],"last_seen":loop_count,"first_seen":loop_count}

def clean_service_issues():
    for issue in service_issues:
        if service_issues[issue]["last_seen"] != loop_count:
            del issue

async def send_tweets():
    # Create tasks for async
    tweet_tasks = []
    for incident in service_issues:
        if service_issues[incident]["first_seen"] == loop_count:
            tweet_tasks.append(asyncio.create_task(tweepy_client.create_tweet(text=f'⚠  LoL Service Issue: {service_issues[incident]["title"]}.\nRegions affected: {list(service_issues[incident]["regions_plain_text"])}')))

    # Send tweets
    if len(tweet_tasks) != 0:
        try:
            await asyncio.gather(*tweet_tasks)
            print('New tweet(s) sent.')
        except tweepy.errors.TweepyException as e:
            print(f'Sending tweet(s) failed. (Error: {e})')
    else:
        print('No tweets to send.')

async def main():
    global loop_count
    while True:
        # clear the gathered api data
        api_data.clear
        clearConsole()

        # Update all regions
        await asyncio.create_task(get_region_data())

        # Parse api data
        get_service_issues()

        # Clean service issue list
        clean_service_issues()

        print(f"{service_issues}")

        # Send Tweets
        asyncio.create_task(send_tweets())

        # Wait before updating again
        print(f'\nCurrent iteration count: {loop_count}\n')
        print(f'Will update again in {sleep_interval} seconds...\n')
        await asyncio.sleep(sleep_interval)
        loop_count = loop_count + 1

# ---------- PROGRAM START ----------

asyncio.run(main())