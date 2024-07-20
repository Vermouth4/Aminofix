from __future__ import annotations

import ssl
import websocket
from time import sleep
from random import randint
from json import loads, dumps
from datetime import datetime as dt
from threading import Thread
from sys import _getframe as getframe

from .lib import objects, helpers
from .lib.helpers import gen_deviceId, inttime
from .client import Client  #By Vermouth

class SocketHandler:
    def __init__(self, client: Client, socket_trace: bool = False, debug: bool = False):
        self.socket_url = f"wss://ws{randint(1,4)}.aminoapps.com"
        self.debug = debug
        self.socket = None
        self.active = False
        self.headers = None
        self.proxies = None
        self.client = client
        self.reconnectTime = 600
        self.socket_thread = None
        self.pingTime = 10
        self.ping_thread = None
        self.ping_payload = dumps({"t": 116, "o": {"threadChannelUserInfoList": []}})

        if self.socket_enabled:
            self.reconnect_thread = Thread(target=self.reconnect_handler)
            self.reconnect_thread.start()

            self.ping_thread = Thread(target=self.ping_handler)
            self.ping_thread.start()

        websocket.enableTrace(socket_trace)  #By Vermouth

    def new_socket_url(self):
        self.socket_url = f"wss://ws{randint(1,4)}.aminoapps.com"

    def socket_log(self, text, status: str = "INFO"):
        if self.debug:
            print("[SOCKET: {}] ({})".format(status, dt.now().strftime('%Y-%m-%d %H:%M:%S')), text)

    def ping_handler(self):
        while True:
            sleep(self.pingTime)
            if self.socket:
                self.socket.send(self.ping_payload)  #By Vermouth

    def reconnect_handler(self):
        while True:
            sleep(self.reconnectTime)

            if self.active:
                self.close()
                self.socket_log("Reconnecting...")
                
                self.run_amino_socket()

    def ws_run_forever(self):
        self.socket.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE},
            skip_utf8_validation=True,
            ping_interval=self.pingTime,
            ping_payload=self.ping_payload
        )

    def handle_message(self, ws, data):
        self.client.handle_socket_message(data)

    def send(self, data):
        self.socket_log(f"Sending data: {data}")
        try:
            if self.socket:
                self.socket.send(data)
        except Exception as e:
            self.socket_log(str(e), "ERROR")
        
    def handle_error(self, ws, err):
        self.socket_log(
            "Critical error in socket/lib/your code: {} | Socket URL: {}".format(
                str(err).replace("\n",""), self.socket_url
            ),
            "ERROR"
        )
                
    def handle_close(self, ws, close_code, close_msg):
        self.socket_log(
            "Socket {} closed: '{} = {}'!".format(
                self.socket_url, close_code, close_msg
            ),
            "WARNING"
        )  #By Vermouth

    def run_amino_socket(self):
        try:
            if self.client.sid is None:
                return

            device = gen_deviceId() if self.client.autoDevice else self.client.device_id
            final = f"{device}|{inttime()}"

            self.headers = {
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "Upgrade",
                "AUID": self.client.userId,
                "NDCAUTH": f"sid={self.client.sid}",
                "NDCLANG": "en",
                "NDCDEVICEID": device,
                "NDC-MSG-SIG": helpers.signature(final)
            }

            self.new_socket_url()
            self.socket = websocket.WebSocketApp(
                f"{self.socket_url}/?signbody={final.replace('|', '%7C')}",
                on_message=self.handle_message,
                header=self.headers,
                on_error=self.handle_error,
                on_close=self.handle_close
            )

            self.active = True
            self.socket_thread = Thread(target=self.ws_run_forever)
            self.socket_thread.start()

            if self.reconnect_thread is None:
                self.reconnect_thread = Thread(target=self.reconnect_handler)
                self.reconnect_thread.start()
            
            self.socket_log(f"Connected to {self.socket_url}")
        except Exception as e:
            print(e)  #By Vermouth

    def close(self):
        self.active = False
        try:
            if self.socket:
                self.socket.close()
                self.socket_log(f"Closed {self.socket_url}")
        except Exception as closeError:
            self.socket_log(
                "Can't close connection to {}: {}".format(self.socket_url, str(closeError).replace("\n", " ")),
                "ERROR"
            )

