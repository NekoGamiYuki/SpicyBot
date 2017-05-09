"""
Author: NekoGamiYuki
Version: 1.0.0

Description:
A way to create and manage quotes. Specifically made for quick creation of
quotes during livestreams.
"""

# TODO: After completing the necessary parts of the quote functionality, read up
#       "Fluent Python"
# TODO: Add documentation to all functions.
# TODO: Use Emote class feature to find out whether emotes are at the start or
#       end of a quote. Add appropriate spacing to allow the emote to show.
# TODO: Maybe make a statistics value that shows how many times a quote is used
#       (excluding random appears?).
# TODO: Log who creates/deletes/edits a quote and maybe the changes they made?
# TODO: ^ If done, consider creating a "revert/undo" function to revert a quote
#       to its previous version. Also log that. Have the revert function work
#       both ways. If used on a reverted quote
#       it'll return to the latest edit.
# TODO: Make broadcaster_nickname changes apply to the quotes file
# TODO: When fixing up the entire set of code, consider implementing a system
#       to stop quotes for being repeated for some time.
# TODO: Fix bug where commands like '!quote add --name=amama... Test' result
#       in a quote that looks like this:
#           "--name=amama... Test" - amama... Test (DATE)

# Imported Modules--------------------------------------------------------------
import re
import os
import datetime
import warnings
from random import randint
from difflib import SequenceMatcher
import spicytwitch

# Global Variables--------------------------------------------------------------
IRC = spicytwitch.irc
module_tools = spicytwitch.bot.modules

DELETED_FILL = "###DELETED###"

# Offset to account for spaces and any other extra characters when formatting
# the quote, so that it doesn't exceed twitch's character limit.
SIZE_OFFSET = 20

# Max size of a message
MAX_SIZE = 500

SAVE_FORMAT = "{}|{}|{}\n"
QUOTE_FORMAT = "\"{}\" - {} ({})"
INDEX_FORMAT = " [#{}]"

RESERVED_COMMAND_NAMES = [
    "quote"
]

quotes = {}
nicknames = {}


# Regex-------------------------------------------------------------------------
quote_read_regex = r"quote( \d+)?"
quote_edit_regex = r"quote edit (\d+)( --\w+=\w+)? (.+)"
quote_add_regex = r"quote add( --\w+=\w+)? (.+)"
quote_delete_regex = r"quote delete (\d+)"
quote_set_nickname_regex = r"quote set nickname (.+)"

# Module Registration-----------------------------------------------------------
module_tools.register_command_module()
logger = spicytwitch.log_tools.create_logger()
storage_directory = module_tools.get_storage_directory()


# Exceptions--------------------------------------------------------------------
class NegativeIndex(Exception):
    pass

class IndexTooLarge(Exception):
    pass

class ChannelNotInitiated(Exception):
    pass

class DoesNotExist(Exception):
    pass


# Quotes management-------------------------------------------------------------
# Setting up storage
quotes_directory = os.path.join(storage_directory, 'quotes')
if not os.path.exists(quotes_directory):
    logger.debug("Created directory for quotes files")
    os.mkdir(quotes_directory)

# Setting up quotes files for joined channels
def initialize_channels():
    global quotes
    for channel in IRC.channels:
        if channel not in os.listdir(quotes_directory):
            with open(os.path.join(quotes_directory, channel), 'w') as quotes_file:
                # Create empty file
                logger.debug("Created empty quotes file for channel: {}".format(channel))
                quotes_file.close()
                quotes[channel] = []
initialize_channels()
                

# Loading quotes
for channel in os.listdir(quotes_directory):

    channel_name = os.path.basename(channel)
    logger.info("Loading quotes for: {}".format(channel_name))

    if channel_name not in quotes:
        logger.debug("Creating empty list to store quotes in")
        quotes[channel_name] = []

    logger.debug("Opening quotes file")
    with open(os.path.join(quotes_directory, channel), 'r') as quotes_file:
        for line in quotes_file.readlines():
            try:
                information = line.rsplit('|', 2)
                quote_text = information[0]
                quoted_person = information[-2].strip()
                quote_date = information[-1].strip()

                quotes[channel_name].append([
                    quote_text, quoted_person, quote_date
                ])
            except IndexError:
                warnings.warn(
                    "Issue parsing quotes file: {}".format(
                        os.path.join(quotes_directory, channel)
                    )
                )
                pass
