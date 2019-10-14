#Discord Bot for Cakechat
#By Victor Yuska

import discord
import asyncio
import requests
import random
import time
import os
import sys
import re

from textblob import TextBlob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from collections import deque


from cakechat.utils.env import init_cuda_env

init_cuda_env()

from cakechat.api.response import get_response
from cakechat.config import INPUT_CONTEXT_SIZE, DEFAULT_CONDITION

client = discord.Client()

_context = deque(maxlen=INPUT_CONTEXT_SIZE)

from cakechat.api.v1.server import app

def getAllUsersCount():
    guilds = client.guilds
    user_count = 0
    for g in guilds:
         user_count += len(g.members)
    return("Current user count: " + str(user_count))

@client.event
async def on_ready():
    print('Logged in as '+client.user.name+' (ID:'+str(client.user.id)+') | '+str(len(client.guilds))+' servers | ' + getAllUsersCount())
    await client.change_presence(activity=discord.Game(name='chat with me!'))
    global es
    es = EmotionState()




class EmotionState: #Class to store emotional dats
    def __init__(self):
        self.thought_polarity = 0.0 #Positivity/Negativity
        self.thought_subjectivity = 0.0 #Subjectivity/Objectivity
        self.emotions_dividend = 2.0 #Controls intensity of the sentiment detection; lower is more intense, higher is less
        self.emotions_fade = 0.04
        self.emotions_minimum = 0.1
        
    async def new_sentiment_analysis(self, input):
        txtblob = TextBlob(input)
        sent = txtblob.sentiment
        COND = DEFAULT_CONDITION
        #TO-DO: More fine tuning
        self.thought_subjectivity += sent.subjectivity
        #self.thought_subjectivity -= 0.25
        if(self.thought_polarity >= self.emotions_minimum):
            self.thought_polarity -= self.emotions_fade
        if(self.thought_polarity <= 0 - self.emotions_minimum):
            self.thought_polarity += self.emotions_fade
        if(self.thought_subjectivity < 0.0):
            self.thought_subjectivity = 0.0
        if(self.thought_subjectivity > 1.0):
            self.thought_subjectivity = 1.0
        self.thought_polarity += sent.polarity / self.emotions_dividend #Adjust polarity based on sentiment detection results
        if(self.thought_polarity < -1.0):
            self.thought_polarity = -1.0
        if(self.thought_polarity > 1.0):
            self.thought_polarity = 1.0
        if(self.thought_subjectivity >= 0.0 and self.thought_subjectivity <= 0.4): #If feeling neutral and indifferent, then change condition to neutral
            COND = "neutral"
        if(self.thought_subjectivity >= 0.4 and self.thought_polarity >= 0.6):
            COND = "joy"
        if(self.thought_subjectivity >= 0.4 and self.thought_polarity <= -0.1):
            COND = "sadness"
        if(self.thought_subjectivity >= 0.55 and self.thought_polarity <= -0.45):
            COND = "anger"
        if(self.thought_subjectivity >= 0.15 and self.thought_polarity <= -0.75):
            COND = "fear"
        print("Condition: " + COND + "; Polarity: " + str(self.thought_polarity) + "; Subjectivity: " + str(self.thought_subjectivity))
        return COND #Return the condition to respond with!



#Determine the intent of a sentence and the emotion to respond with (TODO: This should be more dynamic! Rework coming eventually)
def sentiment_analysis(input): 
    txtblob = TextBlob(input)
    sent = txtblob.sentiment
    #The below values should be fine-tuned or replaced completely with a more dynamic system
    if(sent.subjectivity < 0.27):
        COND = "neutral"
    elif(sent.polarity < -0.88):
       COND = "fear"
    elif(sent.polarity > 0.4):
        COND = "joy"
    elif(sent.polarity < -0.67):
        COND = "anger"
    elif(sent.polarity < -0.39):
        COND = "sadness"
    else:
        COND = DEFAULT_CONDITION
    #await client.change_presence(activity=discord.Game(name='feeling ' + COND)) #Display the bot's emotion as a status
    return COND #Return the condition to respond with!


#Called when a message is received
@client.event
async def on_message(message):
    if not (message.author == client.user): #Check to ensure the bot does not respond to its own messages
        if(client.user.mentioned_in(message) or isinstance(message.channel, discord.abc.PrivateChannel)): #Check if the bot is mentioned or if the message is in DMs
            async with message.channel.typing(): #Show that the bot is typing
                txtinput = message.content.replace("<@" + str(client.user.id) + ">", "")  #Filter out the mention so the bot does not get confused
                if(len(txtinput) > 220): #Spam protection
                    txt = "I am sorry, that is too long for me."
                dicestr = re.search("Roll (\d{1,2})d(\d{1,3})",message.content)
                if(dicestr != None):
                    dice = [dicestr.group(1), dicestr.group(2)]
                    output = "I rolled "
                    for i in range(int(dice[0])):
                        output += str(random.randrange(1, int(dice[1]))) + ", "
                    txt = output
                else:
                    blob = TextBlob(txtinput)
                    lang = blob.detect_language()
                    if(lang != "en"):
                        txtinput = str(blob.translate(from_lang=lang, to="en"))
                    _context.append(txtinput)
                    COND = await es.new_sentiment_analysis(txtinput) #Determine how to respond to the sentence emotionally
                    await client.change_presence(activity=discord.Game(name='feeling ' + COND)) #Display the bot's emotion as a status
                    txt = get_response(_context, COND) #Get a response!
                    response_blob = TextBlob(txt)
                    if(lang != "en"):
                        txt = str(response_blob.translate(from_lang="en", to=lang))
                bot_message = await message.channel.send(txt) #Fire away!
print('Starting...')
client.run('TOKEN_GOES_HERE') #Replace TOKEN_GOES_HERE with your bot's API token
