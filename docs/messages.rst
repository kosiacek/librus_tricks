Wiadomości z Synergii
**********************

Implementacja wiadomości w librus-tricks
===========================================

Librus pozwala odczytać wiadomości z dziennika na 3 sposoby.

- "Nowy" moduł wiadomości do Synergii oparty na flashu (można z niego wykorzystać API oparte na XML)
- Normalny panel z wiadomościami w Synergii
- Implementacja w API (wymaga Mobilnych dodatków)

W librus-tricks wykorzystywane są ostatnie dwie metody, można ich używać na zmianę.

W przypadku kiedy nie mamy mobilnych dodatków możemy wykonać taki skrypt:

.. code-block:: python

    from librus_tricks import create_session

    session = create_session('kocham@librus.pl', 'ApkaLibrusaJestSuper(SzczególnieNaIOS)')

    messages = session.message_reader.read_messages()
    topics = [f'{m.header} by {m.author} \n {m.text}\n' for m in messages]
    print(*topics, sep='\n')

Kiedy jesteś bogaczem i stać cię na mobilne dodatki (lub używasz lucky patchera)

.. code-block:: python

    from librus_tricks import create_session

    session = create_session('kocham@librus.pl', 'ApkaLibrusaJestSuper(SzczególnieNaIOS)')

    messages = session.messages()
    topics = [f'{m.topic} \n {m.body}\n' for m in messages]
    print(*topics, sep='\n')

Na obecną chwilę polecam używać pierwszej opcji, ponieważ jest dłużej rozwijana.

Dokumentacja modułu ``messages.py``
=====================================
.. automodule:: librus_tricks.messages
    :members:
    :undoc-members:
    :special-members: __init__
    :member-order: bysource