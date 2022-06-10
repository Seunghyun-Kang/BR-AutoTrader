import json
import requests
import configparser as parser
import datetime
from datetime import date
from pathlib import Path

class Kakao:
    def __init__(self):
        today = date.today()
        properties = parser.ConfigParser()
        
        fpath = Path('config.ini').absolute()
        properties.read(fpath)
        
        self.api_key = properties['KAKAO_INFO']['api_key']
        self.code = properties['KAKAO_INFO']['code']

        try:
            fpath = Path('kakao_token.json').absolute()
            with open(fpath, 'r') as fp:
                print(f"카카오 토큰 있음 - {today}")
                json_data = json.load(fp)
                expire_resfresh = json_data['refresh_token_expires_in']
                expire_accesstoken = json_data['expires_in']
                
        except:
            self.get_request_token()

        self.url_send = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        self.access_token = ""

# 최초 토큰 발췌용 함수 refresh token을 리턴함 (refresh token은 한달정도 유효)
    def get_request_token(self):
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": self.api_key,
            "redirect_uri": "https://localhost:3000",
            "code": self.code
        }

        response = requests.post(url, data=data)
        tokens = response.json()
        print(tokens)

        try:
            fpath = Path('kakao_token.json').absolute()
            
            with open(fpath, "w") as fp:
                json.dump(tokens, fp)
            with open(fpath, "r") as fp: 
                ts = json.load(fp) 
                self.refresh_token = ts["refresh_token"]
        except:
            print("KAKAO get_request_token ERROR OCCURED")

# 토큰을 갱신하는 함수로 refresh token을 인자로 받고 새로운 token을 리턴함 (주기마다 반복 발급 받음)
    def get_refresh_token(self):
        url = "https://kauth.kakao.com/oauth/token"

        fpath = Path('kakao_token.json').absolute()
            
        with open(fpath, "r") as fp:
            json_data = json.load(fp)
            refresh_token = json_data['refresh_token']

        data = {
            "grant_type": "refresh_token",
            "client_id": self.api_key,
            "refresh_token": refresh_token
        }
        
        response = requests.post(url, data=data)
        tokens = response.json()

        try:
            self.access_token = tokens['access_token']
            expires = tokens['expires_in']
        except:
            print(tokens)
            print("KAKAO get_refresh_token ERROR OCCURED")
            self.get_request_token()
            self.get_refresh_token()

    def send_msg_to_me(self, msg):

        self.get_refresh_token()

        header = {'Authorization': 'Bearer ' + self.access_token}
        url = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'

        post = {
            'object_type': 'text',
            'text': msg,
            'link': {'web_url': 'https://developers.kakao.com',
                     'mobile_web_url': 'https://developers.kakao.com'},
        }

        data = {'template_object': json.dumps(post)}
        return requests.post(url, headers=header, data=data)
    
    def send_msg_to_clients(self, msg):

        self.get_refresh_token()

        header = {'Authorization': 'Bearer ' + self.access_token}
        url= "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"
        friend_id = self.get_friends_list()
        data = {
            'receiver_uuids': '["{}"]'.format(friend_id),
            "template_object": json.dumps({
                "object_type": "text",
                "text": msg,
                "link": {'web_url': 'https://developers.kakao.com',
                     'mobile_web_url': 'https://developers.kakao.com'},
            })
        }
        return requests.post(url, headers=header, data=data)

    def get_friends_list(self):
        url = "https://kapi.kakao.com/v1/api/talk/friends" #친구 목록 가져오기
        self.get_refresh_token()
        header = {'Authorization': 'Bearer ' + self.access_token}

        result = json.loads(requests.get(url, headers=header).text)
        friends_list = result.get("elements")
        # print(result)
        print("친구 목록::::")
        print(friends_list)
        return friends_list

# a = Kakao()
# a.send_msg_to_me('테스트입니다')