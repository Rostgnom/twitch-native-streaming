#!/usr/bin/env python3

import re
import json
from pprint import pprint
from argparse import ArgumentParser
from json import JSONDecodeError
from subprocess import call
import urllib
from os.path import expanduser
from urllib.parse import urlparse
import requests
import sys
from past.builtins import raw_input

# call watch() if no arguments are supplied
WATCH_AS_DEFAULT = True


class Twitch(object):
    _channel_list = []
    _storage_file = expanduser("~/.twitch-channels")

    def __init__(self):
        self.load_channels()

    def load_channels(self):
        try:
            self._channel_list = json.load(open(self._storage_file, 'r'))
        except (JSONDecodeError, FileNotFoundError):
            self.save_channels()

    def save_channels(self):
        json.dump(self._channel_list, open(self._storage_file, 'w'))

    def add_channel(self, name: str):
        name = name.lower()
        if name not in self._channel_list:
            self._channel_list.append(name.lower())
            self.save_channels()
            return True
        else:
            return False

    def remove_channel(self, name: str):
        if name in self._channel_list:
            self._channel_list.remove(name.lower())
            self.save_channels()
            return True
        else:
            return False

    @property
    def channels(self):
        return self._channel_list


def query_streams(channel_list):
    print("Looking for currently streaming channels...")
    online_streams = []
    for channel in channel_list:
        url = 'https://api.twitch.tv/kraken/streams/' + channel
        response = requests.get(url)

        # try:
        s = response.json()
        s = s["stream"] if "stream" in s else None
        if not s:
            continue

        stream_url = s["channel"]["url"]
        streamer = s["channel"]["display_name"]
        game = s["game"]
        stream_desc = s["channel"]["status"]
        online_streams.append({'name': streamer, 'url': stream_url, 'game': game, 'desc': stream_desc})

    return online_streams


def watch(streams):
    if len(streams) > 0:
        print("Channels online:")
        i = 1
        for s in streams:
            print("({}) {}: [{}] {}".format(i, s['name'], s['game'], s['desc']))
            print("{} {}".format(' ' * (2 + len(str(i))), s['url']))
            i += 1

        while True:
            print()
            input = raw_input("Enter number of stream to watch: ")

            try:
                stream_number = int(input)
                break
            except ValueError:
                print("Please specify the number of the stream to watch.")
                continue

        command = "livestreamer {} best".format(streams[stream_number - 1]['url'])
        call(command.split(), shell=False)

    else:
        print("No streams online.")


def main():
    parser = ArgumentParser(
        description="Add twitch channels and watch them directly with your native video application.")
    parser.add_argument("watch", nargs='?', help="Start watching streams!")
    parser.add_argument("-a", "--add", help="Add one or more channels by name or twitch url", type=str, nargs='+')
    parser.add_argument("-r", "--remove", help="Remove one or more channels by name", type=str, nargs='+')
    parser.add_argument("-l", "--list", help="List all added channels", action='store_true')
    args = parser.parse_args()

    twitch = Twitch()

    if args.add:
        for channel in args.add:
            parsed = urlparse(channel)
            is_url = bool(parsed.scheme)

            if is_url:
                if "twitch.tv" not in parsed.netloc:
                    sys.exit("The url {} is invalid.".format(channel))
                channel = str(parsed.path).split('/').__getitem__(1)

            if twitch.add_channel(channel):
                print("Added {} to the list of channels.".format(channel))
            else:
                print("{} is already in the list of channels.".format(channel))

    if args.remove:
        for channel in args.remove:
            if twitch.remove_channel(channel):
                print("Removed {} from the list of channels.".format(channel))
            else:
                print("{} is not in the list of channels. Nothing removed.".format(channel))

    if args.list:
        print('Your channels: ' + ', '.join(twitch.channels))

    # default action
    if args.watch or (not any(vars(args).values()) and WATCH_AS_DEFAULT):
        if len(twitch.channels) == 0:
            parser.print_help()
            print()
            print('You have not added any channels yet. Try\n  twitch -a [NAME/URL]')
        else:
            # initialize
            watch(query_streams(twitch.channels))