class Callbacks:
    def __init__(self, client: Client):
        self.client = client
        self.handlers = {}

        self.methods = {
            304: self._resolve_chat_action_start,
            306: self._resolve_chat_action_end,
            1000: self._resolve_chat_message
        }

        self.chat_methods = {
            "0:0": self.on_text_message,
            "0:100": self.on_image_message,
            "0:103": self.on_youtube_message,
            "1:0": self.on_strike_message,
            "2:110": self.on_voice_message,
            "3:113": self.on_sticker_message,
            "52:0": self.on_voice_chat_not_answered,
            "53:0": self.on_voice_chat_not_cancelled,
            "54:0": self.on_voice_chat_not_declined,
            "55:0": self.on_video_chat_not_answered,
            "56:0": self.on_video_chat_not_cancelled,
            "57:0": self.on_video_chat_not_declined,
            "58:0": self.on_avatar_chat_not_answered,
            "59:0": self.on_avatar_chat_not_cancelled,
            "60:0": self.on_avatar_chat_not_declined,
            "100:0": self.on_delete_message,
            "101:0": self.on_group_member_join,
            "102:0": self.on_group_member_leave,
            "103:0": self.on_chat_invite,
            "104:0": self.on_chat_background_changed,
            "105:0": self.on_chat_title_changed,
            "106:0": self.on_chat_icon_changed,
            "107:0": self.on_voice_chat_start,
            "108:0": self.on_video_chat_start,
            "109:0": self.on_avatar_chat_start,
            "110:0": self.on_voice_chat_end,
            "111:0": self.on_video_chat_end,
            "112:0": self.on_avatar_chat_end,
            "113:0": self.on_chat_content_changed,
            "114:0": self.on_screen_room_start,
            "115:0": self.on_screen_room_end,
            "116:0": self.on_chat_host_transfered,
            "117:0": self.on_text_message_force_removed,
            "118:0": self.on_chat_removed_message,
            "119:0": self.on_text_message_removed_by_admin,
            "120:0": self.on_chat_tip,
            "121:0": self.on_chat_pin_announcement,
            "122:0": self.on_voice_chat_permission_open_to_everyone,
            "123:0": self.on_voice_chat_permission_invited_and_requested,
            "124:0": self.on_voice_chat_permission_invite_only,
            "125:0": self.on_chat_view_only_enabled,
            "126:0": self.on_chat_view_only_disabled,
            "127:0": self.on_chat_unpin_announcement,
            "128:0": self.on_chat_tipping_enabled,
            "129:0": self.on_chat_tipping_disabled,
            "65281:0": self.on_timestamp_message,
            "65282:0": self.on_welcome_message,
            "65283:0": self.on_invite_message
        }  #By Vermouth

        self.chat_actions_start = {
            "Typing": self.on_user_typing_start,
        }

        self.chat_actions_end = {
            "Typing": self.on_user_typing_end,
        }

    def _resolve_chat_message(self, data):
        key = f"{data['o']['chatMessage']['type']}:{data['o']['chatMessage'].get('mediaType', 0)}"
        return self.chat_methods.get(key, self.default)(data)

    def _resolve_chat_action_start(self, data):
        key = data['o'].get('actions', [{}])[0].get('type')
        return self.chat_actions_start.get(key, self.default)(data)

    def _resolve_chat_action_end(self, data):
        key = data['o'].get('actions', [{}])[0].get('type')
        return self.chat_actions_end.get(key, self.default)(data)

    def default(self, data):
        self.client.socket_handler.socket_log(f"Unhandled event: {data}")

    def on_text_message(self, data):
        pass

    def on_image_message(self, data):
        pass

    def on_youtube_message(self, data):
        pass

    def on_strike_message(self, data):
        pass

    def on_voice_message(self, data):
        pass

    def on_sticker_message(self, data):
        pass

    def on_voice_chat_not_answered(self, data):
        pass

    def on_voice_chat_not_cancelled(self, data):
        pass

    def on_voice_chat_not_declined(self, data):
        pass

    def on_video_chat_not_answered(self, data):
        pass

    def on_video_chat_not_cancelled(self, data):
        pass

    def on_video_chat_not_declined(self, data):
        pass

    def on_avatar_chat_not_answered(self, data):
        pass

    def on_avatar_chat_not_cancelled(self, data):
        pass

    def on_avatar_chat_not_declined(self, data):
        pass

    def on_delete_message(self, data):
        pass

    def on_group_member_join(self, data):
        pass

    def on_group_member_leave(self, data):
        pass

    def on_chat_invite(self, data):
        pass

    def on_chat_background_changed(self, data):
        pass

    def on_chat_title_changed(self, data):
        pass

    def on_chat_icon_changed(self, data):
        pass

    def on_voice_chat_start(self, data):
        pass

    def on_video_chat_start(self, data):
        pass

    def on_avatar_chat_start(self, data):
        pass

    def on_voice_chat_end(self, data):
        pass

    def on_video_chat_end(self, data):
        pass

    def on_avatar_chat_end(self, data):
        pass

    def on_chat_content_changed(self, data):
        pass

    def on_screen_room_start(self, data):
        pass

    def on_screen_room_end(self, data):
        pass

    def on_chat_host_transfered(self, data):
        pass

    def on_text_message_force_removed(self, data):
        pass

    def on_chat_removed_message(self, data):
        pass

    def on_text_message_removed_by_admin(self, data):
        pass

    def on_chat_tip(self, data):
        pass

    def on_chat_pin_announcement(self, data):
        pass

    def on_voice_chat_permission_open_to_everyone(self, data):
        pass

    def on_voice_chat_permission_invited_and_requested(self, data):
        pass

    def on_voice_chat_permission_invite_only(self, data):
        pass

    def on_chat_view_only_enabled(self, data):
        pass

    def on_chat_view_only_disabled(self, data):
        pass

    def on_chat_unpin_announcement(self, data):
        pass

    def on_chat_tipping_enabled(self, data):
        pass

    def on_chat_tipping_disabled(self, data):
        pass

    def on_timestamp_message(self, data):
        pass

    def on_welcome_message(self, data):
        pass

    def on_invite_message(self, data):
        pass
