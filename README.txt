MANUAL:

> Aplikacji należy przyznać uprawnienia "execute" za pomocą polecenia:
chmod +x env_measures.py
> Aplikacja potrzebuje tych uprawnień do auto restartu po zmianie ustawień lub w przypadku błędu.
> Od teraz można uruchamić aplikację za pomocą polecenia:
./env_measures.py


> Dane z czujników zapisywane są w katalogu "/data/measures"
> Plik ustawień: "/data/settings.json"
> Plik loggów: "/data/app_info.log"

> Opis działania aplikacji:
Aplikacja napisana w języku Python w wersji 3.7.3. Dzieli się na 4 klasy:
AppLogic - odpowiedzialna za operacje typu back-end
GUI - odpowiedzialna za wyświetlanie i formatowanie głównego okna aplikacji
GraphWindow - odpowiedzialna za wyświetlanie okna z wykresami
MplCanvas - klasa pomocnicza dla klasy GraphWindow, odpowiada za konstruowanie wykresów

Po uruchomieniu programu aplikacja zaczyna zbierać dane z czujników 
co określoną ilość czasu podawaną w sekundach. Wysyła je do zabbixa oraz
zapisuje w lokalnej pamięci w pliku tekstowym (*.txt). Z zebranych danych
konstruuje wykres średniej temperatury i wilgotności w danej godzinie z X dni wstecz, gdzie dzień "1" jest aktualnym dniem. Początkowe ustawienia (użytkownika oraz domyślne) są przechowywane w pliku "data/settings.json".
Ustawienia użytkownika są możliwe do modywikacji z poziomu aplikacji.
Ustawienia domyślne są używane w momencie niepoprawnych ustawień użytkownika, wyswietlany jest komunikat o błędzie przed startem aplikacji. Domyślnych ustawień nie można edytować z poziomu aplikacji. 


> Użyte biblioteki:
PyQt5 - biblioteka graficzna
pandas - biblioteka do przetwarzania danych z czujników
matplotlib - bibliotego do konstruowania wykresów
Adafruit_DHT - biblioteka do obsługi czujników wilgotności i temperatury
RPi.GPIO - biblioteka do obsługi czujnika ruchu

> Build-ins:
partial
sys
os
socket
time
json
re
copy
datetime
logging




