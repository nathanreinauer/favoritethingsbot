import praw
import prawcore
import config
import time
import os
from datetime import datetime, timedelta
import traceback
from collections import Counter
from praw.models import Comment
from praw.models import Message
from statistics import mean
import re
import winsound
import random
import enchant
from textblob import TextBlob
from profanity_check import predict
import warnings

def fxn():
    warnings.warn("deprecated", DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fxn()


isWord = enchant.Dict("en_US")

def beep():
    frequency = 1000
    duration = 500
    winsound.Beep(frequency, duration)

def bot_login():
    print("--- Logging in...")
    r = praw.Reddit(username = config.username,
                password = config.password,
                client_id = config.client_id,
                client_secret = config.client_secret,
                user_agent = "JulieAndrewsBot v1")
    print("--- Logged in!\n")
    return r      

def run_bot(r):
    #print(getInfo(r))
    print("--- Deleting older comments. This may take several minutes.")
    deleteBadComments(r)
    checkMessages(r)
    runTimeMessages = time.time()
    print("--- Streaming new comments...\n")
    startTime = time.time()
    allTimes = []
    for comment in r.subreddit('all').stream.comments():
        finalList = phraseIsGood(comment)
        if finalList:
            if isUserAMod(comment):
                print("--- User is a mod! Skipping...")
            else:
                if (time.time() - runTimeMessages) >= 90:
                    checkMessages(r)
                    deleteBadComments(r)
                    runTimeMessages = time.time()
                elapsedTime = time.time() - startTime
                allTimes.append(elapsedTime)
                averageTime = sum(allTimes) / len(allTimes)
                elapsedMin = str(int(elapsedTime/60))
                elapsedSec = str(int(elapsedTime%60))
                averageMin = str(int(averageTime/60))
                averageSec = str(int(averageTime%60))
                postReply(comment, finalList)
                with open ("TimeToPost.txt", "a") as f:
                    f.write("{}\n".format(str(elapsedTime)))
                print("--- Posted! Time: {}:{} Average time: {}:{}".format(elapsedMin, elapsedSec.zfill(2), averageMin, averageSec.zfill(2)))
                startTime = time.time()
                beep()

def getInfo(r):
    # Get average time
    averageTTP = 0
    ttp = ""
    with open("TimeToPost.txt", "r") as f:
        ttp = f.read()
        ttp = ttp.split("\n")
        ttp = filter(None, ttp) #This filters out the blank line at the end of the list from '\n'
    ttp = list(map(float, ttp))
    averageTTP = int(sum(ttp)/len(ttp))

    # Get actual lyrics
    class actualWord:
        def __init__(self, word, count):
            self.word = word
            self.count = count
    pastPhrasesText = ""
    wordList = []
    wordListText = ""
    with open("PastPhrases.txt", "r") as f:
        pastPhrasesText = f.read()
    for word in actualLyrics:
        wordCount = pastPhrasesText.count(word)
        if wordCount > 0:
            wordList.append(actualWord(word, wordCount))
    wordList.sort(key=lambda x: x.count, reverse=True)
    for word in wordList:
        wordListText += "{} ({}), ".format(word.word, str(word.count))
            
    # Info
    infoText = "**How do I work?** First I read as many new comments as I can and turn each one into a list of noun phrases"
    infoText += " (things like 'raindrop' or 'brown paper package'). Next I pluralize them and run them through an algorithm"
    infoText += " to determine the number of syllables each noun phrase contains. If I find that your comment contains"
    infoText += " three noun phrases of 2 syllables each, one noun phrase of 5 syllables, and one noun phrase of 6 syllables"
    infoText += " I simply insert them into the lyrics and post them back to you! Finding noun phrases, determining syllables counts,"
    infoText += " and pluralizing words are all very tricky and I often make mistakes! But my developer is always tweaking and adding"
    infoText += " new rules (and exceptions to rules) to make finding your Favorite Things more accurate!\n\n"

    # Get common phrases
    allPhrases = getAllPhrases()
    mostCommon = ""
    c = Counter(allPhrases).most_common(5)
    for word, count in c:
        mostCommon += "{} ({}), ".format(word, count)

    # Bad Word Count
    class badWord:
        def __init__(self, word, count):
            self.word = word
            self.count = count
    predictBadWords = predict(allPhrases)
    badWords = []
    badWordsText = ""
    for i, num in enumerate(predictBadWords):
        if num == 1:
            word = allPhrases[i]
            wordCount = allPhrases.count(word)
            badWords.append(badWord(word, wordCount))
    badWords.sort(key=lambda x: x.count, reverse=True)
    bwList = []
    for word in badWords:
        bwList.append("{} ({}), ".format(word.word, word.count))
    seen = set()
    vowels = "aeiou"
    counter = 0
    for item in bwList:
        if item not in seen and counter < 3:
            seen.add(item)
            for c in item:
                if c in vowels:
                    item = item.replace(c, "\*")
            badWordsText += item
            counter += 1
       
    # Most upvoted
    allComments = r.redditor("JulieAndrewsBot").comments.new(limit=None)
    topScore = 0
    topComment = ""
    topCommentLink = ""
    numberOfComments = 0
    for c in allComments:
        numberOfComments += 1
        if c.score > topScore:
            topScore = c.score
            topComment = c.body
            topCommentLink = c.parent().permalink
    topComment = topComment.split("---")[0]
    topComment = topComment.split("\n\n")
    topCommentText = ""
    for line in topComment:
        topCommentText += ">" + line + "\n\n"
    
    # Percentage that were 'bad' and deleted
    deletedComments = len(pastPhrases) - numberOfComments
    deletedPercent = "{}%".format(str(int((deletedComments/len(pastPhrases))*100)))

    # Friendliest sub
    goodBotCount = 0
    goodBotList = []
    with open ("good_bot.txt", "r") as f:
        goodBotList = f.read()
        goodBotList = re.findall(r'r/(.*?)\n', goodBotList)
    subsList = Counter(goodBotList)
    friendlySub = max(goodBotList, key=subsList.get)

    infoReply = infoText
    infoReply += "**Most popular comment:** [{} upvotes]({})\n\n{}[See all my top comments](https://www.reddit.com/user/JulieAndrewsBot/?sort=top)\n\n".format(topScore, topCommentLink, topCommentText[:-3])
    infoReply += "**Average time to find new lyrics:** {} seconds\n\n".format(averageTTP)
    infoReply += "**Percentage of comments I self-deleted:** {}\n\n^(Every few minutes I automatically delete all comments older than an hour that do not have at least 1 upvote, a gilding, or replies. I do the same thing with comments older than 4 hours, but they must have at least 5 upvotes to stay. Gotta keep my history clean and entertaining!)\n\n".format(deletedPercent)
    infoReply += "**Most common noun phrases I have found & posted:** {}\n\n".format(mostCommon[:-2])
    infoReply += "**Nouns from the [original lyrics](https://www.google.com/search?q=favorite+things+lyrics) I have found & posted:** {}\n\n".format(wordListText[:-2])
    infoReply += "**Top 3 most common naughty phrases found & posted:** {}\n\n".format(badWordsText[:-2])
    infoReply += "**Friendliest sub (most 'Good bot' replies):** r/{}\n\n".format(friendlySub)
    infoReply += "**Number of times people have replied to my lyrics with 'WTF':** {}\n\n".format(str(len(wtfList)))
    return infoReply

def getAllPhrases():
    phrases = []
    almostFinalPhrases = []
    finalPhrases = []
    for phrase in pastPhrases:
        phrases.append(phrase.split("[ID")[0])
    for phrase in phrases:
        x = phrase.split("/")
        for i in x:
            almostFinalPhrases.append(i)
    for phrase in almostFinalPhrases:
        x = phrase.split(",")
        for i in x:
            finalPhrases.append(i.strip())
    return finalPhrases
    
def deleteBadComments(r):
    allComments = r.redditor("JulieAndrewsBot").comments.new(limit=None)
    currentTime = time.time()
    oldComments = []
    olderComments = []
    deletedComments = 0
    # Comments older than 1 hour...
    for c in allComments:
        if c.created_utc < (currentTime - 3600): # 3600 is 1 hour
            oldComments.append(c)
    for c in oldComments:
        if c.score < 1 and c.gilded == 0 and len(c.replies) == 0:
            c.delete()
            deletedComments += 1
    # Comments older than 4 hours...
    for c in allComments:
        if c.created_utc < (currentTime - 14400): # 14400 is 4 hours
            olderComments.append(c)
    for c in olderComments:
        if c.score < 5 and c.gilded == 0 and len(c.replies) == 0:
            c.delete()
            deletedComments += 1
    if deletedComments > 0:
        print("--- {} older comment(s) have been deleted.".format(str(deletedComments)))

def postReply(comment, finalList):
    replyText = "*{} on {} and {} on kittens* \N{Eighth Note}\n\n".format(finalList[0], finalList[1], finalList[2])
    replyText += "*{} and warm woolen mittens* \N{Eighth Note}\n\n".format(finalList[3])
    replyText += "*{} tied up with strings* \N{Eighth Note}\n\n".format(finalList[4])
    replyText += "*These are a few of my favorite things!* \N{Eighth Note}\n\n---\n[sing it](https://youtu.be/kwN3LJdGyuU?t=20) / ^(reply 'info' to learn more about this bot (including fun stats!)^)"
    justWords = "{}, {}, {} / {} / {}".format(finalList[0], finalList[1], finalList[2], finalList[3], finalList[4])
    try:
        print(justWords)
        comment.reply(replyText)
        with open ("PastPhrases.txt", "a") as f:
            f.write(deEmojify(justWords) + '[ID: ' + str(comment.id) + ', SUB: r/' + str(comment.subreddit) + ', TIME: ' + str(time.time()) + ']' + "\n")
    except praw.exceptions.APIException as e:
        if e.error_type == "RATELIMIT":
            rateLimitError(e)
        else:
            print(e)
    except prawcore.exceptions.Forbidden as e:
            print(e)
            print("--- Possibly banned? Subreddit: r/{}".format(str(comment.subreddit)))

def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')

def rateLimitError(e):
    msg = str(e).lower()
    search = re.search(r'\b(minutes)\b', msg)
    minutes = int(msg[search.start()-2]) + 1
    t = datetime.now() + timedelta(minutes = minutes)
    wakeTime = t.strftime("%H:%M:%S")
    print("--- Ratelimited for " + str(minutes) + " minutes. Will resume at " + wakeTime + ".")
    time.sleep(minutes*60)

def isUserAMod(comment):
    mods = list(comment.subreddit.moderator())
    if comment.author.name in mods:
        return True
    if comment.author.name == "AutoModerator":
        return True
    if comment.author.name.lower() == "credobot":
        return True
    if comment.author.name.lower() == "julieandrewsbot":
        return True

def phraseIsGood(comment):
    phrase = comment.body
    if len(phrase) > 2000:
        return False
    if str(comment.subreddit) in bannedSubs:
        return False
    firstNounList = TextBlob(phrase).noun_phrases.singularize().pluralize()
    for word in goodWordsList:
        if word in phrase:
            firstNounList.append(word)
    nounList = []
    for noun in firstNounList:
        n = re.sub(r'[^a-zA-Z ]', '', noun)
        nounPhrase = ""
        words = n.split(' ')
        for word in words:
            if len(word) > 2 and (isWord.check(word) or word in goodWordsList)and word not in badWordsList:
                nounPhrase += word + " "
        if len(nounPhrase) > 2:
            nounList.append(nounPhrase.strip())
    twoSylNouns = []
    fiveSylNouns = []
    sixSylNouns = []
    finalList = []
    for noun in nounList:
        if syllableCount(noun) == 2 and noun not in twoSylNouns and noun.lower() not in badWordsList:
            twoSylNouns.append(noun)
        if syllableCount(noun) == 5 and noun not in fiveSylNouns and noun.lower() not in badWordsList:
            fiveSylNouns.append(noun) 
        if syllableCount(noun) == 6 and noun.lower() not in badWordsList:
            sixSylNouns.append(noun)
    if len(twoSylNouns) > 2:
        if len(fiveSylNouns) > 0:
            if len(sixSylNouns) > 0:
                finalList.append(twoSylNouns[0].capitalize())
                finalList.append(twoSylNouns[1])
                finalList.append(twoSylNouns[2])
                finalList.append(fiveSylNouns[0].capitalize())
                finalList.append(sixSylNouns[0].capitalize())
                return finalList

def checkMessages(r):
    newMessageCount = 0
    for item in r.inbox.unread(limit=50):
        newMessageCount += 1
        if "You've been permanently banned from participating in r/" in item.subject or "You've been temporarily banned from participating in r/" in item.subject:
            bannedSub = item.subject.split('/')[1]
            with open("BannedSubs.txt", "a") as f:
                f.write(bannedSub + "\n")
            print("--- r/{} added to the ban list.".format(bannedSub))
            item.mark_read()
            newMessageCount -= 1
        elif "info" in item.body.lower() and item.author.name.lower() != "sneakpeekbot":
            replyText = getInfo(r)
            try:
                item.reply(replyText)
                print("--- Replied to 'info'.")
                item.mark_read()
                newMessageCount -= 1
            except:
                print("--- Error!")
                traceback.print_exc()
        elif "good bot" in item.body.lower() and not ">" in item.body:
            try:
                with open ("good_bot.txt", "a") as f:
                    f.write("ID: {}, USER: {}, SUB: r/{}\n".format(str(item.id), str(item.author.name), str(item.subreddit)))
                print("--- I'm a Good Bot! Saved to textfile.")
                item.mark_read()
                newMessageCount -= 1
            except:
                print("--- Error! Message/User may have been deleted.")
                continue
        elif ("wtf" in item.body.lower() or "what the fuck" in item.body.lower() or "what the actual fuck" in item.body.lower() or "what in the" in item.body.lower()) and not ">" in item.body and not "how do I work?" in item.parent().body.lower():
            try:
                with open ("wtf.txt", "a") as f:
                    f.write("ID: {}, USER: {}, SUB: r/{}\n".format(str(item.id), str(item.author.name), str(item.subreddit)))
                print("--- 'WTF' noted.")
                item.mark_read()
                newMessageCount -= 1
            except:
                print("--- Error! Message/User may have been deleted.")
                continue
    if newMessageCount > 0:
        print("--- {} new message(s) found!".format(str(newMessageCount)))

def getBadWordsList():
    if not os.path.isfile("BadWords.txt"):
        badWordsList = []
    else:
        with open("BadWords.txt", "r") as f:
            badWordsList = f.read()
            badWordsList = badWordsList.split("\n")
            badWordsList = filter(None, badWordsList) #This filters out the blank line at the end of the list from '\n'        
    return list(badWordsList)

def getGoodWordsList():
    if not os.path.isfile("GoodWords.txt"):
        goodWordsList = []
    else:
        with open("GoodWords.txt", "r") as f:
            goodWordsList = f.read()
            goodWordsList = goodWordsList.split("\n")
            goodWordsList = filter(None, goodWordsList) #This filters out the blank line at the end of the list from '\n'        
    return list(goodWordsList)
    
def getActualLyrics():
    if not os.path.isfile("ActualLyrics.txt"):
        actualLyrics = []
    else:
        with open("ActualLyrics.txt", "r") as f:
            actualLyrics = f.read()
            actualLyrics = actualLyrics.split("\n")
            actualLyrics = filter(None, actualLyrics) #This filters out the blank line at the end of the list from '\n'        
    return list(actualLyrics)

def getPastPhrases():
    if not os.path.isfile("PastPhrases.txt"):
        pastPhrases = []
    else:
        with open("PastPhrases.txt", "r") as f:
            pastPhrases = f.read()
            pastPhrases = pastPhrases.split("\n")
            pastPhrases = filter(None, pastPhrases) #This filters out the blank line at the end of the list from '\n'        
    return list(pastPhrases)

def getBadSubs():
    if not os.path.isfile("BadSubs.txt"):
        badSubs = []
    else:
        with open("BadSubs.txt", "r") as f:
            badSubs = f.read()
            badSubs = badSubs.split("\n")
            badSubs = filter(None, badSubs) #This filters out the blank line at the end of the list from '\n'        
    return list(badSubs)

def getBannedSubs():
    if not os.path.isfile("BannedSubs.txt"):
        bannedSubs = []
    else:
        with open("BannedSubs.txt", "r") as f:
            bannedSubs = f.read()
            bannedSubs = bannedSubs.split("\n")
            bannedSubs = filter(None, bannedSubs) #This filters out the blank line at the end of the list from '\n'        
    return list(bannedSubs)

def getWTFList():
    if not os.path.isfile("wtf.txt"):
        wtfList = []
    else:
        with open("wtf.txt", "r") as f:
            wtfList = f.read()
            wtfList = wtfList.split("\n")
            wtfList = filter(None, wtfList) #This filters out the blank line at the end of the list from '\n'        
    return list(wtfList)


# I DID NOT WRITE THIS FUNCTION, IT IS FREE USE CODE I FOUND ON GITHUB FOR DETERMINING VOWEL COUNT:
def syllableCount(word):
    word = word.lower()

    # exception_add are words that need extra syllables
    # exception_del are words that need less syllables

    exception_add = ['serious','crucial']
    exception_del = ['fortunately','unfortunately']

    co_one = ['cool','coach','coat','coal','count','coin','coarse','coup','coif','cook','coign','coiffe','coof','court']
    co_two = ['coapt','coed','coinci']

    pre_one = ['preach']

    syls = 0 #added syllable number
    disc = 0 #discarded syllable number

    #1) if letters < 3 : return 1
    if len(word) <= 3 :
        syls = 1
        return syls

    #2) if doesn't end with "ted" or "tes" or "ses" or "ied" or "ies", discard "es" and "ed" at the end.
    # if it has only 1 vowel or 1 set of consecutive vowels, discard. (like "speed", "fled" etc.)

    if word[-2:] == "es" or word[-2:] == "ed" :
        doubleAndtripple_1 = len(re.findall(r'[eaoui][eaoui]',word))
        if doubleAndtripple_1 > 1 or len(re.findall(r'[eaoui][^eaoui]',word)) > 1 :
            if word[-3:] == "ted" or word[-3:] == "tes" or word[-3:] == "ses" or word[-3:] == "ied" or word[-3:] == "ies" :
                pass
            else :
                disc+=1

    #3) discard trailing "e", except where ending is "le"  

    le_except = ['whole','mobile','pole','male','female','hale','pale','tale','sale','aisle','whale','while']

    if word[-1:] == "e" :
        if word[-2:] == "le" and word not in le_except :
            pass

        else :
            disc+=1

    #4) check if consecutive vowels exists, triplets or pairs, count them as one.

    doubleAndtripple = len(re.findall(r'[eaoui][eaoui]',word))
    tripple = len(re.findall(r'[eaoui][eaoui][eaoui]',word))
    disc+=doubleAndtripple + tripple

    #5) count remaining vowels in word.
    numVowels = len(re.findall(r'[eaoui]',word))

    #6) add one if starts with "mc"
    if word[:2] == "mc" :
        syls+=1

    #7) add one if ends with "y" but is not surrouned by vowel
    if word[-1:] == "y" and word[-2] not in "aeoui" :
        syls +=1

    #8) add one if "y" is surrounded by non-vowels and is not in the last word.

    for i,j in enumerate(word) :
        if j == "y" :
            if (i != 0) and (i != len(word)-1) :
                if word[i-1] not in "aeoui" and word[i+1] not in "aeoui" :
                    syls+=1

    #9) if starts with "tri-" or "bi-" and is followed by a vowel, add one.

    if word[:3] == "tri" and word[3] in "aeoui" :
        syls+=1

    if word[:2] == "bi" and word[2] in "aeoui" :
        syls+=1

    #10) if ends with "-ian", should be counted as two syllables, except for "-tian" and "-cian"

    if word[-3:] == "ian" : 
    #and (word[-4:] != "cian" or word[-4:] != "tian") :
        if word[-4:] == "cian" or word[-4:] == "tian" :
            pass
        else :
            syls+=1

    #11) if starts with "co-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.

    if word[:2] == "co" and word[2] in 'eaoui' :

        if word[:4] in co_two or word[:5] in co_two or word[:6] in co_two :
            syls+=1
        elif word[:4] in co_one or word[:5] in co_one or word[:6] in co_one :
            pass
        else :
            syls+=1

    #12) if starts with "pre-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.

    if word[:3] == "pre" and word[3] in 'eaoui' :
        if word[:6] in pre_one :
            pass
        else :
            syls+=1

    #13) check for "-n't" and cross match with dictionary to add syllable.

    negative = ["doesn't", "isn't", "shouldn't", "couldn't","wouldn't"]

    if word[-3:] == "n't" :
        if word in negative :
            syls+=1
        else :
            pass   

    #14) Handling the exceptional words.

    if word in exception_del :
        disc+=1

    if word in exception_add :
        syls+=1     

    # calculate the output
    return numVowels - disc + syls

        

r = bot_login()
wtfList = getWTFList()
goodWordsList = getGoodWordsList()
actualLyrics = getActualLyrics()
badWordsList = getBadWordsList()
pastPhrases = getPastPhrases()
badSubs = getBadSubs()
bannedSubs = getBannedSubs()

while True:
    run_bot(r)