def manage_spacing(quote: str, user: IRC.User) -> str:
    new_quote = quote
    front_done = False
    back_done = False
    for emote in user.emotes:

        if front_done and back_done:
            break

        data = new_quote.split()
        possible_emote = user.message[emote.position['start']:emote.position['end']]
        if data[0] == possible_emote and not front_done:
            # Add a space to the start
            new_quote = ' '+new_quote
            front_done = True
        if data[-1] == possible_emote and not back_done:
            # Add a space to the end
            new_quote += ' '
            back_done = True

    return new_quote



def edit_quote(channel: str, index: int, full_quote: list) -> int:
    global quotes
    channel_file = os.path.join(quotes_directory, channel)

    # Make sure index is not larger than the number of quotes
    if index > len(quotes[channel]):
        raise IndexTooLarge("Index larger than number of quotes")

    # Make sure index is positive, account for Zero-based indexing since our
    # input will come from users.
    if index > 0:
        index -= 1
    elif index < 0:
        raise negativeindex("quote index must not be negative")

    # create copy of current state of file
    logger.debug("Creating copy of quotes file in memory")
    file_copy = None
    with open(channel_file, 'r') as quotes_file:
        file_copy = quotes_file.readlines() 

    # rewrite the file, updating the quote when we reach the input index
    logger.debug("Updating quotes file for new quote")
    with open(channel_file, 'w') as quotes_file:
        for i, line in enumerate(file_copy):
            if i ==  index:
                quotes_file.write(SAVE_FORMAT.format(*full_quote))
            else:
                # stripping just to ensure that only one newline is output
                quotes_file.write(line.strip() + '\n')

    # update the channel's quotes list
    logger.debug("Updating channel '{}' quote list".format(channel))
    quotes[channel][index] = full_quote

    
def add_quote(channel: str, full_quote: list) -> bool:
    global quotes
    channel_file = os.path.join(quotes_directory, channel)

    # check for duplicates
    logger.debug("Checking if new quote is a duplicate")
    for quote in quotes:
        if full_quote[0].lower() == quote[0].lower():
            logger.debug(
                "Quote was a duplicate in channel '{}': {}".format(
                    channel, QUOTE_FORMAT.format(*full_quote)
                )
            )
            return False  # duplicate quote

    # save quote to file
    logger.debug("Saving to quotes file")
    with open(channel_file, 'a') as quotes_file:
        quotes_file.write(SAVE_FORMAT.format(*full_quote))

   # add quote to list
    quotes[channel].append(full_quote)

    return True
    
    
def delete_quote(channel: str, index: int, deleter: str) -> bool:

    if index > 0:
        check_index = index - 1
    else:
        check_index = index

    if index > len(quotes[channel]):
        return "Quote #{} does not exist! sfhHM".format(index)

    quote_copy = quotes[channel][check_index]
    if quote_copy[0] == DELETED_FILL and quote_copy[-2] == DELETED_FILL:
        return "Quote #{} was already deleted on {}.".format(
            index, quote_copy[-1]
        )
    else:
        edit_quote(
            channel,
            index,
            [DELETED_FILL, DELETED_FILL, datetime.datetime.now().date()]
        )
        logger.info(
            "User {} has deleted quote #{}, which said: {}".format(
                deleter, index,  QUOTE_FORMAT.format(*quote_copy)
            )
        ) 
        return "Quote #{index} has been deleted. Rip quote #{index} sfhSAD".format(index=index)


def get_quote(channel: str, index: int) -> str:
    if index < 0:
        raise NegativeIndex("Index must not be negative!")
    elif index > 0:
        index -= 1

    try:
        chosen_quote = quotes[channel][index]

        if chosen_quote[0] == DELETED_FILL and chosen_quote[1] == DELETED_FILL:
            # NOTE: If someone asks for quote 1, it'll be turned into 0 and then
            #       it won't be incremented back... I should find a way to fix
            #       this issue.
            if index > 0:
                index += 1
            return "Quote #{} was deleted on {} sfhSAD".format(index, chosen_quote[-1])
        else:
            return QUOTE_FORMAT.format(*chosen_quote)
    except IndexError:
        if index > 0:
            # Increment it for user readability
            index += 1

        return "Quote #{} does not exist.".format(index)


