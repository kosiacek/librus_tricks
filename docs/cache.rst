Mechanizmy cache
*****************

Podłączanie innej bazy danych niż domyślny SQLite
==================================================
Domyślny mechanizm cache bazuje na bibliotece SQLAlchemy. Zmiana bazy danych jest dość prosta.

`Przykładowe uri do baz danych <https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls>`_

Przykład z podłączeniem do PostgreSQL.

>>> new_cache = cache.AlchemyCache(engine_uri='postgresql+psycopg2://krystian:librek@db.um.warszawa.pl:5432/dev129')
<AlchemyCache with postgresql backend using psycopg2 driver (postgresql+psycopg2://krystian:librek@db.um.warszawa.pl:5432/dev129)>

.. warning::
    Ze względu na kolumnę JSON można jedynie używać tych wybranych baz danych

    - PostgreSQL (9.4 lub nowsza)
    - MySQL (5.7 lub nowsza)
    - MariaDB (10.2.7 lub nowsza)
    - SQLite (3.9 lub nowsza)
    - Oracle Database (12.2 lub nowsza)

Tworzenie własnego obiektu cache
==================================
Załóżmy, że wbudowany mechanizm cache nie jest wystarczający dla ciebie. Stwórzmy coś nowego.

W tej sekcji tworzenia obiektu cache będę używał modeli Django jak backend dla bazy danych.

Zacznijmy od tego, że ``SynergiaClient`` przyjmuje jedynie obiekty, które są dziedziczone przez ``CacheBase``.

.. code-block:: python

   from librus_tricks.cache import CacheBase

    class DjangoCache(CacheBase):
        pass

Mamy już klasę dziedziczną po ``CacheBase``. Teraz wypadałoby dodać metody, które będą przyjmowały dane itp.
Klasa ``CacheBase`` ma 6 metod:

- ``add_object``
- ``get_object``
- ``del_object``
- ``add_query``
- ``get_query``
- ``del_query``

Każda z tych funkcji MUSI BYĆ NADPISANA!

Przejdźmy do tworzenia nowego cache. Dlatego, że będę używał Django w naszym obiekcie stworzę dwa modele.
Jeden model na zapytania http (queries and responses) i drugi na obiekty.

.. code-block:: python

   from django.db import models
   from jsonfield import JSONField
   from librus_tricks.cache import CacheBase

    class DjangoCache(CacheBase):
        class Responses(models.Model):
            uri = models.URLField()
            owner = models.CharField(max_length=64)
            response = JSONField()
            last_load = models.DateTimeField(auto_now_add=True)
        class Objects(models.Model):
            uid = models.IntegerField(primary_key=True)
            name = models.CharField(max_length=64)
            resource = JSONField()
            last_load = models.DateTimeField(auto_now_add=True)

Super! Mamy już miejsce na przechowywanie naszych danych. Teraz trzeba tylko stworzyć metody.

.. code-block:: python

    from django.db import models
    from jsonfield import JSONField
    from librus_tricks.cache import CacheBase

    class TricksCache(CacheBase):
        class Responses(models.Model):
            uri = models.URLField()
            owner = models.CharField(max_length=64)
            response = JSONField()
            last_load = models.DateTimeField(auto_now_add=True)

        class Objects(models.Model):
            uid = models.IntegerField(primary_key=True)
            name = models.CharField(max_length=64)
            resource = JSONField()
            last_load = models.DateTimeField(auto_now_add=True)

    def add_query(self, uri, response, user_id):
        self.Responses(
            uri=uri, response=response, owner=user_id
        ).save()

    def get_query(self, uri, user_id):
        return self.Responses.objects.filter(uri=uri, owner=user_id).first()

    def del_query(self, uri, user_id):
        return self.Responses.objects.filter(uri=uri, owner=user_id).first().delete()

Teraz trzeba utworzyć podobne metody dla ``_object``. To wszystko.

Potem implementacja takiego obiektu jest banalnie prosta
>>> session = create_session('kocham@librus.pl', 'ApkaLibrusaJestSuper(SzczególnieNaIOS)', cache=cache_lib.TricksCache())

Dokumentacja modułu ``cache.py``
=====================================
.. automodule:: librus_tricks.cache
    :members:
    :undoc-members:
    :special-members: __init__
    :member-order: bysource
