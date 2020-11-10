Uwierzytelnianie
*****************

Jak wygląda logowanie?
=======================
Proces logowania się do API synergii jest trochę skomplikowany.
Librus utrudnił logowanie się do API zamykając mechanizm OAuth. Tak, Librus Portal wykorzystuje OAuth.

1. Pozyskujemy token CSRF z strony Librus Portal
2. Wysyłamy email, hasło i token CSRF do Librus Portal
3. W odpowiedzi dostajemy redirection na ``localhost/bar?code=fg234asd...`` z naszym kodem do API Librus Portal
4. Używamy kodu do otrzymania listy kont Synergii podłączonych do Librus Portal wraz z tokenami
5. Tworzymy sesję i uwierzytelniamy się header'em ``Authentication: Bearer fg234asd...``

Podtrzymywanie sesji
=====================
Od wersji ``0.7.4`` librus-tricks automatycznie wykrywa utracenie sesji.
Jednak *keep in mind*, że mechanizm ponownego uwierzytelniania w Synergii nie jest perfekcyjny i czasami zwraca śmieci,
z którymi librus-tricks (jeszcze) sobie nie radzi. Mi przez ok 72h. sesja została utracona 3 razy i 2 razy udało się ją przywrócić.

Więcej info znajdziesz `tutaj <https://github.com/Backdoorek/Librus-Tricks/issues/13>`_.

Problemy z captcha
===================
Możliwe, że podczas pracy z librus-tricks pojawi się żądanie captchy od strony serwera.
Polecam wtedy w trybie incognito się zalogować na `portal.librus.pl <https://portal.librus.pl/rodzina>`_.
W kolejnych wersjach spróbuję dodać opcję wyświetlania captchy.

Dokumentacja modułu ``auth.py``
=====================================
.. automodule:: librus_tricks.auth
    :members:
    :undoc-members:
    :special-members: __init__
    :member-order: bysource
