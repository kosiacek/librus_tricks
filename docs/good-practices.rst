Dobre praktyki
***************

Przywracanie wcześniej utworzonej sesji
========================================

W quick start powiedziałem, że logowanie wygląda mniej więcej tak

.. code-block:: python

   from librus_tricks import create_session
   session = create_session('kocham@librus.pl', 'ApkaLibrusaJestSuper(SzczególnieNaIOS)')

Well... wygląda jakby to było wszystko. No nie do końca.
Podczas dłuższej pracy z librusem można zacząć dostawać captchę przy logowaniu (np. dlatego Travis-CI ma cały czas fail).
W tym celu dobrze by było zapisywać tokeny z takich sesji i nie powtarzać procesu logowania za każdym razem.

Proponuję używać czegoś takiego.

.. code-block:: python

    from librus_tricks import cache as cache_lib
    from librus_tricks import create_session, use_json

    try:
        session = use_json()
    except Exception:
        session = create_session('kocham@librus.pl', 'ApkaLibrusaJestSuper(SzczególnieNaIOS)')
    finally:
        session.user.dump_credentials()

.. warning::
    Biblioteka pozwala na TYLKO JEDNEGO JSONA w swoim root directory. Więcej niż jeden json spowoduje error.
