from datetime import datetime
import logging

import requests
from bs4 import BeautifulSoup


class SynergiaScrappedMessage:
    def __init__(self, url, parent_web_session, header, author, message_date, synergia_session):
        """
        :type url: str
        :type parent_web_session: requests.sessions.Session
        :type message_date: datetime
        :type synergia_session: librus_tricks.core.SynergiaClient
        """
        self.web_session = parent_web_session
        self.url = url
        self.id = url.split('/')[-2]
        self.header = header
        self.author_alias = author
        self.msg_date = message_date
        self.synergia_session = synergia_session

    def __read_from_server(self):
        response = self.web_session.get('https://synergia.librus.pl' + self.url)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.find('div', attrs={'class': 'container-message-content'}).text

    @property
    def text(self):
        return self.__read_from_server()

    @property
    def author(self):
        from librus_tricks.classes import SynergiaTeacher
        teachers = self.synergia_session.return_objects('Users', cls=SynergiaTeacher, extraction_key='Users')
        for teacher in teachers:
            if str(teacher.name) in self.author_alias and str(teacher.last_name) in self.author_alias:
                return teacher
        return
    
    @property
    def files(self) -> list:
        response = self.web_session.get('https://synergia.librus.pl' + self.url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', attrs={'class': 'stretch container-message'}).findAll('table')[-2]
        r= []
        for row in table.findAll('tr'):
            p = row.find('a')
            if p!=None:
                l = str(p).split('otworz_w_nowym_oknie(')[-1].split('",')[0].replace('"','').strip().replace('\\',"")
                r.append({'filename':str(row.text).replace('Pliki:',"").strip(),"url":l})
        return r
    
    def __repr__(self):
        return f'<Message from {self.author_alias} into {self.url}>'


class MessageReader:
    def __init__(self, session):
        """

        :param librus_tricks.core.SynergiaClient session:
        """
        self._syn_session = session
        self._web_session = requests.session()
        logging.debug('Obtain AutoLoginToken from server')
        token = session.post('AutoLoginToken')['Token']
        self._web_session.get(f'https://synergia.librus.pl/loguj/token/{token}/przenies/wiadomosci')
        logging.debug('Webscrapper logged into Synergia')

    def read_messages(self):
        messages = []
        page=0
        while True:
            if page==0:
                response = self._web_session.get('https://synergia.librus.pl/wiadomosci')
            else:
                data = {"requestkey": request_key,"filtrUzytkownikow": 0,"idPojemnika": 105,"opcja_zaznaczone_g": 0,"filtr_uzytkownikow": "-","sortujTabele[tabeleKolumna]": 3,"sortujTabele[tabeleKierunek]": 1,"sortujTabele[tabelePojemnik]": 105,"sortowanie[105][0]": "","sortowanie[105][1]": "","sortowanie[105][2]": "","opcja_zaznaczone_d": 0,"numer_strony105": page,"porcjowanie_pojemnik105": 105,"poprzednia": 5}
                response = self._web_session.post('https://synergia.librus.pl/wiadomosci',data=data)
            soup = BeautifulSoup(response.text, 'html.parser')
            pages =soup.find('div',{"class":"pagination"}).find('span').text[-1]
            table = soup.find('table', attrs={'class': 'decorated stretch'})
            tbody = table.find('tbody')
            request_key =request_key = soup.find('input', {'name':'requestkey'})['value']
            if 'Brak wiadomości' in tbody.text:
                return None

            rows = tbody.find_all('tr')
            for message in rows:
                cols = message.find_all('td')
                messages.append(SynergiaScrappedMessage(
                    url=cols[3].a['href'],
                    header=cols[3].text.strip(),
                    author=cols[2].text.strip(),
                    parent_web_session=self._web_session,
                    message_date=datetime.strptime(cols[4].text, '%Y-%m-%d %H:%M:%S'),
                    synergia_session=self._syn_session
                ))
            page+=1
            if page==int(pages):return messages

    def __repr__(self):
        return f'<{self.__class__.__name__} for {self._syn_session.user}>'
