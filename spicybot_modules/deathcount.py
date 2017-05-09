"""
Author: NekoGamiYuki
Version: 1.0.0

Description:
A way to create and manage deaths during a game. Specifically made for quick
managing of deaths during livestreams.
"""

# Imported Modules--------------------------------------------------------------
import re
import sqlite3
import warnings
import os
import spicytwitch

# Global Variables--------------------------------------------------------------
IRC = spicytwitch.irc
module_tools = spicytwitch.bot.modules

RESERVED_COMMAND_NAMES = [
    "dc",
    "d",
    "dd",
    "deathcount"
]


# Regex-------------------------------------------------------------------------
deathcount_regex = r"dc( [\w\W ]+)?"
increment_regex = r"d( \d+)?"
decrement_regex = r"dd( \d+)?"
add_game_regex = r"deathcount add game ([\w\W A-Z]+)"
remove_game_regex = r"deathcount remove game ([\w\W A-Z]+)"
set_game_regex = r"deathcount set game ([\w\W A-Z]+)"
set_nickname_regex = r"deathcount set nickname (\w+)"


# Module Registration-----------------------------------------------------------
module_tools.register_command_module()
logger = spicytwitch.log_tools.create_logger()
storage_directory = module_tools.get_storage_directory()


# Database----------------------------------------------------------------------
connection = sqlite3.connect(os.path.join(storage_directory, __name__))
cursor = connection.cursor()

# Setup database on startup
# Setting up nickname table
# NOTE: This is not affected by channels as it is capitalized
cursor.execute(
    "CREATE TABLE IF NOT EXISTS nicknames "
    "(nickname TEXT, channel TEXT)"
)

cursor.execute(
    "CREATE TABLE IF NOT EXISTS deathcount "
    "(game TEXT, count INT, isdefault TEXT, channel TEXT)"
)

# Nickname management-----------------------------------------------------------
def db_set_nickname(nickname: str, channel: str):
    # Check if channel already has a nickname
    cursor.execute(
        "SELECT * FROM nicknames "
        "WHERE channel=(?)",
        (channel,)
    )
    data = cursor.fetchall()
    if not data:
        # Create a row for the channel and add their new nickname
        cursor.execute(
            "INSERT INTO nicknames "
            "(nickname, channel) "
            "VALUES (?, ?)",
            (nickname, channel)
        )
    else:
        # Update their nickname
        cursor.execute(
            "UPDATE nicknames "
            "SET nickname=(?) "
            "WHERE channel=(?)",
            (nickname, channel.lower())
        )

    connection.commit()


def db_get_streamer_nickname(channel: str) -> str:
    """Returns channel nickname, if not found it returns the channel's name
    """
    cursor.execute(
        "SELECT nickname FROM nicknames "
        "WHERE channel=?",
        (channel.lower(),)
    )
    data = cursor.fetchall()
    if not data:
        nickname = channel
    else:
        nickname = data[0][0]

    return nickname


# Data management---------------------------------------------------------------
def db_check_for_duplicate(game: str, channel: str) -> bool:
    """Checks if a game is already in the database for a channel
    """
    cursor.execute(
        "SELECT * FROM deathcount "
        "WHERE channel=(?)AND game=(?)",
        (channel.lower(), game.lower())
    )
    data = cursor.fetchall()
    if len(data) > 0:
        return False
    else:
        return True


def db_check_game_exists(game: str, channel: str) -> bool:
    """Wrapper for db_check_for_duplicates, for readability

    Reverses the return of db_check_for_duplicates, True indicates
    that a game exists, False indicates that it does not.
    """
    return not db_check_for_duplicate(game, channel)


def db_get_death_count(game: str, channel: str) -> int:
    """Returns the deathcount for a game in a specific channel.
    """
    cursor.execute(
        "SELECT count FROM deathcount "
        "WHERE channel=(?) AND game=(?)",
        (channel.lower(), game.lower())
    )
    data = cursor.fetchall()
    if not data:
        return -1
    else:
        return data[0][0]


def db_get_game_count(channel: str):
    """Returns the number of games in a channel
    """
    cursor.execute(
        "SELECT game FROM deathcount "
        "WHERE channel=(?)",
        (channel.lower(),)
    )
    data = cursor.fetchall()
    return len(data)


def db_add_game(game: str, channel: str, set_default_game: bool=False) -> bool:
    """Adds a game to the database for a channel, does not allow duplicates
    """
    if not db_check_for_duplicate(game, channel):
        return False
    else:
        if set_default_game:
            default = "YES"
        else:
            default = "NO"

        cursor.execute(
            "INSERT INTO deathcount "
            "(game, count, isdefault, channel) "
            "VALUES (?, ?, ?, ?)",
            (game.lower(), 0, default, channel.lower())
        )
        connection.commit()

        return True
    

