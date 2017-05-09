"""
This module will manage two main parts of the system.

First:
It will manage configuration of every other command module

Second:
It will manage local commands, simple response commands
that are common in just about every bot.
"""
# TODO: I just realized something pretty terrible... Registering commands with
#       the create_command() function will make the command available on every
#       channel this bot is on... So really, I can't do it this way. Instead I
#       should use the data from module_tools

# Imports---------------------------------------------------------------------
import re
import spicytwitch


# Global Variables------------------------------------------------------------
IRC = spicytwitch.irc
module_tools = spicytwitch.bot.modules
RESERVED_COMMAND_NAMES = [
    "commands"
]

# Regex-----------------------------------------------------------------------
# TODO: I believe I need to do a check at the start of each regex.
#       I'll check for a character as that's what'll be used to denote a call.
add_regex = r"commands add( --\w+=\w+)* {}(\w+) (.+)".format(
    module_tools.DEFAULT_COMMAND_PREFIX
)
edit_regex = r"commands edit (--\w+=\w+)? {}(\w+) (.+)".format(
    module_tools.DEFAULT_COMMAND_PREFIX
)
delete_regex = r"commands (delete|remove) {}(\w+)".format(
    module_tools.DEFAULT_COMMAND_PREFIX
)
rename_regex = r"commands rename {prefix}(\w+) {prefix}(\w+)".format(
    prefix=module_tools.DEFAULT_COMMAND_PREFIX
)

# Module Registration-----------------------------------------------------------
spicytwitch.bot.modules.register_command_module()
logger = spicytwitch.log_tools.create_logger()


# Database setup----------------------------------------------------------------
# TODO: Setup storage location in Bot.modules
storage_location = module_tools.get_storage_directory()
database = spicytwitch.bot.modules.GeneralCommandDatabase(
    __name__, storage_location
)

def _close_database():
    database.close()
   

# Command Functions-------------------------------------------------------------
def commands_add(user: IRC.User):
    parsed_input = re.findall(add_regex, user.message)[0]
    print('Parsed: {}'.format(parsed_input))

    options = {}
    if len(parsed_input) >= 3:
        print(parsed_input[:-2])
        for option in parsed_input[:-2]:
            option_value = option.split('=', 1)

            if len(option_value) < 2:
                continue

            options[option[0].split('-', 2)[-1].lower()] = option_value[1]
    
    print(parsed_input)

    command_name = parsed_input[-2]
    command_response = parsed_input[-1]

    if module_tools.check_if_command_exists(command_name, ignore_casing=True):
        user.send_message("The name '{}' is already in use.".format(command_name))
    else:
        if 'userlevel' in options.keys():
            level = options['userlevel']
            if level.lower() not in module_tools.USER_LEVELS:
                level = 'everyone'
            print(level)
        else:
            level = 'everyone'

        if "cooldown" in options.keys():
            cooldown = options['cooldown']
        else:
            cooldown = 30

        if not database.add_command(
            command_name, command_response, cooldown, level, user.chatted_from
        ):
            user.send_message("The name '{}' is already in use".format(command_name))
        else:
            user.send_message("Command '{}' has been created PogChamp".format(command_name))


# Registering commands----------------------------------------------------------
module_tools.register_command(add_regex, commands_add, "moderator", mod_cooldown=3)
module_tools.reserve_general_commands(RESERVED_COMMAND_NAMES)
module_tools.register_shutdown_function(_close_database)


# Outer interface---------------------------------------------------------------
# NOTE: I should update the GeneralCommandModule to allow for editing.
def manage_general_commands(user: IRC.User) -> bool:
    try:
        command_name = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    except IndexError:
        logger.info("Was not a command")
        return False

    database.initialize_channel(user.chatted_from)
    response =  database.get_response(command_name, user.chatted_from)
    if not response:
        logger.info("Was not a command in the general database")
        return False

    user_level = database.get_user_level(command_name, user.chatted_from)
    if not module_tools.default_check_user_level(user_level, user):
        logger.info("Userlevel did not check out")
        return False

    if not database.check_cooldown(command_name, user.chatted_from):
        logger.info("Cooldown did not check out")
        return False

    IRC.chat(response, user.chatted_from)
    database.mark_cooldown(command_name, user.chatted_from)
    logger.info("Sent command '{}' to channel '{}'".format(command_name, user.chatted_from))
    return True

   
