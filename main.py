# Imports-----------------------------------------------------------------------
import sys
import os
from time import sleep
import spicytwitch
import spicybot_modules

# Global Variables--------------------------------------------------------------
VERSION = "0.2.0"
CODENAME = "Gypsy Pepper"
CONFIG = {}

admin = ''  # NOTE: This is later set in the config file!
shutdown = "{}shutdown".format(spicytwitch.bot.modules.DEFAULT_COMMAND_PREFIX)
entrance_message = "sfhSORA This chat needs some extra spices! Good thing I'm here now. sfhSORA"
shutdown_message = (
    "Fuck, the dev's killing me off now. I only wanted to spice up chat FeelsBadMan "
    "(Bot is shutting down)"
)

logger = spicytwitch.log_tools.create_logger()

# Other functions---------------------------------------------------------------
def cleanup():
    for channel in spicytwitch.irc.channels.keys():
        spicytwitch.irc.chat(shutdown_message, channel)

    spicytwitch.irc.disconnect()
    spicytwitch.bot.run_cleanup()


# The Bot-----------------------------------------------------------------------
# NOTE: Make sure the config file has strict restrictions!


# Loading config
config_file = os.path.join(
    os.path.expanduser('~'), '.spicyconfig'
)

logger.info("Loading spicyconfig file.")
with open(config_file, 'r') as config:
    for index, line in enumerate(config.readlines()):
        try:
            CONFIG[line.split('=', 1)[0]] = line.split('=', 1)[1].strip()
        except IndexError:
            logger.warning("Failed to read configuration line #{}.".format(index))


if "username" not in CONFIG or "oauth" not in CONFIG:
    logger.warning("Username or oauth missing from config file.")
    sys.exit(1)

# Logging into twitch
logger.info("Logging into twitch as '{}'.".format(CONFIG["username"]))
if not spicytwitch.irc.connect(CONFIG["username"], CONFIG["oauth"], "tcp"):
    logger.warning(
        "Failed ot log into twitch. Please double check oauth or username"
    )
    sys.exit(1)


if len(sys.argv) > 1:
    join_these = sys.argv[1:]
else:
    join_these = CONFIG["channels"].split(',')

if not join_these:
    logger.info("Not given any channels to join, aborting")
    sys.exit()

# Joining channels
for channel in join_these:
    if channel:
        channel = channel.strip()
        logger.info("{} is now entering the channel '{}'".format(
                CONFIG["username"], channel
            )
        )
        spicytwitch.irc.join_channel(channel)
        spicytwitch.irc.chat(entrance_message, channel)
    
# Listning to chat
logger.info("{} will now begin monitoring chat.".format(CONFIG["username"]))   
admin = CONFIG["admin"]
while True:
    try:
        logger.debug("Requesting data from twitch")
        if spicytwitch.irc.get_info():
            logger.debug("Recieved data, checking if it is a chat line")
            if spicytwitch.irc.user:
                logger.debug("Message was a chat line")
                user = spicytwitch.irc.user
                if user.command.lower() == shutdown and user.name.lower() == admin:
                    logger.info("Received shutdown command from admin.")
                    break
                else:
                    logger.debug("Data will be passed to bot manager")
                    spicytwitch.bot.manage_all_modules(user)
    except KeyboardInterrupt:
        break


logger.info("Running cleanup")
cleanup()
logger.info("Goodbye! Have a nice day :)")

