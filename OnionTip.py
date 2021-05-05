#!/usr/bin/python3
# coding=utf-8


from datetime import datetime
import time
import emoji
from telegram.ext import CommandHandler, CallbackQueryHandler, Updater, CallbackContext, MessageHandler, Filters, filters
from telegram.utils.helpers import escape_markdown
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from DeepOnionRPC import DeepOnionRPC, Wrapper as RPCWrapper
from HelperFunctions import *
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )


config = load_file_json("config.json")
_lang = "en"  # ToDo: Per-user language
strings = Strings("strings.json")
_paused = False
_spam_filter = AntiSpamFilter(
    config["spam_filter"][0], config["spam_filter"][1])

_rain_queues = {
	"-1": [("0", "@username", "Name")]
}


# Constants
__wallet_rpc = RPCWrapper(DeepOnionRPC(
    config["rpc-uri"], (config["rpc-user"], config["rpc-psw"])))
__fee_std = 0.00010
__units = {
    "parent_name": "ONION",
    "parent_format": "%.4f",
    "name": "mONION",
    "symbol": "mONION",
    "multiplier": 1,
    "multiplier_threshold": 0.01
}
# If True, use getbalance <account>, else use getbalance <address>
__rpc_getbalance_account = True
# If False, use sendmany <source_account> {"address": amount}, else {"account": amount}
__rpc_sendmany_account = False
__blockchain_explorer_tx = "https://explorer.deeponion.org/tx/"
# See issue #4 (https://github.com/DarthJahus/oniontip-Telegram/issues/4)
__minconf = 0

__rain_queue_filter = Filters.chat_type.groups & (
    Filters.text | Filters.photo | Filters.video | Filters.reply | Filters.forwarded
)

#__rain_queue_filter = Filters.chat_type.private
__rain_queue_min_text_length = 10  # 10
__rain_queue_min_words = 2  # 2
__rain_queue_max_members = 30  # Max members in a queue, 30
__rain_min_members = 3  # 5
__rain_min_amount = 0.001  # 10


def echo(update: Update, context: CallbackContext) -> None:
    if(update.message.text == emoji.emojize(strings.get("button_balance", _lang), use_aliases=True)):
        balance(update, context)
    elif(update.message.text == emoji.emojize(strings.get("button_deposit", _lang), use_aliases=True)):
        deposit(update, context)
    elif(update.message.text == emoji.emojize(strings.get("button_withdraw", _lang), use_aliases=True)):
        update.message.reply_text("Use `/withdraw <address> <amount>`", quote=True, parse_mode=ParseMode.MARKDOWN)
    elif(update.message.text == emoji.emojize(strings.get("button_send", _lang), use_aliases=True)):
        tip(update, context)
    elif(update.message.text == emoji.emojize(strings.get("button_help", _lang), use_aliases=True)):
        cmd_help(update, context)
    elif(update.message.text == emoji.emojize(strings.get("button_about", _lang), use_aliases=True)):
        cmd_about(update, context)
    if(update.message.text == emoji.emojize(strings.get("button_exchanges", _lang), use_aliases=True)):
        exchanges(update, context)
    if(update.message.text == emoji.emojize(strings.get("button_features", _lang), use_aliases=True)):
        features(update, context)
    if(update.message.text == emoji.emojize(strings.get("button_roadmap", _lang), use_aliases=True)):
        roadmap(update, context)


def cmd_start_keyboard(update: Update, context: CallbackContext):
    _button_balance = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_balance", _lang), use_aliases=True),
        callback_data="balance"
    )
    _button_deposit = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_deposit", _lang), use_aliases=True),
        callback_data="deposit"
    )

    _button_withdraw = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_withdraw", _lang), use_aliases=True),
        callback_data="withdraw"
    )

    _button_send = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_send", _lang), use_aliases=True),
        callback_data="tip"
    )

    _button_help = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_help", _lang), use_aliases=True),
        callback_data="help"
    )
    _button_about = KeyboardButton(
        text=emoji.emojize(strings.get(
            "button_about", _lang), use_aliases=True),
        callback_data="about"
    )
    _markup = ReplyKeyboardMarkup(
        [
            [_button_balance, _button_deposit, _button_withdraw],
            [_button_send, _button_help, _button_about]
        ],
        resize_keyboard=True
    )
    update.message.reply_text(
        text="",
        quote=True,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=_markup
    )


# ToDo: Don't forget to write the strings in strings.json (they are actually empty)
def cmd_start(update: Update, context: CallbackContext):
    """Reacts when /start is sent to the bot."""
    if update.effective_chat.type == "private":
        if not _spam_filter.verify(str(update.effective_user.id)):
            return
        # Check for deep link
        if len(context.args) > 0:
            if context.args[0].lower() == "about":
                cmd_about(update, context)
            elif context.args[0].lower() == "help":
                cmd_help(update, context)
            elif context.args[0].lower() == "address":
                deposit(update, context)
            elif context.args[0].lower() == "balance":
                balance(update, context)
            elif context.args[0].lower() == "deposit":
                deposit(update, context)
            elif context.args[0].lower() == "withdraw":
                withdraw(update, context)
            elif context.args[0].lower() == "exchanges":
                exchanges(update, context)
            elif context.args[0].lower() == "features":
                features(update, context)
            elif context.args[0].lower() == "roadmap":
                roadmap(update, context)

            else:
                update.message.reply_text(
                    strings.get("error_bad_deep_link", _lang),
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
        else:
            _button_balance = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_balance", _lang), use_aliases=True),
                callback_data="balance"
            )
            _button_deposit = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_deposit", _lang), use_aliases=True),
                callback_data="deposit"
            )

            _button_withdraw = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_withdraw", _lang), use_aliases=True),
                callback_data="withdraw"
            )

            _button_send = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_send", _lang), use_aliases=True),
                callback_data="tip"
            )

            _button_help = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_help", _lang), use_aliases=True),
                callback_data="help"
            )
            _button_about = KeyboardButton(
                text=emoji.emojize(strings.get(
                    "button_about", _lang), use_aliases=True),
                callback_data="about"
            )
            _markup = ReplyKeyboardMarkup(
                [
                    [_button_balance, _button_deposit, _button_withdraw],
                    [_button_send, _button_help, _button_about]
                ],
                resize_keyboard=True
            )
            update.message.reply_text(
                emoji.emojize(strings.get("welcome", _lang), use_aliases=True),
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=_markup
            )