def db_remove_game(game: str, channel: str) -> bool:
    """Removes a game from the database, for a specific channel  
    """
    if db_check_game_exists(game, channel):
        cursor.execute(
            "DELETE FROM deathcount "
            "WHERE channel=(?) AND game=(?)",
            (channel.lower(), game.lower())
        )
        connection.commit()
        return True
    else:
        return False


def db_increment_count(game: str, channel: str, amount: int) -> bool:
    """Incremenets the deathcount of a game, for a specific channel
    """

    if db_check_game_exists(game, channel):
        cursor.execute(
            "UPDATE deathcount "
            "SET count=count+(?) "
            "WHERE channel=(?) AND game=(?)",
            (amount, channel.lower(), game.lower())
        )
        connection.commit()
        return True
    else:
        return False


def db_decrement_count(game: str, channel: str, amount: int) -> bool:
    if db_check_game_exists(game, channel):
        count = db_get_death_count(game, channel)
    
        if count - amount < 0:
            cursor.execute(
                "UPDATE deathcount "
                "SET count=(?) "
                "WHERE channel=(?) AND game=(?)",
                (0, channel.lower(), game.lower())
            )
            connection.commit()
            return True
        else:
            cursor.execute(
                "UPDATE deathcount "
                "SET count=count-(?) "
                "WHERE channel=(?) AND game=(?)",
                (amount, channel.lower(), game.lower())
            )
            connection.commit()
            return True
    else:
        return False
            

def db_reset_count(game: str, channel: str) -> bool:
    """Sets the counter to 0 for a game, in a specific channel
    """
    if db_check_game_exists(game, channel):
        cursor.execute(
            "UPDATE deathcount "
            "SET count=(?) "
            "WHERE channel=(?) AND game=(?)",
            (0, channel.lower(), game.lower())
        )
        connection.commit()
        return True
    else:
        return False


def db_get_default_game(channel: str):
    """Returns the default game for a specific channel
    
    The default game is the game that will be used whenever a command
    is called without any game specified.
    """
    cursor.execute(
        "SELECT game FROM deathcount "
        "WHERE channel=(?) AND isdefault=(?)",
        (channel.lower(), "YES")
    )
    data = cursor.fetchall()

    if len(data) == 0:
        return ''
    else:
        return data[0][0]


def db_set_default_game(game: str, channel:str) -> bool:
    """Marks a game as being the default for a specfic channel
    """

    if db_check_game_exists(game, channel):
        # Unset previous default
        cursor.execute(
            "UPDATE deathcount "
            "SET isdefault='NO' "
            "WHERE channel=(?) AND isdefault=(?)",
            (channel.lower(), "YES")
        )
        connection.commit()

        # Set new game to default
        cursor.execute(
            "UPDATE deathcount "
            "SET isdefault=(?) "
            "WHERE channel=(?) AND game=(?)",
            ("YES", channel.lower(), game.lower())
        )
        connection.commit()
        return True
    else:
        return False
    
    
def db_close_connection():
    logger.info(
        "Saving database and closing connection."
    )
    cursor.close()
    connection.close()
    

# Command functions ------------------------------------------------------------
def increment_deaths(user: IRC.User):

    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = re.findall(increment_regex, user_input)

    if parsed_input[0]:
        try:
            increment_by = int(parsed_input[0].strip())
        except ValueError:
            # I doubt this will ever launch, but I'd prefer not to have the bot
            # crash.
            logger.warning(
                "Failed to convert user's input into an integer! "
                "User input: {}".format(user.message)
            )
            return
    else:
        increment_by = 1

    game = db_get_default_game(user.chatted_from)

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod"
            "can set the game by using '!deathcount set game <game>'"
        )
        return


    if not db_increment_count(game, user.chatted_from, increment_by):
        user.send_message(
            "The game you've given is not in the list of games!"
        )
    else:
        logger.info(
            "{} has Incremented death count by {}, for the game {}, in the channel "
            "{}.".format(user.name, increment_by, game, user.chatted_from)
        )

        user.send_message(
            "Death count has been incremented by {}, for the "
            "game '{}'. RIP sfhSAD".format(increment_by, game)
        )
    
def decrement_deaths(user: IRC.User):
    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = re.findall(decrement_regex, user_input)

    if parsed_input[0]:
        try:
            decrement_by = int(parsed_input[0].strip())
        except ValueError:
            # I doubt this will ever launch, but I'd prefer not to have the bot
            # crash.
            logger.warning(
                "Failed to convert user's input into an integer! "
                "User input: {}".format(user.message)
            )
            return
    else:
        decrement_by = 1

    game = db_get_default_game(user.chatted_from)

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod"
            "can set the game by using '!deathcount set game <game>'"
        )


    if not db_decrement_count(game, user.chatted_from, decrement_by):
        user.send_message(
            "The game you've given is not in the list of games!"
        )
    else:
        logger.info(
            "{} has decremented the death count for the game '{}' by {} in the channel "
            "'{}'.".format(user.name, game, decrement_by, user.chatted_from)
        )

        user.send_message(
            "Death count has been decremented by {} for the game '{}'. "
            "sfhOH".format(decrement_by, game)
        )