def get_random_quote(channel: str) -> str:
    quote_count = len(quotes[channel])

    if quote_count == 0:
        return "There are no quotes! sfhSAD"

    random_index = randint(0, quote_count-1)
    chosen_quote = quotes[channel][random_index]
        

    while chosen_quote[0] == DELETED_FILL and chosen_quote[1] == DELETED_FILL:
        random_index = randint(0, quote_count)
        chosen_quote = quotes[channel][random_index]

    return QUOTE_FORMAT.format(*chosen_quote) + INDEX_FORMAT.format(random_index + 1)

def save_all_quotes(channel: str) -> bool:
    try:
        channel_quotes = quotes[channel]
        with open(os.path.join(quotes_directory, channel), 'w') as quotes_file:
            for quote in channel_quotes:
                quotes_file.write(SAVE_FORMAT.format(*quote))
        return True
    except KeyError:
        return False

# Nickname management-----------------------------------------------------------
# Setting up storage
nicknames_file_path = os.path.join(storage_directory, 'nicknames.txt')
if 'nicknames.txt' not in os.listdir(storage_directory):
    with open(nicknames_file_path, 'w') as nicknames_file:
        nicknames_file.close()


# Load nicknames
with open(nicknames_file_path, 'r') as nicknames_file:
    for index, line in enumerate(nicknames_file.readlines()):
        information = line.rsplit('=', 1)

        if len(information) < 2:
            warnings.warn(
                "Issue loading nickname for line #{} in file '{}'!".format(
                    index, nicknames_file_path
                )
            )
            continue

        channel = information[0].strip()
        nickname = information[1].strip()

        nicknames[channel] = nickname

print(nicknames)

def save_nicknames():
    with open(nicknames_file_path, 'w') as nicknames_file:
        for channel in nicknames:
            nicknames_file.write('{}={}\n'.format(channel, nicknames[channel]))


def set_nickname(new_nickname: str, channel: str):
    global nicknames
    global quotes

    # Update channel quotes to use new nickname
    update_these = quotes[channel]
    current_nickname = get_streamer_nickname(channel)
    for index, quote in enumerate(update_these):
        if quote[1] == current_nickname:
            update_these[index] = [quote[0], new_nickname, quote[-1]]

    quotes[channel] = update_these
    save_all_quotes(channel)

    # Set new nickname
    nicknames[channel] = new_nickname
    save_nicknames()


def get_streamer_nickname(channel: str) -> str:
    """Returns channel nickname, if not found it returns the channel's name
    """

    try:
        return nicknames[channel]
    except KeyError:
        return channel


# Similarity tests--------------------------------------------------------------
# TODO: Implement similarity tests.
# NOTE: I can see this maybe getting annoying so it should be possible to toggle.
# NOTE: We could respond with something like:
#       "That quote is rather similar to quote #{} sfhHM ... Maybe you should
#       take a look?"
#       But still make the quote, just in case.
"""
def _quote_similarity(channel_name: str, quote_text: str) -> str:
    if channel_quotes[channel_name]:
        similarity = []
        for quote in channel_quotes[channel_name]:
            similarity.append(SequenceMatcher(None, quote[0], quote_text).ratio())

        similarity_index, highest_similarity = max(enumerate(similarity), key=operator.itemgetter(1))
        if highest_similarity == 1.0:
            return "FeelsBadMan looks like your quote is already in the system. Check quote #{}".format(similarity_index)
"""