def cmd_about(update: Update, context: CallbackContext):
    if not _spam_filter.verify(str(update.effective_user.id)):
        return
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"
    #
    bot = context.bot
    if _chat_type == "private":
        # Check if callback
        try:
            if update.callback_query.data is not None:
                update.callback_query.answer(
                    strings.get("callback_simple", _lang))
        except:
            pass
        # Answer
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_help", _lang), use_aliases=True),
            callback_data="help"
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        bot.send_message(
            chat_id=update.effective_chat.id,
            text=strings.get("about", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )
    else:
        # Done: Button (2018-07-18)
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_about", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=about" % context.bot.username
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        update.message.reply_text(
            "%s" % strings.get("about_public", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )
    return True


def cmd_help(update: Update, context: CallbackContext):
    if not _spam_filter.verify(str(update.effective_user.id)):
        return
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"
    #
    bot = context.bot
    if _chat_type == "private":
        # Check if callback
        try:
            if update.callback_query.data is not None:
                update.callback_query.answer(
                    strings.get("callback_simple", _lang))
        except:
            pass
        # Answer
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_help_advanced_caption", _lang), use_aliases=True),
            url=strings.get("button_help_advanced_url", _lang)
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        bot.send_message(
            chat_id=update.effective_chat.id,
            text=emoji.emojize(strings.get("help", _lang), use_aliases=True),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_markup,
            disable_web_page_preview=True
        )
    else:
        # Done: Button (2018-07-18)
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_help", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=help" % context.bot.username
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        update.message.reply_text(
            "%s" % strings.get("help_public", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )
    return True


def msg_no_account(update: Update, context: CallbackContext):
    bot = context.bot
    _button = InlineKeyboardButton(
        text=emoji.emojize(strings.get(
            "user_no_address_button", _lang), use_aliases=True),
        url="https://telegram.me/%s?start=address" % bot.username
    )
    _markup = InlineKeyboardMarkup(
        [[_button]]
    )
    update.message.reply_text(
        "%s" % strings.get("user_no_address", _lang),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=_markup
    )


def deposit(update: Update, context: CallbackContext):
    """
    This commands works only in private.
    If the user has no address, a new account is created with his Telegram user ID (str)
    """
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"

    # Only show deposit address if it's a private conversation with the bot
    if _chat_type == "private":
        if not _spam_filter.verify(str(update.effective_user.id)):
            return  # ToDo: Return a message?
        if _paused:
            update.message.reply_text(text=emoji.emojize(
                strings.get("global_paused"), use_aliases=True), quote=True)
            return
        _username = update.effective_user.username
        if _username is None:
            _user_id = str(update.effective_user.id)
        else:
            _user_id = '@' + _username.lower()
        _address = None
        _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
        if not _rpc_call["success"]:
            print("Error during RPC call.")
            log("deposit", _user_id, "getaddressesbyaccount > Error during RPC call.")
        else:
            if _rpc_call["result"]["error"] is not None:
                print("Error: %s" % _rpc_call["result"]["error"])
                log("deposit", _user_id, "getaddressesbyaccount > Error: %s" %
                    _rpc_call["result"]["error"])
            else:
                # Check if user already has an address. This will prevent creating another address if user has one
                _addresses = _rpc_call["result"]["result"]
                if len(_addresses) == 0:
                    # Done: User has no address, request a new one (2018-07-16)
                    _rpc_call = __wallet_rpc.getaccountaddress(_user_id)
                    if not _rpc_call["success"]:
                        print("Error during RPC call.")
                        log("deposit", _user_id,
                            "getaccountaddress > Error during RPC call.")
                    else:
                        if _rpc_call["result"]["error"] is not None:
                            print("Error: %s" % _rpc_call["result"]["error"])
                            log("deposit", _user_id, "getaccountaddress > Error: %s" %
                                _rpc_call["result"]["error"])
                        else:
                            _address = _rpc_call["result"]["result"]
                else:
                    _address = _addresses[0]
                # ToDo: Can it happen that a user gets more than juan address? Verify.
                if _address is not None:
                    update.message.reply_text(
                        text="%s `%s`" % (strings.get(
                            "user_address", _lang), _address),
                        quote=True,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
    else:
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_deposit", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=deposit" % context.bot.username,
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        update.message.reply_text(
            "%s" % strings.get("user_balance_public", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )

# Done: Give balance only if a private chat (2018-07-15)
# Done: Remove WorldCoinIndex (2018-07-15)
# ToDo: Add conversion


def balance(update: Update, context: CallbackContext):
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"

    # Only show balance if it's a private conversation with the bot
    if _chat_type == "private":
        if not _spam_filter.verify(str(update.effective_user.id)):
            return  # ToDo: Return a message?
        if _paused:
            update.message.reply_text(text=emoji.emojize(
                strings.get("global_paused"), use_aliases=True), quote=True)
            return
        # See issue #2 (https://github.com/DarthJahus/PandaTip-Telegram/issues/2)
        _username = update.effective_user.username
        if _username is None:
            _user_id = str(update.effective_user.id)
        else:
            _user_id = '@' + _username.lower()
        # get address of user
        _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
        if not _rpc_call["success"]:
            print("Error during RPC call: %s" % _rpc_call["message"])
            log("balance", _user_id, "(1) getaddressesbyaccount > Error during RPC call: %s" %
                _rpc_call["message"])
        elif _rpc_call["result"]["error"] is not None:
            print("Error: %s" % _rpc_call["result"]["error"])
            log("balance", _user_id, "(1) getaddressesbyaccount > Error: %s" %
                _rpc_call["result"]["error"])
        else:
            _addresses = _rpc_call["result"]["result"]
            if len(_addresses) == 0:
                # User has no address, ask him to create one
                msg_no_account(update, context)
            else:
                # ToDo: Handle the case when user has many addresses?
                # Maybe if something really weird happens and user ends up having more, we can calculate his balance.
                # This way, when asking for address (/deposit), we can return the first one.
                _address = _addresses[0]
                if __rpc_getbalance_account:
                    _rpc_call = __wallet_rpc.getbalance(_user_id, __minconf)
                else:
                    _rpc_call = __wallet_rpc.getbalance(_address, __minconf)
                if not _rpc_call["success"]:
                    print("Error during RPC call.")
                    log("balance", _user_id, "(2) getbalance > Error during RPC call: %s" %
                        _rpc_call["message"])
                elif _rpc_call["result"]["error"] is not None:
                    print("Error: %s" % _rpc_call["result"]["error"])
                    log("balance", _user_id, "(2) getbalance > Error: %s" %
                        _rpc_call["result"]["error"])
                else:
                    _balance = float(_rpc_call["result"]["result"])
                    update.message.reply_text(
                        text="%s\n`%s`" % (strings.get(
                            "user_balance", _lang), convert_satoshi(_balance)),
                        parse_mode=ParseMode.MARKDOWN,
                        quote=True
                    )
    else:
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_balance", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=balance" % context.bot.username,
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        update.message.reply_text(
            "%s" % strings.get("user_balance_public", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )


# Done: Rewrite the whole logic; use tags instead of parsing usernames (2018-07-15)
# Done: Allow private tipping if the user can be tagged (@username available) (Nothing to add for it to work.)
def tip(update: Update, context: CallbackContext):
    """
    /tip <user> <amount>
    /tip u1 u2 u3 ... v1 v2 v3 ...
    /tip u1 v1 u2 v2 u3 v3 ...
    """
    if context.args == None:
        update.message.reply_text(
            text="Use `/tip <user> <amount>`. Make sure to correctly tag the person you are tipping.",
            quote=True,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if len(context.args) == 0:
        return
    if not _spam_filter.verify(str(update.effective_user.id)):
        return  # ToDo: Return a message?
    if _paused:
        update.message.reply_text(text=emoji.emojize(
            strings.get("global_paused"), use_aliases=True), quote=True)
        return
    # Get recipients and values
    _message = update.effective_message.text
    _modifier = 0
    _handled = {}
    _recipients = []
    for entity in update.effective_message.entities:
        if entity.type == "text_mention":
            # UserId is unique
            _username = entity.user.name
            if str(entity.user.id) not in _handled:
                _handled[str(entity.user.id)] = (
                    _username, entity.offset, entity.length)
                _recipients.append(str(entity.user.id))
        elif entity.type == "mention":
            # _username starts with @
            # _username is unique
            _username = update.effective_message.text[entity.offset:(
                entity.offset+entity.length)].lower()
            if _username not in _handled:
                _handled[_username] = (_username, entity.offset, entity.length)
                _recipients.append(_username)
        _part = _message[:entity.offset-_modifier]
        _message = _message[:entity.offset-_modifier] + \
            _message[entity.offset+entity.length-_modifier:]
        _modifier = entity.offset+entity.length-len(_part)
    print("_handled = %s" % _handled)
    print("_recipients = %s" % _recipients)
    _amounts = _message.split()
    # check if amounts are all convertible to float
    _amounts_float = []
    try:
        for _amount in _amounts:
            _adjusted_amount = float(_amount)
            if(_adjusted_amount < __fee_std):
                update.message.reply_text(
                    text=emoji.emojize(strings.get("tip_too_small", _lang),
                                       use_aliases=True),
                    quote=True,
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            _amounts_float.append(_adjusted_amount)
    except:
        _amounts_float = []
    # Make sure number of recipients is the same as number of values
    # old: if len(_amounts_float) != len(_recipients) or len(_amounts_float) == 0 or len(_recipients) == 0:
    # new: ((len(_amounts_float) == len(_recipients)) or (len(_amounts_float) == 1)) and (len(_recipients) > 0),
    # use opposite
    if ((len(_amounts_float) != len(_recipients)) and (len(_amounts_float) != 1)) or (len(_recipients) == 0):
        update.message.reply_text(
            text=strings.get("tip_error_arguments", _lang),
            quote=True,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        #
        # Check if only 1 amount is given
        if len(_amounts_float) == 1 and len(_recipients) > 1:
            _amounts_float = _amounts_float * len(_recipients)
        # Check if user has enough balance
        _username = update.effective_user.username
        if _username is None:
            _user_id = str(update.effective_user.id)
        else:
            _user_id = '@' + _username.lower()
        # get address of user
        _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
        if not _rpc_call["success"]:
            print("Error during RPC call: %s" % _rpc_call["message"])
            log("tip", _user_id, "(1) getaddressesbyaccount > Error during RPC call: %s" %
                _rpc_call["message"])
        elif _rpc_call["result"]["error"] is not None:
            print("Error: %s" % _rpc_call["result"]["error"])
            log("tip", _user_id, "(1) getaddressesbyaccount > Error: %s" %
                _rpc_call["result"]["error"])
        else:
            _addresses = _rpc_call["result"]["result"]
            if len(_addresses) == 0:
                # User has no address, ask him to create one
                msg_no_account(update, context)
            else:
                _address = _addresses[0]
                # Get user's balance
                if __rpc_getbalance_account:
                    _rpc_call = __wallet_rpc.getbalance(_user_id, __minconf)
                else:
                    _rpc_call = __wallet_rpc.getbalance(_address, __minconf)
                if not _rpc_call["success"]:
                    print("Error during RPC call.")
                    log("tip", _user_id, "(2) getbalance > Error during RPC call: %s" %
                        _rpc_call["message"])
                elif _rpc_call["result"]["error"] is not None:
                    print("Error: %s" % _rpc_call["result"]["error"])
                    log("tip", _user_id, "(2) getbalance > Error: %s" %
                        _rpc_call["result"]["error"])
                else:
                    _balance = float(_rpc_call["result"]["result"])
                    # Now, finally, check if user has enough funds (includes tx fee)
                    if sum(_amounts_float) > _balance - max(1*__fee_std, float(len(_recipients)/3)*__fee_std):
                        update.message.reply_text(
                            text="%s `%s`" % (
                                strings.get("tip_no_funds", _lang),
                                (sum(_amounts_float) + max(1*__fee_std,
                                                           float(len(_recipients)/3)*__fee_std))
                            ),
                            quote=True,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        # Now create the {recipient_id: amount} dictionary
                        i = 0
                        _tip_dict_addresses = {}
                        _tip_dict_accounts = {}
                        for _recipient in _recipients:
                            # add "or _recipient == bot.id" to disallow tipping the tip bot
                            if _recipient == _user_id:
                                update.message.reply_text(
                                    text="There is no point in tipping yourself",
                                    quote=True,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                                i += 1
                                continue
                            if _recipient[0] == '@':
                                # ToDo: Get the id (actually not possible (Bot API 3.6, Feb. 2018)
                                # Using the @username
                                # Done: When requesting a new address, if user has a @username, then use that username (2018-07-16)
                                # Problem: If someone has no username, then later creates one, he loses access to his account
                                # Done: Create a /scavenge command that allows people who had UserID to migrate to UserName (2018-07-16)
                                _recipient_id = _recipient
                            else:
                                _recipient_id = _recipient
                            # Check if recipient has an address (required for .sendmany()
                            _rpc_call = __wallet_rpc.getaddressesbyaccount(
                                _recipient_id)
                            if not _rpc_call["success"]:
                                print("Error during RPC call.")
                                log("tip", _user_id,
                                    "(3) getaddressesbyaccount(%s) > Error during RPC call: %s" % (_recipient_id, _rpc_call["message"]))
                            elif _rpc_call["result"]["error"] is not None:
                                print("Error: %s" %
                                      _rpc_call["result"]["error"])
                                log("tip", _user_id, "(3) getaddressesbyaccount(%s) > Error: %s" % (
                                    _recipient_id, _rpc_call["result"]["error"]))
                            else:
                                _address = None
                                _addresses = _rpc_call["result"]["result"]
                                if len(_addresses) == 0:
                                    # Recipient has no address, create one
                                    _rpc_call = __wallet_rpc.getaccountaddress(
                                        _recipient_id)
                                    if not _rpc_call["success"]:
                                        print("Error during RPC call.")
                                        log("tip", _user_id,
                                            "(4) getaccountaddress(%s) > Error during RPC call: %s" % (
                                                _recipient_id, _rpc_call["message"])
                                            )
                                    elif _rpc_call["result"]["error"] is not None:
                                        print("Error: %s" %
                                              _rpc_call["result"]["error"])
                                        log("tip", _user_id, "(4) getaccountaddress(%s) > Error: %s" % (
                                            _recipient_id, _rpc_call["result"]["error"]))
                                    else:
                                        _address = _rpc_call["result"]["result"]
                                else:
                                    # Recipient has an address, we don't need to create one for him
                                    _address = _addresses[0]
                            if _address is not None:
                                # Because recipient has an address, we can add him to the dict
                                _tip_dict_accounts[_recipient_id] = _amounts_float[i]
                                _tip_dict_addresses[_address] = _amounts_float[i]
                            i += 1
                        #
                        _tip_dict = {}
                        if __rpc_sendmany_account:
                            _tip_dict = _tip_dict_accounts
                        else:
                            _tip_dict = _tip_dict_addresses
                        # Check if there are users left to tip
                        if len(_tip_dict) == 0:
                            return

                        # Done: replace .move by .sendfrom or .sendmany (2018-07-16)
                        # sendfrom <from address or account> <receive address or account> <amount> [minconf=1] [comment] [comment-to]
                        # and
                        # sendmany <from address or account> {receive address or account:amount,...} [minconf=1] [comment]
                        _rpc_call = __wallet_rpc.sendmany(
                            _user_id, _tip_dict, __minconf)
                        if not _rpc_call["success"]:
                            print("Error during RPC call.")
                            log("tip", _user_id, "(4) sendmany > Error during RPC call: %s" %
                                _rpc_call["message"])
                        elif _rpc_call["result"]["error"] is not None:
                            print("Error: %s" % _rpc_call["result"]["error"])
                            log("tip", _user_id, "(4) sendmany > Error: %s" %
                                _rpc_call["result"]["error"])
                        else:
                            _tx = _rpc_call["result"]["result"]
                            _suppl = ""
                            if len(_tip_dict) != len(_recipients):
                                _suppl = "\n\n_%s_" % strings.get(
                                    "tip_missing_recipient", _lang)
                            update.message.reply_text(
                                text="*%s* %s\n%s\n\n[tx %s](%s)%s" % (
                                    update.effective_user.name,
                                    strings.get("tip_success", _lang),
                                    ''.join((("\n- `%6s `to *%s*" % (convert_satoshi(
                                        _tip_dict_accounts[_recipient_id]), _handled[_recipient_id][0])) for _recipient_id in _tip_dict_accounts)),
                                    _tx[:4] + "..." + _tx[-4:],
                                    __blockchain_explorer_tx + _tx,
                                    _suppl
                                ),
                                quote=True,
                                parse_mode=ParseMode.MARKDOWN,
                                disable_web_page_preview=True
                            )


# Done: Revamp withdraw() function (2018-07-16)
def withdraw(update: Update, context: CallbackContext):
    """
    Withdraw to an address. Works only in private.
    """
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"
    #
    if _chat_type == "private":
        if not _spam_filter.verify(str(update.effective_user.id)):
            return  # ToDo: Return a message?
        if _paused:
            update.message.reply_text(text=emoji.emojize(
                strings.get("global_paused"), use_aliases=True), quote=True)
            return
        _amount = None
        _recipient = None
        if context.args == None:
            update.message.reply_text(
                "You have to provide an withdraw address and an ONION amount.", quote=True)
            return
        if len(context.args) == 2:
            try:
                _amount = context.args[1]
                _recipient = context.args[0]
            except:
                try:
                    _amount = context.args[0]
                    _recipient = context.args[1]
                except:
                    pass
        else:
            update.message.reply_text(
                text="Too few or too many arguments for this command.",
                quote=True
            )
        if _amount is not None and _recipient is not None:
            _username = update.effective_user.username
            if _username is None:
                _user_id = str(update.effective_user.id)
            else:
                _user_id = '@' + _username.lower()
            # get address of user
            _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
            if not _rpc_call["success"]:
                print("Error during RPC call: %s" % _rpc_call["message"])
                log("withdraw", _user_id, "(1) getaddressesbyaccount > Error during RPC call: %s" %
                    _rpc_call["message"])
            elif _rpc_call["result"]["error"] is not None:
                print("Error: %s" % _rpc_call["result"]["error"])
                log("withdraw", _user_id, "(1) getaddressesbyaccount > Error: %s" %
                    _rpc_call["result"]["error"])
            else:
                _addresses = _rpc_call["result"]["result"]
                if len(_addresses) == 0:
                    # User has no address, ask him to create one
                    msg_no_account(context.bot, update)
                else:
                    _address = _addresses[0]
                    if __rpc_getbalance_account:
                        _rpc_call = __wallet_rpc.getbalance(
                            _user_id, __minconf)
                    else:
                        _rpc_call = __wallet_rpc.getbalance(
                            _address, __minconf)
                    if not _rpc_call["success"]:
                        print("Error during RPC call.")
                        log("withdraw", _user_id, "(2) getbalance > Error during RPC call: %s" %
                            _rpc_call["message"])
                    elif _rpc_call["result"]["error"] is not None:
                        print("Error: %s" % _rpc_call["result"]["error"])
                        log("withdraw", _user_id, "(2) getbalance > Error: %s" %
                            _rpc_call["result"]["error"])
                    else:
                        _balance = float(_rpc_call["result"]["result"])
                        if _balance < float(_amount) + __fee_std*2:
                            update.message.reply_text(
                                text="%s `%s`" % (strings.get(
                                    "withdraw_no_funds", _lang), convert_satoshi(_balance-__fee_std*2)),
                                quote=True,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        else:
                            # Withdraw
                            _rpc_call = __wallet_rpc.sendfrom(
                                _user_id, _recipient, float(_amount), __minconf)
                            if not _rpc_call["success"]:
                                print("Error during RPC call.")
                                log("withdraw", _user_id, "(3) sendfrom > Error during RPC call: %s" %
                                    _rpc_call["message"])
                            elif _rpc_call["result"]["error"] is not None:
                                print("Error: %s" %
                                      _rpc_call["result"]["error"])
                                log("withdraw", _user_id, "(3) sendfrom > Error: %s" %
                                    _rpc_call["result"]["error"])
                            else:
                                _tx = _rpc_call["result"]["result"]
                                update.message.reply_text(
                                    text="%s\n[tx %s](%s)" % (
                                        strings.get("withdraw_success", _lang),
                                        _tx[:4]+"..."+_tx[-4:],
                                        __blockchain_explorer_tx + _tx
                                    ),
                                    quote=True,
                                    parse_mode=ParseMode.MARKDOWN,
                                    disable_web_page_preview=True
                                )
    else:
        _button = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_withdraw", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=withdraw" % context.bot.username,
        )
        _markup = InlineKeyboardMarkup(
            [[_button]]
        )
        update.message.reply_text(
            "%s" % strings.get("user_balance_public", _lang),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )


def scavenge(update: Update, context: CallbackContext):
    if update.effective_chat is None:
        _chat_type = "private"
    elif update.effective_chat.type == "private":
        _chat_type = "private"
    else:
        _chat_type = "group"
    # Only if it's a private conversation with the bot
    if _chat_type == "private":
        if not _spam_filter.verify(str(update.effective_user.id)):
            return  # ToDo: Return a message?
        if _paused:
            update.message.reply_text(text=emoji.emojize(
                strings.get("global_paused"), use_aliases=True), quote=True)
            return
        _username = update.effective_user.username
        if _username is None:
            update.message.reply_text(
                text="Sorry, this command is not for you.",
                quote=True
            )
        else:
            _username = '@' + _username.lower()
            _user_id = str(update.effective_user.id)
            # Done: Check balance of UserID (2018-07-16)
            # get address of user
            _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
            if not _rpc_call["success"]:
                print("Error during RPC call: %s" % _rpc_call["message"])
                log("scavenge", _user_id, "(1) getaddressesbyaccount > Error during RPC call: %s" %
                    _rpc_call["message"])
            elif _rpc_call["result"]["error"] is not None:
                print("Error: %s" % _rpc_call["result"]["error"])
                log("scavenge", _user_id, "(1) getaddressesbyaccount > Error: %s" %
                    _rpc_call["result"]["error"])
            else:
                _addresses = _rpc_call["result"]["result"]
                if len(_addresses) == 0:
                    update.message.reply_text(
                        text="%s (`%s`)" % (strings.get(
                            "scavenge_no_address", _lang), _user_id),
                        quote=True,
                    )
                else:
                    _address = _addresses[0]
                    if __rpc_getbalance_account:
                        _rpc_call = __wallet_rpc.getbalance(
                            _user_id, __minconf)
                    else:
                        _rpc_call = __wallet_rpc.getbalance(
                            _address, __minconf)
                    if not _rpc_call["success"]:
                        print("Error during RPC call.")
                        log("scavenge", _user_id, "(2) getbalance > Error during RPC call: %s" %
                            _rpc_call["message"])
                    elif _rpc_call["result"]["error"] is not None:
                        print("Error: %s" % _rpc_call["result"]["error"])
                        log("scavenge", _user_id, "(2) getbalance > Error: %s" %
                            _rpc_call["result"]["error"])
                    else:
                        _balance = float(_rpc_call["result"]["result"])
                        # Done: Move balance from UserID to @username if balance > 5 (2018-07-16)
                        if _balance <= __fee_std*3:
                            update.message.reply_text(
                                text="%s (`ID %s`)." % (strings.get(
                                    "scavenge_empty", _lang), _user_id),
                                parse_mode=ParseMode.MARKDOWN,
                                quote=True
                            )
                        else:
                            # Need to make sure there is an account for _username
                            _rpc_call = __wallet_rpc.getaddressesbyaccount(
                                _username)
                            if not _rpc_call["success"]:
                                print("Error during RPC call: %s" %
                                      _rpc_call["message"])
                                log("scavenge", _user_id, "(3) getaddressesbyaccount > Error during RPC call: %s" %
                                    _rpc_call["message"])
                            elif _rpc_call["result"]["error"] is not None:
                                print("Error: %s" %
                                      _rpc_call["result"]["error"])
                                log("scavenge", _user_id, "(3) getaddressesbyaccount > Error: %s" %
                                    _rpc_call["result"]["error"])
                            else:
                                _address = None
                                _addresses = _rpc_call["result"]["result"]
                                if len(_addresses) == 0:
                                    # Create an address for user (_username)
                                    _rpc_call = __wallet_rpc.getaccountaddress(
                                        _username)
                                    if not _rpc_call["success"]:
                                        print("Error during RPC call.")
                                        log("scavenge", _user_id, "(4) getaccountaddress > Error during RPC call: %s" %
                                            _rpc_call["message"])
                                    elif _rpc_call["result"]["error"] is not None:
                                        print("Error: %s" %
                                              _rpc_call["result"]["error"])
                                        log("scavenge", _user_id, "(4) getaccountaddress > Error: %s" %
                                            _rpc_call["result"]["error"])
                                    else:
                                        _address = _rpc_call["result"]["result"]
                                else:
                                    _address = _addresses[0]
                                if _address is not None:
                                    # Move the funds from UserID to Username
                                    # ToDo: Make the fees consistent
                                    _amount = _balance - 3 * __fee_std
                                    _rpc_call = __wallet_rpc.sendfrom(
                                        _user_id, _address, _amount, __minconf)
                                    if not _rpc_call["success"]:
                                        print("Error during RPC call.")
                                        log("scavenge", _user_id, "(5) sendfrom > Error during RPC call: %s" %
                                            _rpc_call["message"])
                                    elif _rpc_call["result"]["error"] is not None:
                                        print("Error: %s" %
                                              _rpc_call["result"]["error"])
                                        log("scavenge", _user_id, "(5) sendfrom > Error: %s" %
                                            _rpc_call["result"]["error"])
                                    else:
                                        _tx = _rpc_call["result"]["result"]
                                        update.message.reply_text(
                                            text="%s (`%s`).\n%s `%s`\n[tx %s](%s)" % (
                                                strings.get(
                                                    "scavenge_success_1", _lang),
                                                _user_id,
                                                strings.get(
                                                    "scavenge_success_2", _lang),
                                                convert_satoshi(
                                                    _balance-__fee_std*3),
                                                _tx[:4]+"..."+_tx[-4:],
                                                __blockchain_explorer_tx + _tx,
                                            ),
                                            quote=True,
                                            parse_mode=ParseMode.MARKDOWN,
                                            disable_web_page_preview=True
                                        )


def damp_rock(update: Update, context: CallbackContext):
    """
    Manages a queue of active users.
    Activity type is checked before calling this function.
    Message length should be enforced to avoid spam.
    :param bot: Bot
    :param update: Update
    :return: None
    """
    if _paused:
        return
    if update.effective_chat is None:
        return
    elif update.effective_chat.type not in ["group", "supergroup"]:
        return
    #
    _group_id = str(update.effective_chat.id)
    if update.effective_user.is_bot:
        return
    # Get user_id for the tip command (either @username or else UserID)
    _username = update.effective_user.username
    # The queue uses real UserID to avoid registering a user twice if user creates @
    _user_id = str(update.effective_user.id)
    if _username is None:
        _user_id_local = _user_id
        _user_readable_name = update.effective_user.name
    else:
        _user_id_local = '@' + _username.lower()
        _user_readable_name = _username
    if update.effective_message.text is not None:
        if len(update.effective_message.text) < __rain_queue_min_text_length:
            return
        if len(update.effective_message.text.split()) < __rain_queue_min_words:
            return
    # Check the queue
    if _group_id not in _rain_queues:
        _rain_queues[_group_id] = []
    # Note: In Python2, Dict doesn't preserve order as in Python3 (see https://stackoverflow.com/questions/14956313)
    if len(_rain_queues[_group_id]) > 0:
        # If user has talked last, don't remove it, don't add it.
        # Don't use "is not", the object will not be the same, only value will
        if _rain_queues[_group_id][0][0] == _user_id:
            return
        else:
            # Search for user and remove it (in order to place it first)
            for _user_data in _rain_queues[_group_id]:
                if _user_data[0] == _user_id:
                    _rain_queues[_group_id].remove(_user_data)
                    break
    # Add user to queue (first, since it will be read from first to last)
    _rain_queues[_group_id].insert(
        0, (_user_id, _user_id_local, _user_readable_name))
    # Check if the queue has to be pruned
    if len(_rain_queues[_group_id]) > __rain_queue_max_members:
        # pop(-1). This should be enough to remove the last member, but real pruning would be better
        _rain_queues[_group_id].pop()


def rain(update: Update, context: CallbackContext):
    if not _spam_filter.verify(str(update.effective_user.id)):
        return
    if _paused:
        update.message.reply_text(text=emoji.emojize(
            strings.get("global_paused"), use_aliases=True), quote=True)
        return
    if update.effective_chat is None:
        return
    elif update.effective_chat.type not in ["group", "supergroup"]:
        return
    #
    _group_id = str(update.effective_chat.id)
    _user_id = str(update.effective_user.id)
    # We may or may not allow text after the first 2 arguments. Probably not.
    if 0 < len(context.args) <= 2:
        # Check if queue has enough members
        if _group_id not in _rain_queues:
            update.message.reply_text(
                strings.get("rain_queue_not_initialized", _lang),
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return
        # Prepare arguments
        _rain_amount_demanded = 0
        # number of members = min(optional args[1], queue_max, queue_len)
        _rain_members_demanded = __rain_queue_max_members
        try:
            _rain_amount_demanded = float(context.args[0])
            if len(context.args) > 1:
                _rain_members_demanded = int(context.args[1])
        except ValueError:
            return  # Don't show error. Probably trolling.
        if _rain_amount_demanded < __rain_min_amount:
            update.message.reply_text(
                strings.get("rain_queue_min_amount", _lang) % (
                    __rain_min_amount, "ONION", _rain_amount_demanded, "ONION"),
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return
        if _rain_members_demanded < __rain_min_members or _rain_members_demanded > __rain_queue_max_members:
            update.message.reply_text(
                "Can't rain on less than `{}` or more than `{}` members (demanded: `{}`).".format(
                    __rain_min_members, __rain_queue_max_members, _rain_members_demanded),
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return
        # Check if user is in queue, don't remove user from original queue as recipients array will be created later
        # Note that using this command doesn't put the user in queue (commands are excluded from damp_rock())
        _modifier = 0
        for _user_data in _rain_queues[_group_id]:
            if _user_data[0] == _user_id:
                _modifier = -1
                break
        # Check if there are enough members in queue (minus user if needed)
        if len(_rain_queues[_group_id]) + _modifier < __rain_min_members:
            update.message.reply_text(
                strings.get("rain_queue_not_enough_members", _lang) % (
                    len(_rain_queues[_group_id]) + _modifier,
                    - _modifier,
                    __rain_min_members
                ),
                quote=True,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return
        # Prepare queue for tips
        _recipients = []  # Array of LocalUserID
        _handled = {}  # Dict of LocalUserID: (Readable Name, Unused, Unused)
        for _user_data in _rain_queues[_group_id]:
            if _user_data[0] != _user_id:
                # Local UserID (@username or else UserID)
                _recipients.append(_user_data[1])
                _handled[_user_data[1]] = (_user_data[2], None, None)
                if len(_recipients) >= _rain_members_demanded:
                    break
        log("rain", _user_id, "rain (%i over %i members) handed to do_tip()" %
            (_rain_amount_demanded, len(_recipients)))
        do_tip(update, context, [_rain_amount_demanded],
               _recipients, _handled, verb="rain")


def do_tip(update: Update, context: CallbackContext, amounts_float, recipients, handled, verb="tip"):
    """
    Send amounts to recipients
    :param bot: Bot
    :param update: Update
    :param amounts_float: Array of Float
    :param recipients: Array of Username or UserID
    :param handled: Dict of {"username or UserID": (username, entity.offset, entity.length)
    :param verb: "tip", will be used in "%verb%_success" and "%verb%_missing_recipient" strings
    :return: None
    """
    #
    if verb not in ["tip", "rain"]:
        log("do_tip", "__system__", "Incorrect verb passed to do_tip()")
        verb = "tip"
    # Check if only 1 amount is given
    _amounts_float = amounts_float
    if len(_amounts_float) == 1 and len(recipients) > 1:
        _amounts_float = _amounts_float * len(recipients)
    # Check if user has enough balance
    _username = update.effective_user.username
    if _username is None:
        _user_id = str(update.effective_user.id)
    else:
        _user_id = '@' + _username.lower()
    # get address of user
    _rpc_call = __wallet_rpc.getaddressesbyaccount(_user_id)
    if not _rpc_call["success"]:
        print("Error during RPC call: %s" % _rpc_call["message"])
        log("do_tip", _user_id, "(1) getaddressesbyaccount > Error during RPC call: %s" %
            _rpc_call["message"])
    elif _rpc_call["result"]["error"] is not None:
        print("Error: %s" % _rpc_call["result"]["error"])
        log("do_tip", _user_id, "(1) getaddressesbyaccount > Error: %s" %
            _rpc_call["result"]["error"])
    else:
        _addresses = _rpc_call["result"]["result"]
        if len(_addresses) == 0:
            # User has no address, ask him to create one
            msg_no_account(context.bot, update)
        else:
            _address = _addresses[0]
            if __rpc_getbalance_account:
                _rpc_call = __wallet_rpc.getbalance(_user_id, __minconf)
            else:
                _rpc_call = __wallet_rpc.getbalance(_address, __minconf)
            if not _rpc_call["success"]:
                print("Error during RPC call.")
                log("balance", _user_id, "(2) getbalance > Error during RPC call: %s" %
                    _rpc_call["message"])
            elif _rpc_call["result"]["error"] is not None:
                print("Error: %s" % _rpc_call["result"]["error"])
                log("balance", _user_id, "(2) getbalance > Error: %s" %
                    _rpc_call["result"]["error"])
            else:
                _balance = float(_rpc_call["result"]["result"])
                # Now, finally, check if user has enough funds (includes tx fee)
                if sum(_amounts_float) > _balance - max(1*__fee_std, float(len(recipients)/3)*__fee_std):
                    update.message.reply_text(
                        text="%s `%f ONION`" % (strings.get("tip_no_funds", _lang), sum(
                            _amounts_float) + max(1*__fee_std, float(len(recipients)/3)*__fee_std)),
                        quote=True,
                        parse_mode=ParseMode.MARKDOWN
                    )
                # Now create the {recipient_id: amount} dictionary
                else:
                    i = 0
                    _tip_dict_addresses = {}
                    _tip_dict_accounts = {}
                    for _recipient in recipients:
                        # add "or _recipient == bot.id" to disallow tipping the tip bot
                        if _recipient == _user_id:
                            update.message.reply_text(
                                text="There is no point in tipping yourself",
                                quote=True,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            i += 1
                            continue
                        if _recipient[0] == '@':
                            # ToDo: Get the id (actually not possible (Bot API 3.6, Feb. 2018)
                            # Using the @username
                            # Done: When requesting a new address, if user has a @username, then use that username (2018-07-16)
                            # Problem: If someone has no username, then later creates one, he loses access to his account
                            # Done: Create a /scavenge command that allows people who had UserID to migrate to UserName (2018-07-16)
                            _recipient_id = _recipient
                        else:
                            _recipient_id = _recipient
                        # Check if recipient has an address (required for .sendmany()
                        _rpc_call = __wallet_rpc.getaddressesbyaccount(
                            _recipient_id)
                        if not _rpc_call["success"]:
                            print("Error during RPC call.")
                            log("tip", _user_id,
                                "(3) getaddressesbyaccount(%s) > Error during RPC call: %s" % (_recipient_id, _rpc_call["message"]))
                        elif _rpc_call["result"]["error"] is not None:
                            print("Error: %s" %
                                  _rpc_call["result"]["error"])
                            log("tip", _user_id, "(3) getaddressesbyaccount(%s) > Error: %s" % (
                                _recipient_id, _rpc_call["result"]["error"]))
                        else:
                            _address = None
                            _addresses = _rpc_call["result"]["result"]
                            if len(_addresses) == 0:
                                # Recipient has no address, create one
                                _rpc_call = __wallet_rpc.getaccountaddress(
                                    _recipient_id)
                                if not _rpc_call["success"]:
                                    print("Error during RPC call.")
                                    log("tip", _user_id,
                                        "(4) getaccountaddress(%s) > Error during RPC call: %s" % (
                                            _recipient_id, _rpc_call["message"])
                                        )
                                elif _rpc_call["result"]["error"] is not None:
                                    print("Error: %s" %
                                          _rpc_call["result"]["error"])
                                    log("tip", _user_id, "(4) getaccountaddress(%s) > Error: %s" % (
                                        _recipient_id, _rpc_call["result"]["error"]))
                                else:
                                    _address = _rpc_call["result"]["result"]
                            else:
                                # Recipient has an address, we don't need to create one for him
                                _address = _addresses[0]
                        if _address is not None:
                            # Because recipient has an address, we can add him to the dict
                            _tip_dict_accounts[_recipient_id] = _amounts_float[i]
                            _tip_dict_addresses[_address] = _amounts_float[i]
                        i += 1
                    #
                    _tip_dict = {}
                    if __rpc_sendmany_account:
                        _tip_dict = _tip_dict_accounts
                    else:
                        _tip_dict = _tip_dict_addresses
                    # Check if there are users left to tip
                    if len(_tip_dict) == 0:
                        return

                    # Done: replace .move by .sendfrom or .sendmany (2018-07-16)
                    # sendfrom <from address or account> <receive address or account> <amount> [minconf=1] [comment] [comment-to]
                    # and
                    # sendmany <from address or account> {receive address or account:amount,...} [minconf=1] [comment]
                    _rpc_call = __wallet_rpc.sendmany(
                        _user_id, _tip_dict, __minconf)
                    if not _rpc_call["success"]:
                        print("Error during RPC call.")
                        log("tip", _user_id, "(4) sendmany > Error during RPC call: %s" %
                            _rpc_call["message"])
                    elif _rpc_call["result"]["error"] is not None:
                        print("Error: %s" % _rpc_call["result"]["error"])
                        log("tip", _user_id, "(4) sendmany > Error: %s" %
                            _rpc_call["result"]["error"])
                    else:
                        _tx = _rpc_call["result"]["result"]
                        _suppl = ""
                        if len(_tip_dict) != len(recipients):
                            _suppl = "\n\n_%s_" % strings.get(
                                "tip_missing_recipient", _lang)
                        update.message.reply_text(
                            text="*%s* %s\n%s\n\n[tx %s](%s)%s" % (
                                update.effective_user.name,
                                strings.get("rain_success", _lang),
                                ''.join((("\n- `%6s `to *@%s*" % (convert_satoshi(
                                    _tip_dict_accounts[_recipient_id]), handled[_recipient_id][0])) for _recipient_id in _tip_dict_accounts)),
                                _tx[:4] + "..." + _tx[-4:],
                                __blockchain_explorer_tx + _tx,
                                _suppl
                            ),
                            quote=True,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True
                        )
                        # clear only dedicated queue
                        del _rain_queues[str(update.effective_chat.id)]



def convert_to_float(text):
    return float(text)


def convert_satoshi(amount):
    # if amount < __units["multiplier_threshold"]:
    #	return "%i %s" % (amount/__units["multiplier"], __units["symbol"])
    # else:
    #	return "%s %s" % (__units["parent_format"] % amount, __units["parent_name"])
    return "%f %s " % (amount, __units["parent_name"])


def cmd_send_log(update: Update, context: CallbackContext):
    """
    Send logs to (admin) user
    """
    # Note: Don't use emoji in caption
    # Check if admin
    if update.effective_chat.id in config["admins"]:
        with open("log.csv", "rb") as _file:
            _file_name = "%s-log-%s.csv" % (context.bot.username, datetime.fromtimestamp(
                time.time()).strftime("%Y-%m-%dT%H-%M-%S"))
            context.bot.sendDocument(
                chat_id=update.effective_user.id,
                document=_file,
                reply_to_message_id=update.message.message_id,
                caption="Here you are!",
                filename=_file_name
            )
        log(fun="cmd_send_log", user=str(update.effective_user.id),
            message="Log sent to admin '%s'." % update.effective_user.name)


def cmd_clear_log(update: Update, context: CallbackContext):
    if update.effective_chat in config["admins"]:
        clear_log()
        update.message.reply_text(text=emoji.emojize(
            strings.get("clear_log_done"), use_aliases=True))


def cmd_pause(update: Update, context: CallbackContext):
    # Admins only
    if update.effective_chat.id in config["admins"]:
        global _paused
        _paused = not _paused
        _answer = ""
        if _paused:
            _answer = strings.get("pause_answer_paused")
        else:
            _answer = strings.get("pause_answer_resumed")
        update.message.reply_text(emoji.emojize(
            _answer, use_aliases=True), quote=True)


# ToDo: Revamp functions bellow


def price(update: Update, context: CallbackContext):
    pass


def marketcap(update: Update, context: CallbackContext):
    pass


def hi(update: Update, context: CallbackContext):
    bot = context.bot
    if not _spam_filter.verify(str(update.effective_user.id)):
        return  # ToDo: Return a message?
    user = update.message.from_user.username
    if user is None:
        user = "tagless person"
    bot.send_message(chat_id=update.message.chat_id,
                     text="Hello @{0}, how are you doing today?".format(user))


def moon(update: Update, context: CallbackContext):
    update.message.reply_text(text="Moon mission inbound!")


def market_cap(update: Update, context: CallbackContext):
    pass

def exchanges(update: Update, context: CallbackContext):
    _button_feature = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_features", _lang), use_aliases=True),
            callback_data= "features",
        )
    _button_roadmap = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_roadmap", _lang), use_aliases=True),
            callback_data= "roadmap",
        )
    _markup = InlineKeyboardMarkup(
            [[_button_feature, _button_roadmap]]
        )
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text = emoji.emojize(strings.get("exchanges_list", _lang), use_aliases=True),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )

def features(update: Update, context: CallbackContext):
    _button_roadmap = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_roadmap", _lang), use_aliases=True),
            callback_data= "roadmap",
        )
    _button_exchange = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_exchanges", _lang), use_aliases=True),
            callback_data= "exchanges",
        )
    _markup = InlineKeyboardMarkup(
            [[_button_exchange, _button_roadmap]]
        )
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text = emoji.emojize(strings.get("feature_list", _lang), use_aliases=True),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )

def roadmap(update: Update, context: CallbackContext):
    _button_exchange = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_exchanges", _lang), use_aliases=True),
            callback_data= "exchanges",
        )
    _button_feature = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_features", _lang), use_aliases=True),
            callback_data= "features",
        )
    _markup = InlineKeyboardMarkup(
            [[_button_feature, _button_exchange]]
        )
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text = emoji.emojize(strings.get("roadmap", _lang), use_aliases=True),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )

def welcome(update: Update, context: CallbackContext):
    do_chat = -1001488620684
    if not update.message.chat.id == do_chat: # Only welcome in DeepOnion main group
        return
    for new_user_obj in update.message.new_chat_members:
        new_user =new_user_obj.name
        _button_exchange = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_exchanges", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=exchanges" % context.bot.username,
        )
        _button_feature = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_features", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=features" % context.bot.username,
        )
        _button_roadmap = InlineKeyboardButton(
            text=emoji.emojize(strings.get(
                "button_roadmap", _lang), use_aliases=True),
            url="https://telegram.me/%s?start=roadmap" % context.bot.username,
        )
        _markup = InlineKeyboardMarkup(
            [[_button_feature, _button_roadmap, _button_exchange]]
        )
        context.bot.send_message(
            chat_id= update.message.chat_id,
            text= emoji.emojize(strings.get(
                "welcome_new", _lang), use_aliases=True).format(new_user),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=_markup
        )




if __name__ == "__main__":
    updater = Updater(token=config["telegram-token"])
    dispatcher = updater.dispatcher
    # TGBot commands
    dispatcher.add_handler(CommandHandler('start', cmd_start, pass_args=True))
    dispatcher.add_handler(CommandHandler('help', cmd_help))
    dispatcher.add_handler(CallbackQueryHandler(
        callback=cmd_help, pattern=r'^help$'))
    dispatcher.add_handler(CommandHandler('about', cmd_about))
    dispatcher.add_handler(CallbackQueryHandler(
        callback=cmd_about, pattern=r'^about$'))
    # Funny commands
    dispatcher.add_handler(CommandHandler('moon', moon))
    dispatcher.add_handler(CommandHandler('hi', hi))
    # Tipbot commands
    dispatcher.add_handler(CommandHandler('tip', tip, pass_args=True))
    dispatcher.add_handler(CommandHandler(
        'withdraw', withdraw, pass_args=True))
    dispatcher.add_handler(CommandHandler('deposit', deposit))
    dispatcher.add_handler(CommandHandler(
        'address', deposit))  # alias for /deposit
    dispatcher.add_handler(CommandHandler('balance', balance))
    dispatcher.add_handler(CommandHandler("scavenge", scavenge))
    dispatcher.add_handler(CommandHandler("rain", rain, pass_args=True))
    # Conversion commands
    dispatcher.add_handler(CommandHandler('marketcap', marketcap))
    dispatcher.add_handler(CommandHandler('price', price))
    # Admin commands
    dispatcher.add_handler(CommandHandler("send_log", cmd_send_log))
    dispatcher.add_handler(CommandHandler("get_log", cmd_send_log))
    dispatcher.add_handler(CommandHandler("clear_log", cmd_clear_log))
    dispatcher.add_handler(CommandHandler(
        "pause", cmd_pause))  # pause / unpause
    # This will be needed for rain
    dispatcher.add_handler(MessageHandler(__rain_queue_filter, damp_rock))
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, echo))
    # Welcome new user
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    updater.start_polling()
    dispatcher.add_handler(CommandHandler('exchanges', exchanges))
    dispatcher.add_handler(CommandHandler('features', features))
    dispatcher.add_handler(CommandHandler('roadmap', roadmap))
    dispatcher.add_handler(CallbackQueryHandler(
        callback=exchanges, pattern=r'^exchanges$'))
    dispatcher.add_handler(CallbackQueryHandler(
        callback=features, pattern=r'^features$'))
    dispatcher.add_handler(CallbackQueryHandler(
        callback=roadmap, pattern=r'^roadmap$'))



    log("__main__", "__system__", "Started service!")
