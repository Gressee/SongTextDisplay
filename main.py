import json
from re import S, T
import spotipy
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import time
import threading
import lyricsgenius

import kivy
from kivy.core.window import Window
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout

# Load config from file
with open('config.json', 'r') as f:
    data = json.load(f)
    CLIENT_ID       = data['client_id']
    CLIENT_SECRET   = data['client_secret']
    FPS             = data['fps']
    FONT_SIZE       = data['font_size']
    
    # Time the page reaches the bottom before the song ends
    TIME_PAD        = data['time_pad']
    
    # When no songtext can be found 
    NO_TEXT     = data['no_text']

    # Acces token for genius
    GENIUS_TOKEN = data['genius_token']
    
    f.close()


def get_lines_of_str(string: str) -> int:
    try:
        return string.count('\n')
    except:
        print("Can't count lines")
        return


def prepare_title_for_search(title: str) -> str:
    # Cuts the features from title

    # remove brakets
    b1 = title.find('(')
    b2 = title.find(')')
    if not(b1==-1 or b2==-1):
        title = title[:b1] + title[b2+1:]
    
    # Remov everything after feat
    f = title.find('feat')
    if not f == -1:
        title = title[:f]
    
    f = title.find('Feat')
    if not f == -1:
        title = title[:f]

    f = title.find('with')
    if not f == -1:
        title = title[:f]
    
    f = title.find('-')
    if not f == -1:
        title = title[:f]
    
    title = title.replace('Remastered', '')
    title = title.replace('remastered', '')
    title = title.replace('Remaster', '')
    title = title.replace('remaster', '')
    title = title.replace('Remix', '')
    title = title.replace('remix', '')

    
    return title


def prepare_lyrics(lyrics: str) ->str:
    # Remove stuff in []
    
    while True:
        b1 = lyrics.find('[')
        b2 = lyrics.find(']')

        if b1 == -1 or b2 == -1:
            break
        else:
            # This also cuts the char after  ]
            # bc this is a \n most of the time
            lyrics = lyrics[:b1] + lyrics[b2+2:]
    
    return lyrics


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
            except:
                print("Can't get song from spotify api")

    def get_song_name(self):
        try:
            return self.current_song['item']['name']
        except:
            print("Can't get song name")

    def get_artist(self):
        try:
            return self.current_song['item']['artists'][0]['name']
        except:
            print("Can't get artist")

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

        try:
            self.genius_api = lyricsgenius.Genius(GENIUS_TOKEN)
        except:
            print('Genius failed')

        # To detect if the song has changed
        self.last_song_name = ''

        self.scroll_speed = 0
    
    def build(self):
        self.float = FloatLayout()

        self.sv = ScrollView(
            size_hint=(1.0, 0.85),
            size=(Window.width, Window.height)
        )
        t = ''
        self.text_label = Label(
            text=t,
            font_size=FONT_SIZE,
            size_hint_y=None,
            size=(Window.width, FONT_SIZE * get_lines_of_str(t) * 1.3),
            bold=True
        )
        self.sv.add_widget(self.text_label)
        
        self.title_label = Label(
            text='',
            font_size=80,
            size_hint=(1.0, 0.15),
            pos_hint={'x': 0, 'top': 1.0}
        )
        
        self.disclaimer = Label(
            text='* Evtl. falscher Text',
            font_size=30,
            size_hint=(0.18, 0.07),
            pos_hint={'right': 1.0, 'bottom': 1.0}
        )

        self.float.add_widget(self.title_label)
        self.float.add_widget(self.sv)
        self.float.add_widget(self.disclaimer)

        Clock.schedule_interval(self.mainloop, 1/FPS)
        return self.float

    # Get the songtext from genius lyrics
    def search_song_data(self, song_name: str, main_artist: str=''):
        # Returns text, title and artist

        # From genius.com
        try:
            song_name = prepare_title_for_search(song_name)
            song = self.genius_api.search_song(song_name, main_artist)

            # Remove stuff from lyrics
            l = prepare_lyrics(song.lyrics)

            return [l, song.title, song.artist]
        except:
            print(f"Can't scrape text for {song_name}")
            return [NO_TEXT, '', '']
        
        # Webscraping from lyrics.com
        '''
        try:
            # Search request to get link to songtext
            lyrics_com = 'https://lyrics.com'
            base_url = lyrics_com + '/lyrics/'
            song_name = prepare_title_for_search(song_name)
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
            return(NO_TEXT)
        '''    
    
    def mainloop(self, delta):
        # Check if song has changed
        current_song_name = self.spot_api.get_song_name()
        if not self.last_song_name == current_song_name:
            try:

                self.last_song_name = current_song_name
                artist = self.spot_api.get_artist()
                text, title, artist = self.search_song_data(current_song_name, artist)

                self.text_label.text = text
                self.text_label.size = (Window.width, FONT_SIZE * get_lines_of_str(text) * 1.5)

                if title == '' and artist == '':
                    raise Exception()

                self.title_label.text = title + ' - ' + artist

                # Reset scroll to the song progres
                # This is 1.0 at the top and 0.0 at the bottom of the view
                self.sv.scroll_y = 1.0 - self.spot_api.get_song_progress()/self.spot_api.get_song_duration()

                # Calc the amount to scroll per frame in seconds
                song_time_left = (self.spot_api.get_song_duration() - self.spot_api.get_song_progress())/1000.0 - TIME_PAD
                frames_left = song_time_left * FPS
                scroll_perecent_left = 1.0 - self.spot_api.get_song_progress()/self.spot_api.get_song_duration()
                self.scroll_speed = scroll_perecent_left/frames_left
            except:
                print("Error while updating for new song")
                self.title_label.text = ''
                self.text_label.text = NO_TEXT
        
        # Scroll down with respect to the song progress 
        if self.sv.scroll_y >= 0.0:
            self.sv.scroll_y -= self.scroll_speed

        # When the fetching doenst work and the defualt text is shown
        # then downt scroll
        if self.text_label.text == NO_TEXT:
            self.sv.scroll_y = 1.0


if __name__ == '__main__':
    Window.size = (1920, 1040)
    MyApp().run()

