---
name: Zgłoś błąd
about: Opisz jaki błąd znalazłeś
title: "[BUG] "
labels: bug
assignees: Backdoorek

---

## Problem
Postaraj się jak najdokładniej opisać problem

## Jak odtworzyć błąd
Odtwarzanie błędu krok po kroku:
1. Stwórz sesję
2. Pójdź `tam`
3. Wykonaj to `print(aaa)`
4. Zobacz error

## Stacktrace
```python
Traceback (most recent call last):
  File "<input>", line 1, in <module>
  File "<input>", line 16, in explore
  File "D:\PycharmProjects\LibrusTricks\librus_tricks\core.py", line 77, in get
    }[response.status_code]
librus_tricks.exceptions.SynergiaForbidden: {'Status': 'Error', 'Code': 'AccessDeny', 'Message': 'Account not have access to FilledByTeacher resource', 'Resources': {'..': {'Url': 'https://api.librus.pl/2.0/Attendances'}}, 'Url': 'https://api.librus.pl/2.0/Attendances/FilledByTeacher'}
```

## Co powinno się stać
Opisz czego się spodziewałeś wykonując daną rzecz

## Zrzuty ekranu/debuggera
*O ile się da*

## Środowisko
  - OS: (np. Ubuntu 19.04)
  - Wersja pythona: (np. 3.7.4)

### Inne rzeczy
Tu możesz napisać rzeczy, które nie miały zastosowania powyżej