# Command functions-------------------------------------------------------------
def quote_count(user: IRC.User):
    """
    Sends a message to the channel that 'user' chatted from, stating the current
    number of quotes.
    """

    try:
        channel_quotes = quotes[user.chatted_from]
    except KeyError:
        logger.warning(
            "Channel '{}' is missing from quotes dictionary!".format(user.chatted_from)
        )
        initialize_channels()
        channel_quotes = quotes[user.chatted_from]

    if channel_quotes:
        # Getting number of quotes
        quote_count = len(channel_quotes)

        # Getting number of deleted quotes
        deleted_count = 0
        for quote in channel_quotes:
            if quote[0] == "###DELETED###" and quote[1] == "###DELETED###":
                deleted_count += 1

        if quote_count - deleted_count == 0:
            if quote_count > 1:
                IRC.chat("WutFace There are only deleted quotes, "
                            "{} of them! WutFace".format(deleted_count),
                            user.chatted_from)
            elif quote_count == 1:
                IRC.chat("WutFace There is only one quote and it was "
                            "deleted! WutFace", user.chatted_from)

        elif quote_count > 150:
            IRC.chat(" NotLikeThis There are {} quotes and {} "
                        "are deleted! Will they ever stop!? "
                        "NotLikeThis".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count > 100:
            IRC.chat("\m/ SwiftRage \m/ {} quotes, {} were "
                        "burned at the stake! FUCK YEAH! "
                        "\m/ SwiftRage \m/".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count > 50:
            IRC.chat("PogChamp there are {} quotes and {}"
                        " of those were deleted! "
                        "PogChamp".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count == 1:
            IRC.chat("FeelsGoodMan there is 1 quote. FeelsGoodMan",
                         user.chatted_from)
        else:
            if deleted_count == 1:
                deleted_message = "1 was deleted!"
            else:
                deleted_message = "{} were deleted".format(deleted_count)
            IRC.chat(
                "FeelsGoodMan there are {} quotes, of which {} "
                "FeelsGoodMan".format(quote_count, deleted_message),
                user.chatted_from)

        logger.info(
            "Read quote count of {} for channel '{}'. {} are deleted.".format(
                quote_count, user.chatted_from, deleted_count
            )
        )
    else:
        IRC.chat("FeelsBadMan there are no quotes. "
                    "FeelsGoodMan time to make some quotes!",
                    user.chatted_from)


def quote_read(user: IRC.User):
    try:
        temp = quotes[user.chatted_from]
    except KeyError:
        initialize_channels()

    parsed_input = re.findall(quote_read_regex, user.message)[0]

    if not parsed_input:
        random = True
    else:
        random = False
        try:
            quote_number = int(parsed_input.strip())
        except ValueError:
            user.send_message("sfhWUT Not even sure what you're trying to do.")
            return

    if random:
        IRC.chat(get_random_quote(user.chatted_from), user.chatted_from)
    else:
        IRC.chat(get_quote(user.chatted_from, quote_number) , user.chatted_from)


# TODO: I think my use of the "too_large" variable makes it so that the original
#       quote is not re-written to the file. This causes it to be deleted, which
#       is not what the _quote_edit() function should be doing...
def quote_edit(user: IRC.User):
    if not quotes:
        initialize_channels()

    parsed_input = re.findall(quote_edit_regex, user.message)[0]

    broadcaster_nickname = get_streamer_nickname(user.chatted_from)
    
    try:
        index = int(parsed_input[0])
    except ValueError: # This shouldn't ever be triggered, but... Gotta be safe.
        return  # NOTE: Maybe log something?

    if index > 0:
        copy_index = index - 1
    else:
        copy_index = index

    # Get information of the quotes current state
    try:
        quote_copy = quotes[user.chatted_from][copy_index]
    except IndexError:
        user.send_message("Quote #{} does not exist".format(index))
        return

    quoted_person =  quote_copy[-2]
    date = quote_copy[-1]
    quote_text = manage_spacing(parsed_input[-1], user)

    # Parse any options
    for option in parsed_input:
        if '--name=' in option:
            try:
                broadcaster_nickname = option.split('=', 1)[1]
            except IndexError:
                # TODO: Log issue with option being wrong
                break  # NOTE Remember to remove this if I add more options!

    was_deleted = False
    # Check if the quote was previously deleted
    if quoted_person == DELETED_FILL:
        was_deleted = True
        # Update with a new name for the person being quoted
        quoted_person = broadcaster_nickname

        # Update the date, as this is a new quote
        date = datetime.datetime.now().date()

    if len(quote_text) + len(quoted_person) + len(str(date)) + SIZE_OFFSET > MAX_SIZE:
        user.send_message("Your quote was too large, please shorten it! sfhMAD")
    else:
        # Update to the new quote
        new_quote = [quote_text, quoted_person, date]
        edit_quote(user.chatted_from, index, new_quote)

        if was_deleted:
            message = "Previously deleted quote has been reborn as a new " \
                      "quote! FeelsAmazingMan"
            logger.info(
                "{} has edited quote #{}, which was previously deleted, "
                "in channel '{}': {}".format(
                    user.name, index, user.chatted_from, 
                    QUOTE_FORMAT.format(*new_quote)
                )
            )
        else:
            message = "Quote #{} has been successfully edited! " \
                      "FeelsGoodMan".format(index)
            logger.info(
                "{} has edited quote #{} in channel '{}': {} -> {}".format(
                    user.name, index, user.chatted_from,
                    QUOTE_FORMAT.format(*quote_copy),
                    QUOTE_FORMAT.format(*new_quote)
                )
            )

        user.send_message(message)


# TODO: WHen new system is implemented. Use twitch.user.emotes[] and find the start and end of each emote. If one
#       starts at 0 or ends at the very last character of the quote, add a space to the left or right respectively.
def quote_add(user: IRC.User):
    if not quotes:
        initialize_channels()


    parsed_input = re.findall(quote_add_regex, user.message)[0]

    # Set the new quote
    new_quote = manage_spacing(parsed_input[-1].strip(), user)

    # Set the date
    quote_date = datetime.datetime.now().date()

    # Set default quoted person to the streamer's nickname.
    quoted_person = get_streamer_nickname(user.chatted_from)

    # Check if user input a different name for the quoted person.
    for option in parsed_input:
        if '-name=' in option:
            try:
                quoted_person = option.split('=', 1)[1]
            except IndexError:
                pass

    # Checking if new quote is too large
    if len(new_quote) + len(quoted_person) + len(str(quote_date)) + SIZE_OFFSET > MAX_SIZE:
        user.send_message("Your new quote was too large, please shorten it! "
                          "sfhMAD")
        return

    # Initialize quotes list for channel if not already available
    if user.chatted_from not in quotes.keys():
        quotes[user.chatted_from] = []

    # Check if that quote was already made before.
    for index, quote in enumerate(quotes[user.chatted_from]):
        if new_quote.strip().lower() == quote[0].strip().lower():
            user.send_message("That quote is the same as quote #{}! "
                              "sfhPLS".format(index + 1))
            return
    
    add_quote(user.chatted_from, [new_quote, quoted_person, quote_date])
    
    logger.info("User {}, in channel {}, has created quote #{}: {}".format(
        user.name, user.chatted_from, len(quotes[user.chatted_from]), 
        QUOTE_FORMAT.format(*quotes[user.chatted_from][-1])
    ))
    user.send_message("Quote #{} has been created! sfhWOW".format(len(quotes[user.chatted_from])))


def quote_delete(user: IRC.User):
    """
    Overwrites a quote with data relating to the deletion, including saving the
    date of deletion.
    """
    if not quotes:
        initialize_channels()

    parsed_input = re.findall(quote_delete_regex, user.message)[0]

    index = int(parsed_input)
    user.send_message(delete_quote(user.chatted_from, index, user.name))


def quote_set_nickname(user: IRC.User):
    parsed_input = re.findall(quote_set_nickname_regex, user.message)[0]
    print(parsed_input)
    set_nickname(parsed_input, user.chatted_from)
    user.send_message("Nickname has been changed to '{}'".format(parsed_input))
    logger.info(
        "User '{}' has changed the nickname of channel '{}' to '{}'".format(
            user.name, user.chatted_from, parsed_input
        )
    )
    
# Registering commands----------------------------------------------------------
module_tools.register_command(r'quotes', quote_count)
module_tools.register_command(quote_read_regex , quote_read)
module_tools.register_command(quote_add_regex , quote_add, "moderator")
module_tools.register_command(quote_edit_regex, quote_edit, "moderator")
module_tools.register_command(quote_delete_regex, quote_delete, "moderator")
module_tools.register_command(quote_set_nickname_regex, quote_set_nickname, "moderator")

# Reserving command names
module_tools.reserve_general_commands(RESERVED_COMMAND_NAMES)