def reset_deaths(user: IRC.User):
    game = db_get_default_game(user.chatted_from)

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod "
            "can set the game by using '!deathcount set game <game>'"
        )


    if not db_reset_count(game, user.chatted_from):
        user.send_message(
            "The game currently set is not in the database. This should not "
            "have happened... OhGod"
        )
    else:
        logger.info("Reset death count for game '{}' in channel {}.".format(
            game, user.chatted_from)
        )
        
        user.send_message(
            "Deaths have been reset to zero for the game '{}'. "
            "sfhWOW".format(game)
        )


def death_count(user: IRC.User):
    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = re.findall(deathcount_regex, user_input)[0]

    if parsed_input:
        game = parsed_input.strip().lower()
    else:
        game = db_get_default_game(user.chatted_from)

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod "
            "can set the game by using '!deathcount set game <game>'"
        )
        return

    
    deaths = db_get_death_count(game, user.chatted_from)

    streamer = db_get_streamer_nickname(user.chatted_from)

    if deaths > 1:
        user.send_message(
            "{} has died {} times. RIP sfhSAD".format(streamer, deaths)
        )
    elif deaths == 1:
        user.send_message("{} has died 1 time. RIP sfhSAD".format(streamer))
    elif deaths == 0:
        user.send_message("{} has yet to die! sfhOH".format(streamer))
    else:
        user.send_message("{} is not in the list of games.".format(game))
        return

    logger.info(
        "Read death count of {} for the game {}, in the channel "
        "{}.".format(
            deaths, game, user.chatted_from, user.name
        )
    )

    
def add_game(user: IRC.User):
    game = re.findall(add_game_regex, user.message)[0]

    if not db_add_game(game, user.chatted_from):
        user.send_message("'{}' is already in the list of games.".format(game))
    else:
        logger.info(
            "{} has added the game '{}' to the channel '{}'".format(
                user.name, game, user.chatted_from
            )
        )
        user.send_message("'{}' is now in the list of games! sfhOH".format(game))


def set_game(user: IRC.User):
    game = re.findall(set_game_regex, user.message)[0]

    if db_set_default_game(game, user.chatted_from):
        logger.info(
            "Default game for channel '{}' has be set to '{}' by {}".format(
                user.chatted_from, game, user.name
            )
        )
        user.send_message("Game has been changed to {}. sfhOH".format(game))
    else:
        user.send_message(
            "{} is not in the list of games. If you'd like to add it to the "
            "list of games (and are a moderator), run '{}deathcount add game {}'."
            "".format(game, module_tools.DEFAULT_COMMAND_PREFIX, game)
        )


def remove_game(user: IRC.User):
    game = re.findall(remove_game_regex, user.message)[0]

    if db_remove_game(game, user.chatted_from):
        logger.info(
            "{} has removed the game '{}' from the channel '{}'".format(
                user.name, game, user.chatted_from
            )
        )
        user.send_message(
            "{} has been removed from the list of games! "
            "RIP".format(game)
        )

    else:
        user.send_message("{} is not in the list of games.".format(game))


def set_nickname(user: IRC.User):
    nickname = re.findall(set_nickname_regex, user.message)[0]

    db_set_nickname(nickname, user.chatted_from)
    logger.info(
        "{} has set the nickname for channel '{}' to '{}'".format(
            user.name, user.chatted_from, nickname
        )
    )
    user.send_message("Nickname has been set to '{}'".format(nickname))


# Registering Commands----------------------------------------------------------
module_tools.register_command(increment_regex, increment_deaths, "moderator", mod_cooldown=15)
module_tools.register_command(decrement_regex, decrement_deaths, "moderator", mod_cooldown=15)
module_tools.register_command(deathcount_regex, death_count)
module_tools.register_command("deathcount reset", reset_deaths, "broadcaster")
module_tools.register_command(remove_game_regex, remove_game,"moderator")
module_tools.register_command(add_game_regex, add_game, "moderator", mod_cooldown=15)
module_tools.register_command(set_game_regex, set_game,  "moderator")
module_tools.register_command(set_nickname_regex, set_nickname, "moderator")

# Reserving command names
module_tools.reserve_general_commands(RESERVED_COMMAND_NAMES)

# Registering shutdown functions
module_tools.register_shutdown_function(db_close_connection)

