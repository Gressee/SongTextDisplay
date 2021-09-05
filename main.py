import json
import spotipy
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import time
import threading

import kivy
from kivy.core.window import Window
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

CLIENT_ID = '7873392635534605b0c97f11e4360687'
CLIENT_SECRET = '83bae44d26f34a7a815e056216b7b5d7'

FPS = 30

def get_lines_of_str(string: str) -> int:
    try:
        return string.count('\n')
    except:
        print("Can't count lines")
        return

# Get the songtext from genius lyrics
def get_songtext(song_name: str):
    # From genius.com
    '''
    base_url = 'https://genius.com/search?q='
    song_name = song_name.replace(' ', '%20')
    search_results = requests.get(base_url + song_name).content
    soup = BeautifulSoup(search_results, "html.parser")
    best_matches = soup.findAll('div')
    print(best_matches)
    f = open('page.html', 'w+')
    f.write(str(search_results).replace('\\n', '\n'))
    f.close

    # From lyrics.com
    '''
    try:
        # Search request to get link to songtext
        lyrics_com = 'https://lyrics.com'
        base_url = lyrics_com + '/lyrics/'
        song_name = song_name.replace(' ', '%20')
        search_results = requests.get(base_url + song_name).content
        soup = BeautifulSoup(search_results, "html.parser")
        best_matches = soup.find('div', {'class': 'best-matches'})
        best = best_matches.findChild('div', {'class': 'bm-case'})
        best_link = best.findChild('a', href=True)['href']

        # Get the songtext
        song_text = requests.get(lyrics_com + best_link).content
        soup = BeautifulSoup(song_text, 'html.parser')
        text_element = soup.find('pre', {'id': 'lyric-body-text'})
        text = text_element.get_text()
        return text
    except:
        print(f"Can't scrape text for {song_name}")
        return(':D')
    

class SpotifyApi:
    
    def __init__(self) -> None:
        self.current_song = {}
        self.connect()
        
        t = threading.Thread(target=self.thread_fetch_song, args=())
        t.start()

    def connect(self):
        try:
            self.api = spotipy.Spotify(
                    auth_manager=spotipy.oauth2.SpotifyOAuth(
                        scope="user-read-currently-playing",
                        client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri='http://127.0.0.1:9090'
                    )
                )
        except:
            print("Can't connect with spotify api")

    def thread_fetch_song(self):
        while True:
            try:
                self.current_song = self.api.currently_playing()
                time.sleep(2)
                f = open('song.json', 'w')
                json.dump(self.current_song, f, indent=4)
                f.close()
            except:
                print("Can't get song from spotify api")

    def get_song_name(self):
        try:
            return self.current_song['item']['name']
        except:
            print("Can't get song name")

    def get_song_duration(self):
        try:
            return self.current_song['item']['duration_ms']
        except:
            print("Can't get song duration")
    
    def get_song_progress(self):
        try:
            return self.current_song['progress_ms']
        except:
            print("Can't get song name")


class MyApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.spot_api = SpotifyApi()
        # To detect if the song has changed
        self.last_song_name = ''

        self.scroll_speed = 0
    
    def build(self):
        self.sv = ScrollView(
            size_hint=(1.0, None),
            size=(Window.width, Window.height)
        )
        t = ''
        self.text_label = Label(
            text=t,
            font_size=50,
            size_hint_y=None,
            size=(Window.width, 50 * get_lines_of_str(t) * 1.3)
        )
        self.sv.add_widget(self.text_label)

        Clock.schedule_interval(self.mainloop, 1/FPS)
        return self.sv
    
    def mainloop(self, delta):
        # Check if song has changed
        current_song_name = self.spot_api.get_song_name()
        if not self.last_song_name == current_song_name:
            try:
                self.last_song_name = current_song_name
                text = get_songtext(current_song_name)

                self.text_label.text = text
                self.text_label.size = (Window.width, 50 * get_lines_of_str(text) * 1.5)

                # Reset scroll to the song progres
                # This is 1.0 at the top and 0.0 at the bottom of the view
                self.sv.scroll_y = 1.0 - self.spot_api.get_song_progress()/self.spot_api.get_song_duration()

                # Time that the scroll reches the bottom before the song ends
                time_pad = 22.0   
                # Calc the amount to scroll per frame in seconds
                song_time_left = (self.spot_api.get_song_duration() - self.spot_api.get_song_progress())/1000.0 - time_pad
                frames_left = song_time_left * FPS
                scroll_perecent_left = 1.0 - self.spot_api.get_song_progress()/self.spot_api.get_song_duration()
                self.scroll_speed = scroll_perecent_left/frames_left
            except:
                print("Error while updating for new song")
        # Scroll down with respect to the song progress 
        if self.sv.scroll_y >= 0.0:
            self.sv.scroll_y -= self.scroll_speed

        print(self.sv.scroll_y)

if __name__ == '__main__':
    Window.size = (1600, 900)
    MyApp().run()
