# Imports-----------------------------------------------------------------------
import re
import datetime
from random import choice
import spicytwitch

# Global Variables--------------------------------------------------------------
# Decided to use a local variable for storage instead of the module_tools
# storage system since I don't intend to have any of this data saved. The one
# downside is that now I have to manage channels myself.
sacrifices = {}
today = None

module_tools = spicytwitch.bot.modules
IRC = spicytwitch.irc

reserved_commands = [
    "sacrifice"
]

# Regex-------------------------------------------------------------------------
main_regex = r"sacrifice( subs| mods)?"
reset_regex = r"sacrifice reset"


# Module Registration-----------------------------------------------------------
module_tools.register_command_module()

# Getting a logger
logger = spicytwitch.log_tools.create_logger()


# Ease of use-------------------------------------------------------------------
def check_channel(channel: str):
    global sacrifices

    if channel not in sacrifices.keys():
        sacrifices[channel] = {'subs': [], 'mods': [], 'everyone_else': []}

# TODO: Implement this in code!
def check_day(channel: str):
    global today
    global sacrifices
    
    current_date = datetime.datetime.today()
    if today is not current_date:
        del sacrifices[channel]  # Remove the channel from the sacrifices dict.
        check_channel(channel)  # Add back the channel.

        today = current_date
    
def is_in_sacrifices(username: str, channel: str):
    sacrifice_list = sacrifices[channel]
    username = username.lower()

    if username in sacrifice_list['subs']:
        return True
    elif username in sacrifice_list['mods']:
        return True
    elif username in sacrifice_list['everyone_else']:
        return True
    else:
        return False

# Command functions-------------------------------------------------------------
def sacrifice_me(user: IRC.User):
    check_channel(user.chatted_from)

    global sacrifices

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']

    if is_in_sacrifices(user.name, user.chatted_from):
        return

    if user.is_mod:
        logger.info("Adding '{}' to mods sacrifice list for channel '{}'.".format(
                user.name, user.chatted_from
            )
        )
        sacrifices[user.chatted_from]['mods'].append(user.name.lower())
    elif user.is_sub:
        logger.info("Adding '{}' to sub sacrifice list for channel '{}'.".format(
                user.name, user.chatted_from
            )
        )
        sacrifices[user.chatted_from]['subs'].append(user.name.lower())
    else:
        logger.info("Adding '{}' to everyone_else sacrifice list for channel '{}'.".format(
                user.name, user.chatted_from
            )
        )
        sacrifices[user.chatted_from]['everyone_else'].append(user.name.lower())


def sacrifice_count(user: IRC.User):
    check_channel(user.chatted_from)

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']
    everyone = sacrifices[user.chatted_from]['everyone_else'] + subs + mods

    count = len(everyone)
    if count <= 0:  # Should never be less than Zero, but I'd rather be safe.
        user.send_message("Nobody has offered themselves as a sacrifice.")
    elif count == 1:
        IRC.chat("There is 1 soon-to-be sacrifice!", user.chatted_from)
    else:
        IRC.chat(
            "There are {} soon-to-be sacrifices!".format(count),user.chatted_from
        )

    logger.info("Read sacrifice count of {} for channel '{}'".format(
            count, user.chatted_from
        )
    )


def sacrifice_reset(user: IRC.User):
    check_channel(user.chatted_from)

    sacrifices[user.chatted_from] = {
        'subs': [], 'mods': [], 'everyone_else': []
    }

    user.send_message("List of sacrifices has been cleared.")
    logger.info("Sacrifice list has been cleared by '{}' in channel '{}'".format(
            user.name, user.chatted_from
        )
    )


def sacrifice(user: IRC.User):
    check_channel(user.chatted_from)

    parsed_input = re.findall(main_regex, user.message)[0]

    if parsed_input:
        option = parsed_input.lower().strip()
    else:
        option = ''

    print(option)

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']
    everyone = sacrifices[user.chatted_from]['everyone_else'] + subs + mods

    todays_sacrifice = ''
    if option:
        if option == 'subs':
            if subs:
                todays_sacrifice = choice(subs)
                user.send_message(
                    "Subscriber sacrifice is @{}".format(todays_sacrifice)
                )
            else:
                user.send_message(
                    "No subscribers have offered themselves as a sacrifice."
                )
        elif option == 'mods':
            if subs:
                todays_sacrifice = choice(mods)
                user.send_message(
                    "Moderator sacrifice is @{}".format(todays_sacrifice)
                )
            else:
                user.send_message(
                    "No moderators have offered themselves as a sacrifice."
                )
    else:
        if everyone:
            todays_sacrifice = choice(everyone)
            user.send_message(
                "Today's sacrifice is @{}".format(todays_sacrifice)
            )
        else:
            user.send_message(
                "Nobody has offered themselves as a sacrifice."
            )

    if todays_sacrifice:
        logger.info("Sacrificed user '{}' in channel '{}'".format(
                todays_sacrifice, user.chatted_from
            )
        )

# Registering Commands----------------------------------------------------------
module_tools.register_command(main_regex, sacrifice, "moderator", mod_cooldown=5)
module_tools.register_command(reset_regex, sacrifice_reset, "moderator")
module_tools.register_command("sacrifices", sacrifice_count)
module_tools.register_command(
    "sacrificeme", sacrifice_me, everyone_cooldown=0, mod_cooldown=0
)

module_tools.reserve_general_commands(reserved_commands)
